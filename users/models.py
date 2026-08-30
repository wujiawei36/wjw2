from django.contrib.auth.models import AbstractUser
from django.db import models
import secrets
import string

def generate_invite_code(length=8):
    """生成 8 位大写字母+数字邀请码，剔除易混淆字符（0/O/1/I/L）"""
    alphabet = string.ascii_uppercase + string.digits
    alphabet = alphabet.replace('O', '').replace('0', '').replace('I', '').replace('L', '').replace('1', '')
    return ''.join(secrets.choice(alphabet) for _ in range(length))


def create_invite_code(created_by, expires_at, max_attempts=5):
    """创建唯一邀请码：随机碰撞（概率极低）时自动重试，避免唯一约束报错导致 500。"""
    from django.db import IntegrityError
    for _ in range(max_attempts):
        code = generate_invite_code()
        try:
            return InviteCode.objects.create(code=code, created_by=created_by, expires_at=expires_at)
        except IntegrityError:
            continue
    raise RuntimeError('连续多次生成邀请码均与已有邀请码冲突，请重试')

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
    expires_at = models.DateTimeField('封禁过期时间(留空=永久)', null = True, blank = True)
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


class PageVisit(models.Model):
    """页面访问记录（轻量埋点）：供仪表盘「今日访问」等统计使用。

    由 PageVisitMiddleware 写入；静态文件/管理后台/panel/验证码路径不记录。
    记录会随 cleanup_page_visits 管理命令定期清理（默认保留 30 天）。
    """
    path = models.CharField('访问路径', max_length=255)
    ip = models.GenericIPAddressField('IP', null=True, blank=True)
    created_at = models.DateTimeField('访问时间', auto_now_add=True, db_index=True)

    class Meta:
        verbose_name = '页面访问'
        verbose_name_plural = '页面访问'
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.path} @ {self.created_at:%m-%d %H:%M}'


class InviteCode(models.Model):
    code = models.CharField('邀请码', max_length=16, unique=True)
    created_by = models.ForeignKey(
        CustomUser,
        on_delete=models.CASCADE,
        related_name='created_invite_codes',
        verbose_name='创建者',
    )
    created_at = models.DateTimeField('创建时间', auto_now_add=True)
    expires_at = models.DateTimeField('有效期至')
    used_at = models.DateTimeField('使用时间', null=True, blank=True)
    used_by = models.ForeignKey(
        CustomUser,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='used_invite_code',
        verbose_name='使用者',
    )

    class Meta:
        verbose_name = '邀请码'
        verbose_name_plural = '邀请码'
        ordering = ['-created_at']

    def __str__(self):
        return self.code

    @property
    def is_used(self):
        return self.used_at is not None

    @property
    def is_expired(self):
        from django.utils import timezone
        return self.expires_at <= timezone.now()

    @property
    def status_text(self):
        if self.is_used:
            return '已使用'
        if self.is_expired:
            return '已过期'
        return '可用'
