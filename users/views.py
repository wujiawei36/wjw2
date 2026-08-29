from django.contrib.auth import authenticate, login, logout, get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils.http import url_has_allowed_host_and_scheme
from django.utils import timezone
from django.shortcuts import render, redirect
from captcha.helpers import captcha_image_url
from captcha.models import CaptchaStore
from utils.get_ip import get_ip
from .models import InviteCode
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
		# 蜜罐：正常人不会填 hidden 字段，填了即为机器人 → 静默拒绝（不提示、不消耗验证码）
		if request.POST.get('required'):
			return render(request, 'registration/login.html', get_captchas())

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


def _verify_captcha(request, captcha_value, captcha_key):
	"""验证图形验证码，通过返回 (True, None)，失败返回 (False, 错误信息)。一次性使用。"""
	try:
		captcha = CaptchaStore.objects.get(hashkey=captcha_key)
		if captcha.response.upper() != captcha_value.upper():
			captcha.delete()
			return False, '验证码错误'
		captcha.delete()
		return True, None
	except CaptchaStore.DoesNotExist:
		return False, '验证码过期或无效'


def auth_register(request):
	"""邀请码注册：前台暂不提供入口，仅保留功能（无导航链接）。"""
	if request.user.is_authenticated:
		return redirect('/')

	if request.method == 'POST':
		# 蜜罐：填了 hidden 字段的均为机器人，静默拒绝
		if request.POST.get('required'):
			return render(request, 'registration/register.html', get_captchas())

		username = request.POST.get('username', '').strip()
		password = request.POST.get('password', '')
		password_check = request.POST.get('password_check', '')
		email = request.POST.get('email', '').strip()
		invite_code = request.POST.get('invite_code', '').strip()
		captcha_value = request.POST.get('captcha', '')
		captcha_key = request.POST.get('captcha_key', '')

		# 1. 验证码
		ok, err = _verify_captcha(request, captcha_value, captcha_key)
		if not ok:
			return render(request, 'registration/register.html', {**get_captchas(), 'errors': err})

		# 2. 基础校验
		if not username or not password or not password_check or not invite_code:
			return render(request, 'registration/register.html', {**get_captchas(), 'errors': '输入项不能为空'})
		if password != password_check:
			return render(request, 'registration/register.html', {**get_captchas(), 'errors': '两次输入的密码不一致'})
		if User.objects.filter(username__iexact=username).exists():
			return render(request, 'registration/register.html', {**get_captchas(), 'errors': '用户名已被占用'})
		try:
			validate_password(password, user=None)
		except ValidationError as e:
			return render(request, 'registration/register.html', {**get_captchas(), 'errors': ' '.join(e.messages)})

		# 3. 邀请码校验 + 创建用户（事务：建用户与标记邀请码原子完成，防并发抢码）
		try:
			with transaction.atomic():
				code_obj = InviteCode.objects.select_for_update().get(code=invite_code)
				if code_obj.is_used:
					return render(request, 'registration/register.html', {**get_captchas(), 'errors': '邀请码已被使用'})
				if code_obj.is_expired:
					return render(request, 'registration/register.html', {**get_captchas(), 'errors': '邀请码已过期'})
				user = User.objects.create_user(
					username=username,
					password=password,
					email=email or None,
					is_active=True,
					is_staff=False,
					is_superuser=False,
				)
				code_obj.used_at = timezone.now()
				code_obj.used_by = user
				code_obj.save(update_fields=['used_at', 'used_by'])
		except InviteCode.DoesNotExist:
			return render(request, 'registration/register.html', {**get_captchas(), 'errors': '邀请码无效'})

		logger.info('REGISTER_OK 新用户[%s](id=%s) 使用邀请码[%s] 来自IP[%s] 注册成功',
		            user.username, user.id, invite_code, get_ip(request))
		# 多认证后端（axes + ModelBackend）下必须显式指定 backend
		login(request, user, backend='django.contrib.auth.backends.ModelBackend')
		return redirect('/')

	return render(request, 'registration/register.html', get_captchas())
