from django.contrib.auth.models import AbstractUser
from django.db import models

class CustomUser(AbstractUser):
    # 在这里添加你的自定义字段
    can_develop = models.BooleanField('可开发', default = False)
    need_email_active = models.BooleanField('等待邮箱激活', default=False)

    class Meta:
        verbose_name = "用户"
        verbose_name_plural = verbose_name

class Notification(models.Model):
    target_user = models.ForeignKey(
        CustomUser,
        on_delete=models.CASCADE,
        related_name='my_notification'
    )
    content = models.TextField('通知内容', blank = False)

    def __str__(self):
        return f'对用户 id={self.target_user.id} 的通知'
    class Meta:
        verbose_name = "用户通知"
        verbose_name_plural = verbose_name

class Ban_IP(models.Model):
    ip = models.GenericIPAddressField('IP 地址:', blank = False, primary_key = True)
    reason = models.TextField('封禁理由:', blank = False)
    updated_at = models.DateTimeField('封禁发起时间:', auto_now=True)
    active = models.BooleanField('启用封禁', default = True)
    class Meta:
        verbose_name = '封禁IP'
        verbose_name_plural = '封禁IP列表'
    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        from users.middleware import banned_ip_cache
        banned_ip_cache.clear()

    def delete(self, *args, **kwargs):
        from users.middleware import banned_ip_cache
        banned_ip_cache.clear()
        return super().delete(*args, **kwargs)
