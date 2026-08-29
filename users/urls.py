from django.urls import path
from . import views

app_name = 'users'

urlpatterns = [
	path('login/',views.auth_login,name='login'),
	path('logout/',views.auth_logout,name='logout'),
	path('register/',views.auth_register,name='register'),  # 邀请码注册（前台暂不留入口）
]
