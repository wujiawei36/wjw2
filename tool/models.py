import hashlib
import secrets

from django.conf import settings
from django.db import models
from django.utils import timezone


KEY_PREFIX = 'wjw2_live_'


def hash_api_key(full_key):
    """对 API Key 做加盐哈希：库中只存哈希，明文 key 仅在创建时返回一次。"""
    return hashlib.sha256(('wjw2_api_key_salt::' + full_key).encode('utf-8')).hexdigest()


def generate_api_key():
    """生成一个新的 API Key，返回 (完整key, key_hash)。"""
    full_key = KEY_PREFIX + secrets.token_urlsafe(32)
    return full_key, hash_api_key(full_key)


class ApiKey(models.Model):
    """对外 API 接口的调用凭证。

    安全设计：
    - 只存 key_hash（sha256 加盐），明文 key 仅在创建时展示一次。
    - 支持过期时间、调用额度、工具白名单、一键吊销。
    """
    prefix = models.CharField(max_length=16, default=KEY_PREFIX, editable=False)
    key_hash = models.CharField(max_length=64, unique=True, db_index=True)
    name = models.CharField(max_length=64, help_text='用途备注，如「自己的脚本」')
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL,
        related_name='api_keys', help_text='归属用户（可空）',
    )
    is_active = models.BooleanField(default=True, help_text='取消勾选即吊销')
    expires_at = models.DateTimeField(null=True, blank=True, help_text='过期时间（空=永不过期）')
    quota = models.PositiveIntegerField(null=True, blank=True, help_text='调用额度上限（空=不限）')
    used = models.PositiveIntegerField(default=0, help_text='已使用次数')
    allowed_slugs = models.TextField(blank=True, default='', help_text='允许的工具 slug，逗号分隔（空=全部）')
    created_at = models.DateTimeField(auto_now_add=True)
    last_used_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = 'API Key'
        verbose_name_plural = 'API Key'
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.name} ({self.prefix}...{self.key_hash[-4:]})'

    def masked(self):
        """脱敏展示：前缀 + 哈希后 4 位，绝不显示完整 key。"""
        return f'{self.prefix}...{self.key_hash[-4:]}'

    def allowed_list(self):
        return [s.strip() for s in self.allowed_slugs.split(',') if s.strip()]

    def validate(self, slug):
        """校验该 Key 是否可用于指定工具，返回 (ok, error_code)。"""
        if not self.is_active:
            return False, 'KEY_DISABLED'
        if self.expires_at and self.expires_at <= timezone.now():
            return False, 'KEY_EXPIRED'
        if self.quota is not None and self.used >= self.quota:
            return False, 'QUOTA_EXCEEDED'
        allowed = self.allowed_list()
        if allowed and slug not in allowed:
            return False, 'SLUG_NOT_ALLOWED'
        return True, None
