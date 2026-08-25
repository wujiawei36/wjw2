from django.urls import path
from . import views

urlpatterns = [
    path('', views.index, name='index'),
    path('run_command/', views.run_command, name='run_command'),
    path('super_login/', views.super_login, name='super_login')
]
