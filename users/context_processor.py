from django.conf import settings


def global_site_name(request):
    return {'site_name': settings.SITE_NAME}


def global_notifications(request):
    """注入全局未读通知数（仅登录用户），供 base.html 铃铛使用。"""
    if request.user.is_authenticated:
        from .models import Notification
        unread = Notification.objects.filter(target_user=request.user, is_read=False).count()
        return {'unread_notifications': unread}
    return {'unread_notifications': 0}
