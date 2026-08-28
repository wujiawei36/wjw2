from django.urls import path
from . import views

urlpatterns = [
    path('', views.index, name='index'),
    path('run_command/', views.run_command, name='run_command'),
]
