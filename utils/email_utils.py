# utils/email_utils.py
from django.core.mail import send_mail
from django.conf import settings
from datetime import datetime
import threading
import logging

logger = logging.getLogger(__name__)

def send_email_async(subject, recipient_list, html_message, text_message=None, attachments=None):
	"""
	异步发送邮件，不阻塞主线程。

	:param subject: 邮件主题
	:param recipient_list: 收件人列表，如 ['xxx@qq.com']
	:param html_message: HTML 格式邮件正文
	:param text_message: 纯文本兜底正文（可选）
	:param attachments: 附件列表，格式 [(filename, content, mimetype), ...]
	"""
	def _send():
		logger.info('send_email_async: 开始发送邮件, subject=%s', subject)
		try:
			now = datetime.now()
			final_html_message = html_message + f'<hr><p><b>此邮件由 wjw2 网站服务器自动发送，请勿回复。</b><br>发送时间: {now.year}.{now.month}.{now.day} {now.strftime("%H:%M:%S")}</p>'
			send_mail(
				subject=subject,
				message=text_message or '你的浏览器不支持HTML邮件',
				from_email=None,  # 自动使用 DEFAULT_FROM_EMAIL
				recipient_list=recipient_list or settings.DEVELOPERS,
				html_message=final_html_message,
				fail_silently=False,
			)
		except Exception as e:
			logger.exception('send_email_async: 邮件发送失败')
		else:
			logger.info('send_email_async: 发送邮件结束')

	thread = threading.Thread(target=_send, daemon=True)
	thread.start()
