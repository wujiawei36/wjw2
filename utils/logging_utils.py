# utils/logging_utils.py
"""为日志注入当前请求上下文（IP、访问路径），便于在日志中看到每条记录来自谁、访问了什么。"""
import logging
import threading

_thread_local = threading.local()


class LoggingContextMiddleware:
    """把当前请求放入 thread-local，供日志过滤器读取；请求结束即清理。"""

    def __init__(self, get_response):
        self.get_response = get_response
        self.logger = logging.getLogger(__name__)

    def __call__(self, request):
        _thread_local.request = request
        # 临时取证：打印代理头原始值（定位真实IP来源后删除）
        self.logger.info(
            'META_DEBUG REMOTE_ADDR=%r X-Real-IP=%r XFF=%r X-Forwarded-Proto=%r',
            request.META.get('REMOTE_ADDR', ''),
            request.META.get('HTTP_X_REAL_IP', ''),
            request.META.get('HTTP_X_FORWARDED_FOR', ''),
            request.META.get('HTTP_X_FORWARDED_PROTO', ''),
        )
        try:
            return self.get_response(request)
        finally:
            _thread_local.request = None


class RequestContextFilter(logging.Filter):
    """给每条日志附加 ip / path 属性（无请求上下文时为 '-'）。

    优先取日志记录自带的 request（Django 的 404/500 日志会附带），
    其次取 thread-local 中的当前请求（业务日志场景）。
    """

    def filter(self, record):
        request = getattr(record, 'request', None)
        if request is None:
            request = getattr(_thread_local, 'request', None)
        if request is not None:
            from utils.get_ip import get_ip
            record.ip = get_ip(request) or '-'
            record.path = getattr(request, 'path', '') or '-'
        else:
            record.ip = '-'
            record.path = '-'
        return True
