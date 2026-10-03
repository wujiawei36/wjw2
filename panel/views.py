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
from users.models import InviteCode, Ban_IP, PageVisit, DailyVisit, Notification, UserGroup, create_invite_code
from tool.models import ApiKey, generate_api_key, ApiRequestCounter
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
@user_passes_test(can_develop, login_url='/panel')
def api_keys(request):
    """生成 API Key 快捷页：明文 key 只在生成后展示一次，库中仅存加盐哈希"""
    if request.method == 'POST':
        name = request.POST.get('name', '').strip() or '未命名'
        unlimited = request.POST.get('unlimited') == 'on'
        full_key, key_hash = generate_api_key()
        key = ApiKey.objects.create(
            name=name, key_hash=key_hash, owner=request.user, unlimited=unlimited,
        )
        logger.info('API_KEY_GENERATED 用户[%s](id=%s) 生成 API Key[%s] unlimited=%s',
                    request.user.username, request.user.id, key.masked(), unlimited)
        return render(request, 'panel/api_keys.html', {'full_key': full_key, 'key': key})

    return render(request, 'panel/api_keys.html')


@login_required
@staff_member_required
def dashboard(request):
    """管理仪表盘：指标卡 + 24h 登录趋势 + 安全动态 + 最近事件流"""
    now = timezone.now()
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    hours_24 = now - timedelta(hours=24)
    limit = getattr(settings, 'AXES_FAILURE_LIMIT', 5)

    # ===== 指标卡 =====
    counter = ApiRequestCounter.objects.filter(pk=1).first()
    api_today = counter.today_count if (counter and counter.date == timezone.localdate()) else 0
    api_total = counter.total_count if counter else 0
    visit = PageVisit.objects.filter(pk=1).first()
    today_visits = visit.today_count if (visit and visit.date == timezone.localdate()) else 0
    stats = {
        'user_count': User.objects.count(),
        'today_logins': AccessLog.objects.filter(attempt_time__gte=today_start).count(),
        'today_visits': today_visits,
        'api_today': api_today,
        'api_total': api_total,
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


@login_required
@staff_member_required
def broadcast_notification(request):
    """群发通知：目标可为全员/Staff/开发者/普通用户/指定分组/指定单人。"""
    groups = UserGroup.objects.all()
    users = User.objects.order_by('id')
    context = {'groups': groups, 'users': users}

    if request.method == 'POST':
        target_type = request.POST.get('target_type', '')
        content = request.POST.get('content', '').strip()
        if not content:
            context['error'] = '通知内容不能为空'
            return render(request, 'panel/broadcast_notification.html', context)

        targets = []
        label = ''
        if target_type == 'all':
            targets = list(User.objects.all())
            label = '全员'
        elif target_type == 'staff':
            targets = list(User.objects.filter(is_staff=True))
            label = '所有管理员(Staff)'
        elif target_type == 'developers':
            targets = list(User.objects.filter(can_develop=True))
            label = '开发者(can_develop)'
        elif target_type == 'regular':
            targets = list(User.objects.filter(is_staff=False))
            label = '普通用户'
        elif target_type == 'group':
            gid = request.POST.get('group_id', '').strip()
            group = UserGroup.objects.filter(pk=int(gid)).first() if gid.isdigit() else None
            if group is None:
                context['error'] = '请选择有效分组'
                return render(request, 'panel/broadcast_notification.html', context)
            targets = list(group.members.all())
            label = f'分组[{group.name}]'
        elif target_type == 'single':
            uid = request.POST.get('user_id', '').strip()
            u = User.objects.filter(pk=int(uid)).first() if uid.isdigit() else None
            if u is None:
                context['error'] = '请选择有效用户'
                return render(request, 'panel/broadcast_notification.html', context)
            targets = [u]
            label = f'用户[{u.username}]'
        else:
            context['error'] = '未知目标类型'
            return render(request, 'panel/broadcast_notification.html', context)

        if not targets:
            context['error'] = '目标用户集合为空，未发送'
            return render(request, 'panel/broadcast_notification.html', context)

        Notification.objects.bulk_create([
            Notification(target_user=u, content=content) for u in targets
        ])
        logger.info('BROADCAST_NOTIFICATION 用户[%s](id=%s) 向%s发送通知，共%d人',
                    request.user.username, request.user.id, label, len(targets))
        context['success'] = f'已向「{label}」发送通知，共 {len(targets)} 人'

    return render(request, 'panel/broadcast_notification.html', context)


@login_required
@staff_member_required
def api_usage(request):
    """API 用量列表：展示每个 Key 的调用次数/限频次数/配额等。"""
    keys = ApiKey.objects.select_related('owner').order_by('-created_at')
    return render(request, 'panel/api_usage.html', {'keys': keys})


@login_required
@staff_member_required
def visit_trend(request):
    """访问趋势：最近 30 天每日页面访问量柱状图（DailyVisit 快照）。"""
    days = 30
    today = timezone.localdate()
    start = today - timedelta(days=days - 1)
    data = dict(DailyVisit.objects.filter(date__gte=start).values_list('date', 'count'))
    trend = []
    for i in range(days):
        d = start + timedelta(days=i)
        trend.append({'label': f'{d.month}/{d.day}', 'count': data.get(d, 0)})
    max_count = max([x['count'] for x in trend] or [1]) or 1
    return render(request, 'panel/visit_trend.html', {
        'trend': trend, 'max_count': max_count, 'days': days,
    })
