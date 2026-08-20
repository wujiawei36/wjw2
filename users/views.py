from django.contrib.auth import authenticate, login, logout, get_user_model
from django.shortcuts import render, redirect
from captcha.helpers import captcha_image_url
from captcha.models import CaptchaStore

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

