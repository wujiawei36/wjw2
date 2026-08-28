from django.contrib.auth import logout, get_user_model
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.sessions.models import Session
from django.core.management import call_command
from django.shortcuts import render, redirect
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
