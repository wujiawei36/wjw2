from django.contrib.auth import authenticate, login, logout, get_user_model
from django.utils.http import urlsafe_base64_encode,urlsafe_base64_decode
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from utils.email_utils import send_email_async
from django.shortcuts import render, redirect
from captcha.helpers import captcha_image_url
from django.utils.encoding import force_bytes
from django.utils.encoding import force_str
from utils.tokens import activation_token
from captcha.models import CaptchaStore
from django.http import HttpResponse
from django.conf import settings
from django.urls import reverse


User = get_user_model()

# utils

def online(user):
	return user.is_authenticated

def _merge(a,b):
	return {**a,**b}

def get_captchas():
	new_captcha_key = CaptchaStore.generate_key()
	captcha_image_url_str = captcha_image_url(new_captcha_key)
	return {'captcha_image_url':captcha_image_url_str, 'captcha_key':new_captcha_key}

def upper(s):
	return s.upper()


# views

def auth_login(request):
	nxt = request.GET.get('next', None)
	if online(request.user):
		if nxt is None:
			return redirect(to='/')
		else:
			return redirect(nxt)
	if request.method == 'POST':
		username = request.POST['username']
		password = request.POST['password']
		captcha_value = request.POST.get('captcha')
		captcha_key = request.POST.get('captcha_key')

		try:
			username = int(username)
		except:
			1+1
		else:
			try:
				username = User.objects.get(id=int(username))
			except User.DoesNotExist:
				return render(request, 'registration/login.html', _merge({'errors': '用户名或密码错误'}, get_captchas()))
			username = username.username
		try:
			captcha = CaptchaStore.objects.get(hashkey=captcha_key)
			if upper(captcha.response) != upper(captcha_value):
				captcha.delete()
				return render(request, 'registration/login.html', _merge({'errors': '验证码错误'}, get_captchas()))
			captcha.delete()
		except CaptchaStore.DoesNotExist:
			return render(request, 'registration/login.html', _merge({'errors': '验证码过期或无效'}, get_captchas()))

		try:
			user = User.objects.get(username__iexact=username)
		except User.DoesNotExist:
			return render(request, 'registration/login.html', _merge({'errors': '用户名或密码错误'}, get_captchas()))
		user = authenticate(username=user.username, password=password)
		if user is None:
			return render(request, 'registration/login.html', _merge({'errors': '用户名或密码错误'}, get_captchas()))
		if user.is_active:
			login(request,user)
			if nxt is None:
				return redirect('/')
			else:
				return redirect(nxt)
		return render(request, 'registration/login.html', _merge({'errors': '账号已被禁用'}, get_captchas()))

	return render(request, 'registration/login.html', get_captchas())

def auth_logout(request):
	if online(request.user):
		logout(request)
	return redirect('/')

# def auth_register(request):
# 	if online(request.user):
# 		return redirect(to='/')
# 	if request.method == 'POST':
# 		if request.POST.get('required'):
# 			return redirect(to='/')
# 		username = request.POST['username'].strip()
# 		password = request.POST['password'].strip()
# 		password_check = request.POST['password_check'].strip()
# 		email = request.POST['email'].strip()
# 		captcha_value = request.POST.get('captcha')
# 		captcha_key = request.POST.get('captcha_key')

# 		if not password==password_check:
# 			return render(request, 'registration/register.html', _merge({'errors': '密码不匹配'}, get_captchas()))

# 		if not username.strip() or not password.strip() or not password_check.strip() or not email.strip():
# 			return render(request, 'registration/register.html', _merge({'errors': '输入项不能为空'}, get_captchas()))

# 		try:
# 			captcha = CaptchaStore.objects.get(hashkey=captcha_key)
# 			if upper(captcha.response) != upper(captcha_value):
# 				captcha.delete()
# 				return render(request, 'registration/register.html', _merge({'errors': '验证码错误'}, get_captchas()))
# 			captcha.delete()
# 		except CaptchaStore.DoesNotExist:
# 			return render(request, 'registration/register.html', _merge({'errors': '验证码过期或无效'}, get_captchas()))

# 		# 手动校验密码强度
# 		try:
# 			validate_password(password, user=None)  # user=None 表示暂不检查与用户信息的相似度
# 		except ValidationError as e:
# 			# 如果密码太弱，会把所有错误信息收集起来
# 			error_messages = ' '.join(e.messages)
# 			return render(request, 'registration/register.html', _merge({'errors': error_messages}, get_captchas()))

# 		if User.objects.filter(username=username).exists():
# 			return render(request, 'registration/register.html', _merge({'errors': '用户名已被占用'}, get_captchas()))
# 		if User.objects.filter(email=email).exists():
# 			return render(request, 'registration/register.html', _merge({'errors': '邮箱已被占用'}, get_captchas()))
# 		user = User.objects.create_user(username=username,password=password,is_staff=False,is_active=False,is_superuser=False,need_email_active=True)

# 		# 2. 生成Token
# 		token = activation_token.make_token(user)
# 		# 3. 生成安全的用户ID
# 		uid = urlsafe_base64_encode(force_bytes(user.pk))
# 		# 4. 构建完整激活链接[reference:5]
# 		activation_link = request.build_absolute_uri(
# 			reverse('users:auth_activate', kwargs={'uidb64': uid, 'token': token})
# 		)
# 		print(activation_link)
# 		send_email_async(
# 			subject='【wjw2网站】激活你的账户',
# 			recipient_list=[email],
# 			html_message=f'<a href={activation_link}>单击此处</a>以激活你的账户。<br>如果你没有进行此操作，则可以安全地忽略此邮件。',
# 		)
# 		return HttpResponse("已发送激活邮件，请检查你的邮箱")

# 	return render(request, 'registration/register.html', get_captchas())

# def auth_activate(request, uidb64, token):
# 	try:
# 		uid = force_str(urlsafe_base64_decode(uidb64))
# 		user = User.objects.get(pk=uid, is_active=False, need_email_active=True) # 确保是未激活用户[reference:8]
# 	except (TypeError, ValueError, OverflowError, User.DoesNotExist):
# 		user = None

# 	if user is not None and activation_token.check_token(user, token):
# 		user.is_active = True
# 		user.need_email_active=False
# 		user.save()
# 		login(request,user)
# 		return redirect(to='/')
# 	else:
# 		return HttpResponse("激活链接无效或已过期")
