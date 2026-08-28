#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
wjw2 安全应急核查脚本
用法（在项目根目录、虚拟环境下执行）：
    python check_security.py
输出：超级管理员、staff、最近新增用户、管理日志、会话、封禁IP等，用于确认被攻击后是否有账号被提权/篡改。
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'wjw2.settings')
django.setup()

from django.contrib.auth import get_user_model
from django.contrib.admin.models import LogEntry
from django.contrib.sessions.models import Session
from django.utils import timezone
from users.models import Ban_IP

U = get_user_model()
LINE = '=' * 60


def main():
    print(LINE)
    print('1. 超级管理员（重点核对：是否有不认识的账号）')
    print(LINE)
    for u in U.objects.filter(is_superuser=True):
        print(f'  id={u.id} 用户名={u.username!r} can_develop={u.can_develop} '
              f'创建={u.date_joined.strftime("%m-%d %H:%M")} 最近登录={u.last_login}')

    print(LINE)
    print('2. staff（非超管）')
    print(LINE)
    for u in U.objects.filter(is_staff=True, is_superuser=False):
        print(f'  id={u.id} 用户名={u.username!r} can_develop={u.can_develop} '
              f'创建={u.date_joined.strftime("%m-%d %H:%M")}')

    print(LINE)
    print('3. can_develop=True 的用户')
    print(LINE)
    for u in U.objects.filter(can_develop=True):
        print(f'  id={u.id} 用户名={u.username!r} staff={u.is_staff} super={u.is_superuser}')

    print(LINE)
    print('4. 全部用户')
    print(LINE)
    for u in U.objects.order_by('id'):
        print(f'  id={u.id} {u.username!r} staff={u.is_staff} super={u.is_superuser} '
              f'active={u.is_active} created={u.date_joined.strftime("%m-%d %H:%M")}')

    print(LINE)
    print('5. 最近 24 小时管理日志（LogEntry）')
    print(LINE)
    logs = LogEntry.objects.filter(action_time__gte=timezone.now() - timezone.timedelta(hours=24))
    print(f'  共 {logs.count()} 条')
    for l in logs.order_by('action_time')[:30]:
        print(f'  [{l.action_time.strftime("%m-%d %H:%M")}] 操作人={l.user.username} '
              f'flag={l.action_flag} 对象={l.object_repr} 内容={l.change_message[:50]}')

    print(LINE)
    print('6. 会话数（异常多 = 可能有大量留存会话）')
    print(LINE)
    print(f'  共 {Session.objects.count()} 个会话')

    print(LINE)
    print('7. 封禁IP')
    print(LINE)
    bans = Ban_IP.objects.all()
    if not bans:
        print('  无')
    for b in bans:
        print(f'  {b.ip} active={b.active} 过期={b.expires_at} 理由={b.reason[:40]}')

    print(LINE)
    print('核查要点：')
    print('  * 第1/2/3节出现不认识的高权限账号 → 已被提权，立即删除该账号')
    print('  * 第4节出现今天新增的账号 → 排查来源')
    print('  * 第5节为空但当天有异常 → 攻击者可能绕过 admin 操作（如 super_login 漏洞）')


if __name__ == '__main__':
    main()
