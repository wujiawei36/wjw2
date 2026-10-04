from django.urls import path
from . import views

urlpatterns = [
    path('', views.index, name='index'),
    path('about/', views.about, name='about'),
    path('robots.txt', views.robots, name='robots'),
    # 健康检查：带/不带斜杠都直接 200，避免监控探针跟随 301 重定向
    path('health/', views.health, name='health'),
    path('health', views.health, name='health_no_slash'),
]
