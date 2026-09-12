from django.urls import path

from . import views

urlpatterns = [
    path('', views.tool_index, name='tool_index'),
    path('api/<slug:slug>/', views.tool_api, name='tool_api'),
    path('<slug:slug>/', views.tool_detail, name='tool_detail'),
]
