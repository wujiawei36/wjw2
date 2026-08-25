from django.contrib.auth import logout, get_user_model, SESSION_KEY, BACKEND_SESSION_KEY, HASH_SESSION_KEY
from django.contrib.auth.decorators import permission_required, login_required, user_passes_test
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.sessions.models import Session
from django.core.management import call_command
from django.shortcuts import render, redirect
from django.http import HttpResponseForbidden
from django.contrib.auth import logout
from functools import wraps
from io import StringIO
import sys

User = get_user_model()

# @login_required
# @permission_required('users.delete_user')
# @staff_member_required

# utils

# def group_required(group_name):
#     def decorator(view_func):
#         @wraps(view_func)
#         def wrapper(request, *args, **kwargs):
#             if not request.user.is_authenticated:
#                 return redirect('login')
#             if not request.user.groups.filter(name=group_name).exists():
#                 return HttpResponseForbidden('权限不足')
#             return view_func(request, *args, **kwargs)
#         return wrapper
#     return decorator

def can_develop(user):
    return user.can_develop

# views
@login_required
@staff_member_required
def index(request):
    return render(request,'panel/index.html')

@login_required
@staff_member_required
@user_passes_test(can_develop, login_url='/panel')
def run_command(request):
    if request.method=='POST':
        valid_types = ['captcha_clean',
                       'clearsessions',
                       '_clear_all_session']
        command=request.POST['command-type']
        if command not in valid_types:
            return render(request,'panel/run_command.html',{'text':'run_website_command:执行命令失败，未知的命令'})
        if command == '_clear_all_session':
            Session.objects.all().delete()
            logout(request)
            return redirect(to='/')
        buffer = StringIO()
        old_stdout = sys.stdout
        old_stderr = sys.stderr

        # 4. 执行命令（后续逻辑不变）
        try:
            sys.stdout = buffer
            sys.stderr = buffer
            
            call_command(
                command,
                # 移除 interactive=False（自定义命令不支持该参数）
                verbosity = 3,
                stdout = buffer,
                stderr = buffer
            )
            sys.stdout = old_stdout
            sys.stderr = old_stderr

            print(buffer.getvalue())
            return render(request, 'panel/run_command.html', {'text':'执行成功','output':buffer.getvalue()})

        except Exception as e:
            sys.stdout = old_stdout
            sys.stderr = old_stderr
            print(buffer.getvalue())
            return render(request, 'panel/run_command.html', {'text':f'执行失败：{str(e)}','output':buffer.getvalue()})
    
    return render(request,'panel/run_command.html')

@login_required
@staff_member_required
@user_passes_test(can_develop, login_url='/panel')
def super_login(request):
    if request.method=='POST':
        uid = request.POST['uid']
        try:
            user = User.objects.get(id=uid)
        except User.DoesNotExist:
            return render(request,'panel/super_login.html',{'text':'用户不存在'})

        # 先调用 logout() 清除旧的认证信息（但 session 中的其他数据会被保留）
        # 注意：logout() 默认会清空整个 session，如果你需要保留其他数据，需要额外处理
        logout(request)

        # 手动设置 session，模拟登录状态（不触发 last_login 更新）
        request.session[SESSION_KEY] = user.pk
        request.session[BACKEND_SESSION_KEY] = 'django.contrib.auth.backends.ModelBackend'
        request.session[HASH_SESSION_KEY] = user.get_session_auth_hash()
        request.session.cycle_key()  # 安全起见，旋转 session ID

        return redirect('/')
    return render(request,'panel/super_login.html')
