from utils.get_ip import get_ip

class SessionInfoMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.user.is_authenticated:
            # 每次请求都更新 session 里的 IP 和 UA
            request.session['ip_address'] = get_ip(request)
            request.session['user_agent'] = request.META.get('HTTP_USER_AGENT', '')
        return self.get_response(request)
