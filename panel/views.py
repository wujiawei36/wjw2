from django.contrib.auth.decorators import permission_required, login_required, user_passes_test
from django.contrib.admin.views.decorators import staff_member_required
from django.core.management import call_command
from django.http import HttpResponseForbidden
from django.shortcuts import render, redirect
from functools import wraps
from io import StringIO
import sys

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
@user_passes_test(can_develop)
def run_command(request):
    if request.method=='POST':
        valid_types = ['captcha_clean',
                       'clearsessions']
        command=request.POST['command-type']
        if command not in valid_types:
            return render(request,'panel/run_command.html',{'text':'run_website_command:执行命令失败，未知的命令'})
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
