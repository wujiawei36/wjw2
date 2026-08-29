from django.conf import settings
import ipaddress


def _is_private(ip_str):
    """判断 IP 是否属于内网/保留/回环等不可信地址段。"""
    try:
        ip = ipaddress.ip_address(ip_str)
    except ValueError:
        return True  # 非法格式按内网处理（跳过）
    return (ip.is_private or ip.is_loopback or ip.is_link_local
            or ip.is_reserved or ip.is_multicast)


def get_ip(request):
    """
    获取客户端IP地址。

    安全策略：
    - 默认（TRUST_PROXY=False）：只信任 TCP 层直连地址 REMOTE_ADDR，
      忽略所有可伪造的代理头。
    - 可信代理之后（TRUST_PROXY=True，如自建 nginx / PythonAnywhere）：
      依次尝试 X-Real-IP → X-Forwarded-For（从右往左取第一个公网地址）→ REMOTE_ADDR。
      跳过内网地址：代理链右侧通常是代理追加的内部IP（如 PythonAnywhere 的 10.x），
      从右往左跳过内网后取到的是最近的公网来源。

    使用建议：
    1. 直接对外（runserver / gunicorn 直连）: TRUST_PROXY = False（默认）
    2. 位于可信反向代理之后: 确保代理覆盖 X-Real-IP / X-Forwarded-For，
       再设置 settings.TRUST_PROXY = True
    """
    remote_addr = request.META.get('REMOTE_ADDR', '').strip()

    if not getattr(settings, 'TRUST_PROXY', False):
        return remote_addr

    # 1) nginx 场景：X-Real-IP 优先（取公网地址）
    real_ip = request.META.get('HTTP_X_REAL_IP', '').strip()
    if real_ip and not _is_private(real_ip):
        return real_ip

    # 2) X-Forwarded-For：从右往左取第一个公网地址
    #    最右通常是最新代理追加的内部IP（如 10.0.4.129），跳过它即得到真实客户端
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR', '').strip()
    if x_forwarded_for:
        ips = [ip.strip() for ip in x_forwarded_for.split(',') if ip.strip()]
        for ip in reversed(ips):
            if not _is_private(ip):
                return ip

    # 3) 兜底：直连地址
    return remote_addr
