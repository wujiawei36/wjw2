from django.contrib.auth.models import AbstractUser
from django.db import models

class CustomUser(AbstractUser):
    # 在这里添加你的自定义字段
    can_develop = models.BooleanField('可开发', default = False)

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
