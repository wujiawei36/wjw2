from django.contrib.auth.decorators import permission_required, login_required, user_passes_test
from django.contrib.admin.views.decorators import staff_member_required
from django.http import HttpResponseForbidden
from django.shortcuts import render, redirect
from functools import wraps

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
        return render(request,'panel/run_command.html',{'text':'执行成功'})
    return render(request,'panel/run_command.html')
