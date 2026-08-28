from django.contrib.auth import authenticate, login, logout, get_user_model
from django.utils.http import url_has_allowed_host_and_scheme
from django.shortcuts import render, redirect
from captcha.helpers import captcha_image_url
from captcha.models import CaptchaStore
from utils.get_ip import get_ip
import logging

logger = logging.getLogger(__name__)

User = get_user_model()

def get_captchas():
	new_captcha_key = CaptchaStore.generate_key()
	captcha_image_url_str = captcha_image_url(new_captcha_key)
	return {'captcha_image_url': captcha_image_url_str, 'captcha_key': new_captcha_key}

def _resolve_username(raw):
	"""
	支持「用户名」或「用户ID」两种登录方式。
	返回 (真实用户名, 错误信息)；错误信息非空时直接终止登录流程。
	使用 iexact + first() 避免大小写不同的重名用户触发 MultipleObjectsReturned(500)。
	"""
	try:
		uid = int(raw)
	except (TypeError, ValueError):
		pass
	else:
		try:
			user = User.objects.get(id=uid)
			return user.username, None
		except User.DoesNotExist:
			return None, '用户名或密码错误'

	user = User.objects.filter(username__iexact=raw).order_by('id').first()
	if user is None:
		# 用户不存在时返回原始输入，交由 authenticate 统一产出「用户名或密码错误」
		return raw, None
	return user.username, None

def auth_login(request):
	nxt = request.GET.get('next')
	if request.user.is_authenticated:
		if nxt and _is_safe_next(nxt, request):
			return redirect(nxt)
		return redirect('/')

	if request.method == 'POST':
		username = request.POST.get('username', '').strip()
		password = request.POST.get('password', '')
		captcha_value = request.POST.get('captcha', '')
		captcha_key = request.POST.get('captcha_key', '')

		# 验证码校验（先校验验证码，再进行任何用户查询，避免被用于探测）
		try:
			captcha = CaptchaStore.objects.get(hashkey=captcha_key)
			if captcha.response.upper() != captcha_value.upper():
				captcha.delete()
				return render(request, 'registration/login.html', {**get_captchas(), 'errors': '验证码错误'})
			captcha.delete()
		except CaptchaStore.DoesNotExist:
			return render(request, 'registration/login.html', {**get_captchas(), 'errors': '验证码过期或无效'})

		# 用户名或用户ID解析
		username, err = _resolve_username(username)
		if err:
			return render(request, 'registration/login.html', {**get_captchas(), 'errors': err})

		# 交由 Django 认证后端完成验证（含 axes 失败计数）
		user = authenticate(request, username=username, password=password)
		if user is None:
			logger.warning('LOGIN_FAILED 用户名[%s] 来自IP[%s] 认证失败', username, get_ip(request))
			return render(request, 'registration/login.html', {**get_captchas(), 'errors': '用户名或密码错误'})
		if user.is_active:
			login(request, user)
			logger.info('LOGIN_OK 用户[%s](id=%s) 来自IP[%s] 登录成功', user.username, user.id, get_ip(request))
			if nxt and _is_safe_next(nxt, request):
				return redirect(nxt)
			return redirect('/')
		logger.warning('LOGIN_BLOCKED 用户[%s](id=%s) 账号已被禁用', user.username, user.id)
		return render(request, 'registration/login.html', {**get_captchas(), 'errors': '账号已被禁用'})

	return render(request, 'registration/login.html', get_captchas())

def _is_safe_next(url, request):
	"""防开放重定向：仅允许站内相对路径或同源地址"""
	return url_has_allowed_host_and_scheme(
		url,
		allowed_hosts={request.get_host()},
		require_https=request.is_secure(),
	)

def auth_logout(request):
	if request.user.is_authenticated:
		logger.info('LOGOUT 用户[%s](id=%s) 来自IP[%s] 退出登录', request.user.username, request.user.id, get_ip(request))
		logout(request)
	return redirect('/')
