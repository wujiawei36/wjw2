from django.contrib.auth import authenticate, login, logout, get_user_model, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.contrib.auth.password_validation import validate_password
from django.contrib.sessions.models import Session
from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils.http import url_has_allowed_host_and_scheme
from django.utils import timezone
from datetime import timedelta
from django.shortcuts import render, redirect, get_object_or_404
from django_otp import match_token
from django_otp.plugins.otp_totp.models import TOTPDevice
from django_otp.plugins.otp_static.models import StaticDevice, StaticToken
from captcha.helpers import captcha_image_url
from captcha.models import CaptchaStore
from utils.get_ip import get_ip
from .models import InviteCode
import base64
import io
import logging
import qrcode
from base64 import b32encode

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
		# 同时删除本次提交的验证码记录，避免每次渲染新验证码导致旧记录残留
		if request.POST.get('required'):
			CaptchaStore.objects.filter(hashkey=request.POST.get('captcha_key', '')).delete()
			return render(request, 'registration/login.html', get_captchas())

		username = request.POST.get('username', '').strip()
		password = request.POST.get('password', '')
		captcha_value = request.POST.get('captcha', '')
		captcha_key = request.POST.get('captcha_key', '')

		# 验证码校验（先校验验证码，再进行任何用户查询，避免被用于探测）
		ok, err = _verify_captcha(request, captcha_value, captcha_key)
		if not ok:
			return render(request, 'registration/login.html', {**get_captchas(), 'errors': err})

		# 用户名或用户ID解析
		username, err = _resolve_username(username)
		if err:
			return render(request, 'registration/login.html', {**get_captchas(), 'errors': err})

		# 交由 Django 认证后端完成验证（含 axes 失败计数）
		user = authenticate(request, username=username, password=password)
		if user is None:
			logger.warning('LOGIN_FAILED 用户名[%s] 来自IP[%s] 认证失败', username, get_ip(request))
			return render(request, 'registration/login.html', {**get_captchas(), 'errors': '用户名或密码错误'})
		if not user.is_active:
			logger.warning('LOGIN_BLOCKED 用户[%s](id=%s) 账号已被禁用', user.username, user.id)
			return render(request, 'registration/login.html', {**get_captchas(), 'errors': '账号已被禁用'})

		# 两步验证：密码通过后，若用户已启用 2FA，暂存身份转第二步输入动态码/恢复代码
		if _user_has_2fa(user):
			request.session['2fa_user_id'] = user.id
			request.session['2fa_next'] = nxt if (nxt and _is_safe_next(nxt, request)) else ''
			request.session['2fa_attempts'] = 0
			return redirect('users:otp_login')

		login(request, user)
		logger.info('LOGIN_OK 用户[%s](id=%s) 来自IP[%s] 登录成功', user.username, user.id, get_ip(request))
		if nxt and _is_safe_next(nxt, request):
			return redirect(nxt)
		return redirect('/')

	return render(request, 'registration/login.html', get_captchas())

def _is_safe_next(url, request):
	"""防开放重定向：仅允许站内相对路径或同源地址"""
	return url_has_allowed_host_and_scheme(
		url,
		allowed_hosts={request.get_host()},
		require_https=request.is_secure(),
	)


def _user_has_2fa(user):
	"""判断用户是否已启用两步验证（存在已确认的 TOTP 设备）。"""
	return TOTPDevice.objects.devices_for_user(user, confirmed=True).exists()


def auth_otp(request):
	"""两步验证第二步：输入 6 位动态码或恢复代码，验证通过后完成登录。

	第一步（auth_login）通过密码验证后，会把待登录用户 id 暂存进 session
	（2fa_user_id / 2fa_next / 2fa_attempts），本视图据此完成最终登录。
	"""
	user_id = request.session.get('2fa_user_id')
	if not user_id:
		return redirect('users:login')
	try:
		user = User.objects.get(id=user_id)
	except User.DoesNotExist:
		request.session.pop('2fa_user_id', None)
		request.session.pop('2fa_next', None)
		request.session.pop('2fa_attempts', None)
		return redirect('users:login')

	if request.method == 'POST':
		token = request.POST.get('token', '').strip()
		device = match_token(user, token)
		if device is not None:
			nxt = request.session.pop('2fa_next', '')
			request.session.pop('2fa_user_id', None)
			request.session.pop('2fa_attempts', None)
			user.otp_device = device
			login(request, user, backend='django.contrib.auth.backends.ModelBackend')
			logger.info('LOGIN_OK 用户[%s](id=%s) 来自IP[%s] 两步验证登录成功',
			            user.username, user.id, get_ip(request))
			if nxt and _is_safe_next(nxt, request):
				return redirect(nxt)
			return redirect('/')

		attempts = request.session.get('2fa_attempts', 0) + 1
		request.session['2fa_attempts'] = attempts
		if attempts >= 5:
			request.session.pop('2fa_user_id', None)
			request.session.pop('2fa_next', None)
			request.session.pop('2fa_attempts', None)
			logger.warning('OTP_FAILED 用户[%s](id=%s) 来自IP[%s] 验证码连续错误5次',
			               user.username, user.id, get_ip(request))
			return redirect('users:login')
		return render(request, 'users/login_otp.html', {'errors': '验证码错误，还可尝试 %d 次' % (5 - attempts)})

	return render(request, 'users/login_otp.html')


