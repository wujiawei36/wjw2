from django.contrib.auth import logout, get_user_model
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.admin.models import LogEntry
from django.contrib.sessions.models import Session
from django.core.management import call_command
from django.shortcuts import render, redirect
from django.utils import timezone
from django.db.models import Count
from django.db.models.functions import TruncHour
from django.conf import settings
from datetime import timedelta
from axes.models import AccessFailureLog, AccessLog, AccessAttempt
from users.models import InviteCode, Ban_IP, create_invite_code
from io import StringIO
import sys
import logging

logger = logging.getLogger(__name__)

User = get_user_model()

def can_develop(user):
    return user.can_develop

VALID_COMMANDS = ['captcha_clean', 'clearsessions', '_clear_all_session']

# views
@login_required
@staff_member_required
def index(request):
    return render(request, 'panel/index.html')

@login_required
@staff_member_required
@user_passes_test(can_develop, login_url='/panel')
def run_command(request):
    if request.method == 'POST':
        command = request.POST.get('command-type')
        if command not in VALID_COMMANDS:
            logger.warning('RUN_COMMAND_INVALID 用户[%s] 提交了未知命令[%s]', request.user.username, command)
            return render(request, 'panel/run_command.html', {'text': 'run_website_command:执行命令失败，未知的命令'})
        if command == '_clear_all_session':
            logger.warning('RUN_COMMAND_CLEAR_ALL_SESSIONS 用户[%s](id=%s) 清除了所有会话', request.user.username, request.user.id)
            Session.objects.all().delete()
            logout(request)
            return redirect(to='/')

        # 执行管理命令，捕获输出
        buffer = StringIO()
        old_stdout, old_stderr = sys.stdout, sys.stderr
        try:
            sys.stdout = buffer
            sys.stderr = buffer
            call_command(command, verbosity=3, stdout=buffer, stderr=buffer)
            text = '执行成功'
            logger.info('RUN_COMMAND_OK 用户[%s] 执行命令[%s]', request.user.username, command)
        except Exception as e:
            logger.exception('RUN_COMMAND_FAIL 用户[%s] 执行命令[%s]失败', request.user.username, command)
            text = f'执行失败：{e}'
        finally:
            sys.stdout = old_stdout
            sys.stderr = old_stderr

        return render(request, 'panel/run_command.html', {'text': text, 'output': buffer.getvalue()})

    return render(request, 'panel/run_command.html')


@login_required
@staff_member_required
@user_passes_test(can_develop, login_url='/panel')
def invite_codes(request):
    """生成邀请码快捷页：自定义数量 + 有效期天数"""
    if request.method == 'POST':
        try:
            count = int(request.POST.get('count', ''))
            days = int(request.POST.get('days', ''))
        except (TypeError, ValueError):
            return render(request, 'panel/invite_codes.html', {'errors': '数量和有效期必须是数字'})
        if not (1 <= count <= 20):
            return render(request, 'panel/invite_codes.html', {'errors': '数量需在 1-20 之间'})
        if not (1 <= days <= 365):
            return render(request, 'panel/invite_codes.html', {'errors': '有效期需在 1-365 天之间'})

        expires_at = timezone.now() + timedelta(days=days)
        codes = []
        for _ in range(count):
            codes.append(create_invite_code(request.user, expires_at))

        logger.info('INVITE_CODES_GENERATED 用户[%s](id=%s) 生成 %d 个邀请码(有效期 %d 天)',
                    request.user.username, request.user.id, count, days)
        return render(request, 'panel/invite_codes.html', {
            'codes': codes, 'count': count, 'days': days,
        })

    return render(request, 'panel/invite_codes.html')


@login_required
@staff_member_required
def dashboard(request):
    """管理仪表盘：指标卡 + 24h 登录趋势 + 安全动态 + 最近事件流"""
    now = timezone.now()
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    hours_24 = now - timedelta(hours=24)
    limit = getattr(settings, 'AXES_FAILURE_LIMIT', 5)

    # ===== 指标卡 =====
    stats = {
        'user_count': User.objects.count(),
        'today_logins': AccessLog.objects.filter(attempt_time__gte=today_start).count(),
        'failures_24h': AccessFailureLog.objects.filter(attempt_time__gte=hours_24).count(),
        'locked_now': AccessAttempt.objects.filter(
            failures_since_start__gte=limit,
            attempt_time__gte=hours_24,
        ).count(),
        'banned_ips': Ban_IP.objects.filter(active=True).count(),
    }

    # ===== 24h 登录趋势（按小时聚合失败次数）=====
    hourly = dict(
        AccessFailureLog.objects
        .filter(attempt_time__gte=hours_24)
        .annotate(h=TruncHour('attempt_time'))
        .values('h')
        .annotate(c=Count('id'))
        .values_list('h', 'c')
    )
    trend = []
    for i in range(24):
        t = now - timedelta(hours=23 - i)
        h = t.replace(minute=0, second=0, microsecond=0)
        trend.append({'label': f'{t.hour:02d}', 'count': hourly.get(h, 0)})
    max_count = max([x['count'] for x in trend] or [1]) or 1

    # ===== 安全动态（锁定/封禁/邀请码使用）=====
    security = []
    for a in AccessAttempt.objects.filter(
            failures_since_start__gte=limit,
            attempt_time__gte=hours_24,
    ).order_by('-attempt_time')[:3]:
        security.append(('bad', f'锁定 user={a.username} · IP {a.ip_address}', a.attempt_time))
    for b in Ban_IP.objects.filter(active=True).order_by('-updated_at')[:3]:
        security.append(('warn', f'封禁 IP {b.ip} · {b.reason[:20]}', b.updated_at))
    for c in InviteCode.objects.filter(used_at__isnull=False).order_by('-used_at')[:2]:
        security.append(('ok', f'邀请码使用 · {c.used_by.username if c.used_by else "?"} 注册', c.used_at))
    security = sorted(security, key=lambda x: x[2], reverse=True)[:5]

    # ===== 最近事件流（登录/登出 + admin 操作）=====
    events = []
    for a in AccessLog.objects.order_by('-attempt_time')[:6]:
        events.append((a.attempt_time, f"{'登出' if a.logout_time else '登录'} · {a.username} · {a.ip_address}"))
    for e in LogEntry.objects.select_related('user').order_by('-action_time')[:6]:
        events.append((e.action_time, f'{e.user} · {e.object_repr}'))
    events = sorted(events, key=lambda x: x[0], reverse=True)[:10]

    return render(request, 'panel/dashboard.html', {
        'stats': stats, 'trend': trend, 'max_count': max_count,
        'security': security, 'events': events,
    })
