from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils import timezone
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
    """页面访问聚合计数器（单行记录，pk=1）：供仪表盘「今日访问」等统计使用。

    由 PageVisitMiddleware 更新；静态文件/管理后台/panel/验证码路径不记录。
    完整访问历史见 django.log（每次访问有一条 PAGE_VISIT 日志，保留 7 天），
    因此这里无需逐条记录，用「统计日期 + 当日计数 + 累计计数」聚合即可，
    不随访问量膨胀（跨天自动重置今日，累计单调递增保留总量）。
    """
    date = models.DateField('统计日期', default=timezone.localdate)
    today_count = models.PositiveIntegerField('今日次数', default=0)
    total_count = models.PositiveIntegerField('累计次数', default=0)

    class Meta:
        verbose_name = '页面访问'
        verbose_name_plural = '页面访问'

    def __str__(self):
        return f'{self.date} 今日 {self.today_count} / 累计 {self.total_count}'


def bump_page_visit():
    """每次普通页面访问计数 +1（今日与累计）。

    与 tool.ApiRequestCounter 同款聚合模式：单行记录 + F() 原子更新 +
    date 条件更新，并发下不丢计数、不重复重置，且不随访问量膨胀。
    """
    from django.db.models import F
    today = timezone.localdate()
    obj, created = PageVisit.objects.get_or_create(
        pk=1, defaults={'date': today, 'today_count': 1, 'total_count': 1})
    if created:
        return
    if obj.date != today:
        # 跨天：仅当记录仍停在旧日期时才执行重置（并发下只放行第一个请求）
        PageVisit.objects.filter(pk=1, date=obj.date).update(
            date=today, today_count=1, total_count=F('total_count') + 1)
    else:
        PageVisit.objects.filter(pk=1).update(
            today_count=F('today_count') + 1, total_count=F('total_count') + 1)


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
        # 脱敏：邀请码是注册凭证，明文 str() 会进入 admin 操作日志（LogEntry.object_repr
        # 由 str(obj) 生成），而日志页/dashboard 事件流对所有有 view_logentry 权限者可见。
        # 需要完整码时请用 code 字段本身（如 panel 模板 {{ code.code }}、admin list_display）。
        return f'邀请码({self.code[:4]}****)' if self.code else '邀请码'

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
