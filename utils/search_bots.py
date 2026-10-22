"""搜索引擎爬虫识别（用于放行正规收录，避免 UA 黑名单误伤）。

背景：
    users.middleware.RequestBlockingMiddleware 的 UA 黑名单含 'bot' 关键字，
    会把 bingbot / googlebot 等正规搜索引擎一并拦截，并返回纯文本 403
    （无 <body> 标签）。后果是站点无法被搜索引擎收录，Bing 站点验证也会
    报 "Body tag not found"。

策略：
    仅匹配各搜索引擎官方 UA 中的稳定特征串（含版本斜杠，降低误伤），
    命中后跳过爬虫检测（UA 黑名单 / 缺头拦截 / 无头浏览器），
    但仍受频率限流约束（30 次/10 秒）。

风险说明：
    UA 可被伪造。伪造者可获得与匿名访客相同的公开内容访问能力，
    敏感数据仍由登录态和权限校验保护；此处换取的是搜索引擎可收录，
    属于可接受的权衡。若日后需要更强保证，可增加反向 DNS 校验
    （Bingbot: *.search.msn.com，Googlebot: *.googlebot.com）。
"""

# 官方 UA 特征串（统一小写匹配）
SEARCH_BOT_SIGNATURES = (
    'bingbot/',          # Bing：... bingbot/2.0; +http://www.bing.com/bingbot.htm
    'googlebot/',        # Google：... Googlebot/2.1; +http://www.google.com/bot.html
    'baiduspider/',      # 百度：... Baiduspider/2.0
    'duckduckbot/',      # DuckDuckGo
    'yandexbot/',        # Yandex
    'applebot/',         # Apple
    'sogou web spider/',  # 搜狗
    '360spider',         # 360 搜索
    'bytespider',        # 字节跳动
)


def is_search_engine_bot(user_agent: str) -> bool:
    """判断 UA 是否属于已知搜索引擎爬虫。"""
    ua = (user_agent or '').lower()
    if not ua:
        return False
    return any(sig in ua for sig in SEARCH_BOT_SIGNATURES)
