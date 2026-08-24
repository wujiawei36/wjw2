from utils.get_ip import get_ip

class SessionInfoMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response
        print('=== SessionInfoMiddleware loaded ===')  # 加这行

    def __call__(self, request):
        if request.user.is_authenticated:
            print(f'=== IP: {get_ip(request)} ===')  # 加这行
            request.session['ip_address'] = get_ip(request)
            request.session['user_agent'] = request.META.get('HTTP_USER_AGENT', '')
        return self.get_response(request)
