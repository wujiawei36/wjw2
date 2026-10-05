"""Cloudflare 官方 IP 段与扫描器识别。

用于在中间件中「双重验证」放行 Cloudflare 的安全扫描器：仅当请求 UA 是
Cloudflare 扫描器、且请求 IP 属于 Cloudflare 官方 IP 段（AS13335）时，才视为
可信，跳过爬虫检测（UA 黑名单 / 缺头拦截 / 无头浏览器），但仍保留频率限流。

双重验证的必要性：UA 可被轻易伪造，IP 段是相对可靠的来源锚点；两者同时
满足才放行，避免「伪造 UA」或「借 Cloudflare 网络（如 Workers）发起攻击」
任一单点被利用。
"""
import ipaddress

# Cloudflare 官方 IP 段（来源：https://www.cloudflare.com/ips-v4 与 ips-v6）
CLOUDFLARE_IPV4_CIDRS = [
    '173.245.48.0/20',
    '103.21.244.0/22',
    '103.22.200.0/22',
    '103.31.4.0/22',
    '141.101.64.0/18',
    '108.162.192.0/18',
    '190.93.240.0/20',
    '188.114.96.0/20',
    '197.234.240.0/22',
    '198.41.128.0/17',
    '162.158.0.0/15',
    '104.16.0.0/13',
    '104.24.0.0/14',
    '172.64.0.0/13',
    '131.0.72.0/22',
]

CLOUDFLARE_IPV6_CIDRS = [
    '2400:cb00::/32',
    '2606:4700::/32',
    '2803:f800::/32',
    '2405:b500::/32',
    '2405:8100::/32',
    '2a06:98c0::/29',
    '2c0f:f248::/32',
]

# 编译为 ip_network，匹配时按前缀位比较（O(1) 量级）
CLOUDFLARE_NETWORKS = tuple(
    ipaddress.ip_network(cidr)
    for cidr in CLOUDFLARE_IPV4_CIDRS + CLOUDFLARE_IPV6_CIDRS
)

# Cloudflare 扫描器 UA 关键字：
#   - url-checker        → URL Scanner（Security Center / Radar），UA 形如 url-checker/1.0
#   - cloudflare         → Radar Scanner 等，UA 形如 Cloudflare-Radar-Scanner/1.0
CLOUDFLARE_SCANNER_UA_KEYWORDS = ('cloudflare', 'url-checker')


def is_cloudflare_ip(ip):
    """判断 IP 是否属于 Cloudflare 官方 IP 段。空/非法 IP 返回 False。"""
    if not ip:
        return False
    try:
        addr = ipaddress.ip_address(ip)
    except ValueError:
        return False
    return any(addr in net for net in CLOUDFLARE_NETWORKS)


def is_cloudflare_scanner_ua(user_agent):
    """判断 UA 是否为 Cloudflare 扫描器（含 cloudflare 或 url-checker 关键字）。"""
    ua = (user_agent or '').lower()
    return any(kw in ua for kw in CLOUDFLARE_SCANNER_UA_KEYWORDS)


def is_trusted_cloudflare_scanner(ip, user_agent):
    """双重验证：UA 是 Cloudflare 扫描器 且 IP 属于 Cloudflare 官方 IP 段。"""
    return is_cloudflare_ip(ip) and is_cloudflare_scanner_ua(user_agent)
