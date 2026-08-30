from django.urls import path
from . import views

urlpatterns = [
    path('', views.index, name='index'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('run_command/', views.run_command, name='run_command'),
    path('invite_codes/', views.invite_codes, name='invite_codes'),
]
