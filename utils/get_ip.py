from django.conf import settings

def get_ip(request):
	"""
	获取客户端IP地址。

	安全策略（默认）：只信任 TCP 层直连地址 REMOTE_ADDR。
	客户端可随意伪造 X-Real-IP / X-Forwarded-For 头，因此只有在确认
	部署在可信反向代理（nginx/caddy 等）之后，且代理会覆盖这些头时，
	才应设置 settings.TRUST_PROXY = True，由代理提供的头来取真实IP。

	使用建议：
	1. 直接对外（runserver / gunicorn 直连）: TRUST_PROXY = False（默认）
	2. 位于 nginx 之后: nginx 配置
	       proxy_set_header X-Real-IP $remote_addr;
	       proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
	   同时 settings.TRUST_PROXY = True
	"""
	remote_addr = request.META.get('REMOTE_ADDR', '').strip()

	if not getattr(settings, 'TRUST_PROXY', False):
		# 不信任代理头，直接返回直连地址
		return remote_addr

	# 信任代理场景：nginx 场景优先取 X-Real-IP
	real_ip = request.META.get('HTTP_X_REAL_IP', '').strip()
	if real_ip:
		return real_ip

	# 其次取 X-Forwarded-For 中"最后一个"地址（由最近的代理追加，
	# 左侧地址可被客户端伪造，右侧更接近真实来源）
	x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR', '').strip()
	if x_forwarded_for:
		ips = [ip.strip() for ip in x_forwarded_for.split(',') if ip.strip()]
		if ips:
			return ips[-1]

	return remote_addr