def _qr_data_uri(data):
	"""把 otpauth:// URI 生成二维码 PNG 的内联 data URI，供 <img> 直接展示。"""
	qr = qrcode.QRCode(version=1, box_size=10, border=4)
	qr.add_data(data)
	qr.make(fit=True)
	img = qr.make_image(fill_color='black', back_color='white')
	buf = io.BytesIO()
	img.save(buf, format='PNG')
	return 'data:image/png;base64,' + base64.b64encode(buf.getvalue()).decode()


def _generate_recovery_codes(user, count=8):
	"""删除旧恢复代码并生成 count 个新的一次性恢复代码，返回明文列表（仅本次展示）。"""
	StaticDevice.objects.filter(user=user).delete()
	static_device = StaticDevice.objects.create(user=user, name='恢复代码', confirmed=True)
	codes = []
	for _ in range(count):
		token = StaticToken.random_token()
		StaticToken.objects.create(device=static_device, token=token)
		codes.append(token)
	return codes

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
		# 蜜罐：填了 hidden 字段的均为机器人，静默拒绝；同时删除本次验证码记录防残留
		if request.POST.get('required'):
			CaptchaStore.objects.filter(hashkey=request.POST.get('captcha_key', '')).delete()
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


def user_profile(request, user_id):
	"""用户主页：展示用户名/编号/最后登录时间；有 view_customuser 权限者额外看权限信息。

	右上角用户名链接指向 /user/<id>/。基础信息（用户名、编号、最后登录时间）
	对所有访问者可见（含未登录）；can_develop/superuser/active 等权限信息仅当
	访问者具备 view_customuser 权限（如超级用户或已授权的管理员）时展示。
	匿名访问者 has_perm 恒为 False，天然看不到权限信息。
	"""
	profile_user = get_object_or_404(User, id=user_id)
	can_view_user = request.user.has_perm('users.view_customuser')
	return render(request, 'users/profile.html', {
		'profile_user': profile_user,
		'can_view_user': can_view_user,
	})


@login_required
def user_settings(request):
	"""用户设置列表页：当前仅提供「修改密码」入口，后续可扩展 2FA 等。"""
	return render(request, 'users/settings.html')


@login_required
def user_change_password(request):
	"""修改密码：校验原密码 → 两次新密码一致 → 密码强度 → 更新并保持登录态。"""
	if request.method == 'POST':
		old_password = request.POST.get('old_password', '')
		new_password1 = request.POST.get('new_password1', '')
		new_password2 = request.POST.get('new_password2', '')

		if not old_password or not new_password1 or not new_password2:
			return render(request, 'users/change_password.html', {'errors': '输入项不能为空'})
		if not request.user.check_password(old_password):
			return render(request, 'users/change_password.html', {'errors': '原密码错误'})
		if new_password1 != new_password2:
			return render(request, 'users/change_password.html', {'errors': '两次输入的新密码不一致'})
		if new_password1 == old_password:
			return render(request, 'users/change_password.html', {'errors': '新密码不能与原密码相同'})
		try:
			validate_password(new_password1, user=request.user)
		except ValidationError as e:
			return render(request, 'users/change_password.html', {'errors': ' '.join(e.messages)})

		request.user.set_password(new_password1)
		request.user.save(update_fields=['password'])
		update_session_auth_hash(request, request.user)
		logger.info('PASSWORD_CHANGE 用户[%s](id=%s) 来自IP[%s] 修改密码成功',
		            request.user.username, request.user.id, get_ip(request))
		return render(request, 'users/change_password.html', {'success': '密码修改成功'})

	return render(request, 'users/change_password.html')


