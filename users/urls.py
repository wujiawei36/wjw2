from django.urls import path
from . import views

app_name = 'users'

urlpatterns = [
	path('login/',views.auth_login,name='login'),
	path('login/otp/',views.auth_otp,name='otp_login'),
	path('logout/',views.auth_logout,name='logout'),
	path('register/',views.auth_register,name='register'),  # 邀请码注册（前台暂不留入口）
	path('settings/',views.user_settings,name='settings'),
	path('settings/password/',views.user_change_password,name='change_password'),
	path('settings/2fa/',views.two_factor_setup,name='two_factor_setup'),
	path('settings/sessions/',views.user_sessions,name='sessions'),
	path('settings/login-history/',views.login_history,name='login_history'),
	path('notifications/',views.notification_list,name='notification_list'),
	path('notifications/<int:notification_id>/read/',views.notification_mark_read,name='notification_mark_read'),
	path('<int:user_id>/',views.user_profile,name='user_profile'),
]
