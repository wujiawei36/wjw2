from django.http import HttpResponseForbidden, HttpResponse
from django.utils.deprecation import MiddlewareMixin
from django.utils import timezone
from datetime import timedelta
from utils.get_ip import get_ip
from .models import Ban_IP
import threading
import logging
import time

logger = logging.getLogger(__name__)


class SessionInfoMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.user.is_authenticated:
            ip = get_ip(request)
            ua = request.META.get('HTTP_USER_AGENT', '')
            # 仅在发生变化时才写入 session，避免每次请求都触发数据库写入
            if request.session.get('ip_address') != ip or request.session.get('user_agent') != ua:
                request.session['ip_address'] = ip
                request.session['user_agent'] = ua
        return self.get_response(request)

# logger = logging.getLogger('django')

# ===================== 配置项 =====================
# 请求限制配置（统计窗口：10 秒）
REQUEST_BLOCKING_MIDDLEWARE__TIME = 10  # 统计窗口时间（秒）
REQUEST_BLOCKING_MIDDLEWARE__BAN_MAX_REQUEST_PER_WINDOW = 60  # 封禁IP判定阈值：60次/窗口
REQUEST_BLOCKING_MIDDLEWARE__BLOCK_MAX_REQUEST_PER_WINDOW = 30  # 限流阈值：30次/窗口
REQUEST_BLOCKING_MIDDLEWARE__BLOCK_TIME = 60  # 限流持续时间（秒）
REQUEST_BLOCKING_MIDDLEWARE__BAN_TIME = timedelta(hours=24)  # 自动封禁时长：24小时

# 白名单IP配置
WHITE_LIST_IPS = ['127.0.0.1', '::1', 'localhost']
# ==================================================

# 全局数据结构
ip_access_records = {}  # 存储IP访问记录，格式: {ip: [timestamp1, timestamp2, ...]}
ip_access_lock = threading.Lock()  # 线程锁，保证并发安全
banned_ip_cache = set()  # 缓存被封禁的IP，提高查询效率

def init_banned_ip_cache():
	"""
	初始化被封禁IP缓存
	将数据库中的封禁IP加载到内存缓存中，提高查询效率
	"""
	global banned_ip_cache
	try:
		banned_ip_cache = set(Ban_IP.objects.filter(active=True).values_list('ip', flat=True))
	except Exception:
		# 数据库尚未初始化（如未执行 migrate）时跳过，不影响启动
		banned_ip_cache = set()

def clean_all_expired_records():
	"""
	清理过期访问记录的后台线程函数
	定期清理超过时间窗口的访问记录，防止内存无限增长
	"""
	while True:
		now = time.time()
		with ip_access_lock:
			# 遍历所有IP记录，清理过期的时间戳
			for ip in list(ip_access_records.keys()):
				# 保留仍在时间窗口内的访问记录
				ip_access_records[ip] = [t for t in ip_access_records[ip] 
										if now - t < REQUEST_BLOCKING_MIDDLEWARE__TIME]
				# 如果该IP没有有效记录，则从字典中删除
				if not ip_access_records[ip]:
					del ip_access_records[ip]
		time.sleep(10)  # 每10秒执行一次清理

# 初始化缓存
init_banned_ip_cache()

# 启动后台清理线程
clean_thread = threading.Thread(target=clean_all_expired_records, daemon=True)
clean_thread.start()


class IPBlockMiddleware(MiddlewareMixin):
	"""
	IP封禁中间件
	检查请求IP是否在封禁列表中，如果是则拒绝访问
	优先级最高，最先执行
	"""
	
	def process_request(self, request):
		"""
		处理请求的核心方法
		在视图函数执行前触发，检查客户端IP是否被封禁
		"""
		# 获取客户端真实IP
		ip = get_ip(request)
		
		# 记录访问IP用于调试
		# logger.info(f'IP: {ip}; Address: {request.path_info}')
		
		# 空IP或白名单IP直接放行
		if not ip or ip in WHITE_LIST_IPS:
			return None
		
		# 首先检查内存缓存，快速拦截已知封禁IP
		if ip in banned_ip_cache:
			return HttpResponseForbidden(
				f"您的IP ({ip}) 已被封禁(缓存)，禁止访问！",
				content_type='text/plain; charset=utf-8'
			)
		
		# 检查数据库中的封禁记录
		try:
			banned_ip = Ban_IP.objects.get(ip=ip)
			# 封禁已过期：自动解除并清理记录
			if banned_ip.expires_at and banned_ip.expires_at <= timezone.now():
				banned_ip.delete()
				return None
			# 封禁记录存在但未激活，则放行
			if not banned_ip.active:
				return None
			
			# 添加到缓存，加快后续相同IP的拦截速度
			banned_ip_cache.add(ip)

			logger.warning('IP_BLOCKED IP[%s] 被封禁记录拦截, 理由: %s', ip, banned_ip.reason)
			
			# 返回封禁响应
			return HttpResponseForbidden(
				f"您的IP ({ip}) 已被封禁(查库)！封禁理由：{banned_ip.reason}",
				content_type='text/plain; charset=utf-8'
			)
		except Ban_IP.DoesNotExist:
			# IP未被封禁，正常放行
			return None


