from django.http import HttpResponse
from django.shortcuts import render

# views
def index(request):
    return render(request,'index/index.html')

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
        '\n'
        'Allow: /\n'
    )
    return HttpResponse(content, content_type='text/plain; charset=utf-8')

def about(request):
    return render(request,'index/about.html')
