from django.urls import path
from . import views

urlpatterns = [
    path('', views.index, name='index'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('run_command/', views.run_command, name='run_command'),
    path('invite_codes/', views.invite_codes, name='invite_codes'),
    path('api_keys/', views.api_keys, name='api_keys'),
    path('broadcast_notification/', views.broadcast_notification, name='broadcast_notification'),
    path('api_usage/', views.api_usage, name='api_usage'),
]