class RequestBlockingMiddleware(MiddlewareMixin):
	"""
	请求限流中间件
	实现频率限制、爬虫检测和恶意请求防护
	"""
	
	def clean_expired_records(self, ip, now):
		"""
		清理指定IP的过期访问记录
		
		Args:
			ip: 客户端IP地址
			now: 当前时间戳
		"""
		with ip_access_lock:
			if ip in ip_access_records:
				# 保留仍在时间窗口内的访问记录
				ip_access_records[ip] = [t for t in ip_access_records[ip] 
										if now - t < REQUEST_BLOCKING_MIDDLEWARE__TIME]
				# 如果清理后无记录，删除该IP键
				if not ip_access_records[ip]:
					del ip_access_records[ip]

	def process_request(self, request):
		"""
		处理请求的核心方法
		执行爬虫检测、请求频率限制等功能
		"""
		# 获取客户端真实IP
		ip = get_ip(request)
		
		# 白名单IP直接放行
		if not ip or ip in WHITE_LIST_IPS:
			return None

		# ==================== 爬虫检测 ====================
		user_agent = request.META.get('HTTP_USER_AGENT', '').lower()
		
		# 1. 基础爬虫检测：检查常见爬虫User-Agent
		if not user_agent or any(bot in user_agent for bot in [
			'python-requests', 'curl', 'wget', 'scrapy', 'bot', 'spider'
		]):
			return HttpResponseForbidden(
				"非法请求：爬虫/脚本UA禁止访问", 
				status=403, 
				content_type='text/plain; charset=utf-8'
			)
		
		# 2. 高级爬虫检测：验证浏览器必需的请求头
		required_headers = [
			'HTTP_ACCEPT',           # 浏览器必传：接受的内容类型
			# 'HTTP_ACCEPT_ENCODING',  # 浏览器必传：gzip/deflate编码支持
			'HTTP_ACCEPT_LANGUAGE',  # 浏览器必传：语言偏好设置
			'HTTP_CONNECTION'        # 浏览器必传：连接方式
		]
		
		# 检查是否缺少必需的请求头
		missing_headers = [header for header in required_headers 
						  if not request.META.get(header, '').strip()]
		
		if len(missing_headers) >= 2:
			return HttpResponseForbidden(
				"非法请求：爬虫/脚本伪装浏览器访问，禁止访问！", 
				status=403, 
				content_type='text/plain; charset=utf-8'
			)

		# 3. 无头浏览器检测：识别自动化工具
		if any(headless_tool in user_agent for headless_tool in [
			'headless', 'selenium', 'playwright', 'puppeteer', 'phantomjs'
		]):
			return HttpResponseForbidden(
				"非法请求：无头浏览器/自动化脚本禁止访问！", 
				status=403, 
				content_type='text/plain; charset=utf-8'
			)

		# ==================== 请求频率限制 ====================
		now = time.time()
		
		# 清理该IP的过期访问记录
		self.clean_expired_records(ip, now)

		# 记录本次访问并计算当前窗口内的请求数
		with ip_access_lock:
			current_records = ip_access_records.get(ip, [])
			current_records.append(now)
			current_count = len(current_records)
			ip_access_records[ip] = current_records

		# 检查是否达到封禁阈值（60次/窗口）
		if current_count >= REQUEST_BLOCKING_MIDDLEWARE__BAN_MAX_REQUEST_PER_WINDOW:
			# 创建/更新封禁记录（自动封禁默认24小时，过期自动解除）
			Ban_IP.objects.update_or_create(
				ip=ip,
				defaults={
					'reason': f"高频请求超限({current_count}次/{REQUEST_BLOCKING_MIDDLEWARE__TIME}秒)",
					'active': True,
					'expires_at': timezone.now() + REQUEST_BLOCKING_MIDDLEWARE__BAN_TIME,
				}
			)
			
			# 添加到缓存，立即生效
			banned_ip_cache.add(ip)

			logger.warning('AUTO_BAN IP[%s] 因高频请求(%d次/%ds)被自动封禁24小时, UA=[%s]',
			               ip, current_count, REQUEST_BLOCKING_MIDDLEWARE__TIME, user_agent)
			
			# 返回封禁响应
			return HttpResponseForbidden(
				f"您的IP ({ip}) 因高频访问已被临时封禁，请稍后再试！",
				content_type='text/plain; charset=utf-8'
			)

		# 检查是否达到限流阈值（30次/窗口）
		elif current_count >= REQUEST_BLOCKING_MIDDLEWARE__BLOCK_MAX_REQUEST_PER_WINDOW:
			# 返回限流响应，使用标准HTTP状态码429
			return HttpResponse(
				f"访问频率过高，触发限流保护！请{REQUEST_BLOCKING_MIDDLEWARE__BLOCK_TIME}秒后重试",
				status=429,
				headers={'Retry-After': str(REQUEST_BLOCKING_MIDDLEWARE__BLOCK_TIME)},
				content_type='text/plain; charset=utf-8'
			)
		
		# 所有检查通过，正常放行请求
		return None
