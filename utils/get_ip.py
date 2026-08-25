def get_ip(request):
	"""
	获取客户端真实IP地址
	
	考虑了多种代理情况：
	1. HTTP_X_REAL_IP: nginx真实IP头部
	2. HTTP_X_FORWARDED_FOR: 标准代理头部
	3. REMOTE_ADDR: 直连IP
	
	同时过滤内网IP和IPv6地址
	"""
	# 尝试获取nginx设置的真实IP
	real_ip = request.META.get('HTTP_X_REAL_IP', '').strip()
	if real_ip and not real_ip.startswith(('127.', '192.168.', '10.', '172.', '0.')) and ':' not in real_ip:
		return real_ip
	
	# 尝试获取X-Forwarded-For中的第一个公网IP
	x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR', '').strip()
	if x_forwarded_for:
		ips = [ip.strip() for ip in x_forwarded_for.split(',') if ip.strip()]
		for ip in ips:
			# 排除内网IP和IPv6
			if not ip.startswith(('127.', '192.168.', '10.', '172.', '0.')) and ':' not in ip:
				return ip
	
	# 获取直连IP
	remote_ip = request.META.get('REMOTE_ADDR', '').strip()
	# 如果是IPv6地址，返回本地回环地址
	return remote_ip # if ':' not in remote_ip else '127.0.0.1'