@login_required
def two_factor_setup(request):
	"""两步验证管理页：启用（二维码 + 明文 secret + 输码确认）、重新生成恢复代码、禁用。

	流程用 session 里的 2fa_setup_device_id 关联「未确认设备」，
	确认通过后设备置为 confirmed 并生成 8 个一次性恢复代码（仅本次展示明文）。
	"""
	user = request.user
	context = {}

	if request.method == 'POST':
		action = request.POST.get('action', '')

		if action == 'enable':
			# 生成未确认设备，展示二维码 + 明文 secret，等待输码确认
			TOTPDevice.objects.filter(user=user, confirmed=False).delete()
			device = TOTPDevice.objects.create(user=user, name='默认验证器', confirmed=False)
			request.session['2fa_setup_device_id'] = device.id
			context.update({
				'setup_step': 'confirm',
				'qr_data_uri': _qr_data_uri(device.config_url),
				'secret': b32encode(device.bin_key).decode(),
			})

		elif action == 'confirm':
			device_id = request.session.get('2fa_setup_device_id')
			device = TOTPDevice.objects.filter(id=device_id, user=user, confirmed=False).first()
			if device is None:
				context.update({'setup_step': 'start', 'errors': '绑定会话已过期，请重新启用'})
			else:
				token = request.POST.get('token', '').strip()
				if device.verify_token(token):
					device.confirmed = True
					device.save()
					request.session.pop('2fa_setup_device_id', None)
					recovery_codes = _generate_recovery_codes(user)
					logger.info('TWO_FA_ENABLED 用户[%s](id=%s) 来自IP[%s] 启用两步验证',
					            user.username, user.id, get_ip(request))
					context.update({'setup_step': 'enabled', 'recovery_codes': recovery_codes})
				else:
					context.update({
						'setup_step': 'confirm',
						'qr_data_uri': _qr_data_uri(device.config_url),
						'secret': b32encode(device.bin_key).decode(),
						'errors': '验证码错误，请重试',
					})

		elif action == 'cancel':
			TOTPDevice.objects.filter(user=user, confirmed=False).delete()
			request.session.pop('2fa_setup_device_id', None)
			context['setup_step'] = 'start'

		elif action == 'disable':
			TOTPDevice.objects.filter(user=user).delete()
			StaticDevice.objects.filter(user=user).delete()
			logger.info('TWO_FA_DISABLED 用户[%s](id=%s) 来自IP[%s] 禁用两步验证',
			            user.username, user.id, get_ip(request))
			context.update({'setup_step': 'start', 'success': '两步验证已禁用'})

		elif action == 'regenerate':
			recovery_codes = _generate_recovery_codes(user)
			logger.info('TWO_FA_RECOVERY 用户[%s](id=%s) 来自IP[%s] 重新生成恢复代码',
			            user.username, user.id, get_ip(request))
			context.update({'setup_step': 'enabled', 'recovery_codes': recovery_codes})

		else:
			context['setup_step'] = 'start'

		return render(request, 'users/two_factor_setup.html', context)

	# GET：展示当前状态
	context['setup_step'] = 'enabled' if _user_has_2fa(user) else 'start'
	return render(request, 'users/two_factor_setup.html', context)


@login_required
def user_sessions(request):
	"""会话管理：列出当前用户的所有活跃会话，支持踢出指定设备（删除对应 Session）。

	Session 数据由 SessionInfoMiddleware 写入 ip_address / user_agent；
	遍历未过期 Session 并 decode 匹配 _auth_user_id 即为本人会话。
	"""
	if request.method == 'POST':
		action = request.POST.get('action', 'kick_one')
		if action == 'kick_all':
			# 登出所有其它设备（保留当前会话）
			now = timezone.now()
			kicked = 0
			for s in Session.objects.filter(expire_date__gt=now):
				if s.session_key == request.session.session_key:
					continue
				data = s.get_decoded()
				if str(data.get('_auth_user_id')) == str(request.user.id):
					s.delete()
					kicked += 1
			if kicked:
				logger.info('SESSION_KICKED_ALL 用户[%s](id=%s) 登出%d个其它会话 来自IP[%s]',
				            request.user.username, request.user.id, kicked, get_ip(request))
		else:
			session_key = request.POST.get('session_key', '')
			# 当前会话不允许在此踢出（应走「退出登录」）
			if session_key and session_key != request.session.session_key:
				s = Session.objects.filter(session_key=session_key).first()
				if s is not None:
					data = s.get_decoded()
					if str(data.get('_auth_user_id')) == str(request.user.id):
						s.delete()
						logger.info('SESSION_KICKED 用户[%s](id=%s) 踢出会话[%s] 来自IP[%s]',
						            request.user.username, request.user.id, session_key[:8], get_ip(request))

	sessions = []
	now = timezone.now()
	cookie_age = timedelta(seconds=getattr(settings, 'SESSION_COOKIE_AGE', 1209600))
	for s in Session.objects.filter(expire_date__gt=now).order_by('-expire_date'):
		data = s.get_decoded()
		if str(data.get('_auth_user_id')) == str(request.user.id):
			sessions.append({
				'session_key': s.session_key,
				'ip': data.get('ip_address', '未知'),
				'user_agent': data.get('user_agent', '未知'),
				'last_activity': s.expire_date - cookie_age,
				'is_current': s.session_key == request.session.session_key,
			})

	other_count = sum(1 for s in sessions if not s['is_current'])
	return render(request, 'users/sessions.html', {'sessions': sessions, 'other_count': other_count})


@login_required
def login_history(request):
	"""登录历史：展示本人最近 20 条成功登录记录（axes AccessLog）。

	失败尝试在 AccessFailureLog，不给普通用户看（避免泄露他人探测痕迹）。
	"""
	from axes.models import AccessLog
	records = AccessLog.objects.filter(username=request.user.username).order_by('-attempt_time')[:20]
	history = [
		{
			'ip': r.ip_address,
			'user_agent': r.user_agent,
			'attempt_time': r.attempt_time,
			'logout_time': r.logout_time,
		}
		for r in records
	]
	return render(request, 'users/login_history.html', {'history': history})
