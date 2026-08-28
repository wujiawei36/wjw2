from django.apps import AppConfig
import logging

logger = logging.getLogger(__name__)


class UsersConfig(AppConfig):
    name = 'users'

    def ready(self):
        """应用就绪时挂载审计信号（hijack 劫持/释放事件记录到日志）"""
        from hijack.signals import hijack_started, hijack_ended
        from django.dispatch import receiver
        from utils.get_ip import get_ip

        @receiver(hijack_started)
        def on_hijack_started(sender, request, hijacker, hijacked, **kwargs):
            logger.warning(
                'HIJACK_STARTED 用户[%s](id=%s) 从IP[%s] 劫持了用户[%s](id=%s)',
                hijacker.username, hijacker.id,
                get_ip(request),
                hijacked.username, hijacked.id,
            )

        @receiver(hijack_ended)
        def on_hijack_ended(sender, request, hijacker, hijacked, **kwargs):
            logger.warning(
                'HIJACK_ENDED 用户[%s](id=%s) 释放了用户[%s](id=%s)',
                hijacker.username, hijacker.id,
                hijacked.username, hijacked.id,
            )
