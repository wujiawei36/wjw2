from django.http import HttpResponse
from django.shortcuts import render
from django.utils import timezone
from tool.registry import TOOLS
from users.models import PageVisit

FEATURED_TOOL_SLUGS = ['json', 'timestamp', 'base64', 'uuid', 'password', 'qrcode', 'sha', 'number']


def _page_visit_stats():
    """返回 (today, total)：今日访问需校验统计日期是否为今天（跨天未访问时旧值作废）。"""
    visit = PageVisit.objects.filter(pk=1).first()
    if visit is None:
        return 0, 0
    today = visit.today_count if visit.date == timezone.localdate() else 0
    return today, visit.total_count


# views
def index(request):
    tools = [t for t in TOOLS if t['slug'] in FEATURED_TOOL_SLUGS]
    visit_today, visit_total = _page_visit_stats()
    return render(request, 'index/index.html', {
        'tools': tools,
        'visit_today': visit_today,
        'visit_total': visit_total,
    })

def robots(request):
    """robots.txt：禁止搜索引擎收录后台/私有页面，公开页面正常放行。

    说明：robots.txt 只约束遵守协议的爬虫（搜索引擎），恶意爬虫不遵守，
    真正的防爬由 RequestBlockingMiddleware + IP 限流/封禁负责。
    """
    content = (
        '# robots.txt\n'
        '# Public pages are open to search engines; private areas are blocked.\n'
        '\n'
        'User-agent: *\n'
        'Disallow: /admin/\n'
        'Disallow: /panel/\n'
        'Disallow: /user/\n'
        'Disallow: /captcha/\n'
        'Disallow: /hijack/\n'
        'Disallow: /tools/api/\n'
        'Disallow: /health/\n'
        '\n'
        'Allow: /\n'
    )
    return HttpResponse(content, content_type='text/plain; charset=utf-8')

def about(request):
    return render(request,'index/about.html')


def health(request):
    """健康检查端点：供脚本/监控探针探测站点是否存活，仅返回 200。

    说明：uptime 监控、拨测脚本通常不带浏览器请求头（无 Accept/Accept-Language、
    UA 为 curl/python-requests 等），因此在中间件层跳过爬虫检测，但仍保留
    频率限流，防止被刷爆。
    """
    return HttpResponse('ok', content_type='text/plain; charset=utf-8')
