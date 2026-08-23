from django.urls import path
from . import views

app_name = 'users'

urlpatterns = [
	path('login/',views.auth_login,name='login'),
	path('logout/',views.auth_logout,name='logout'),
	path('register/',views.auth_register,name='register'),
	path('activate/<uidb64>/<token>/', views.auth_activate, name='auth_activate'),
]
