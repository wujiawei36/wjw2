from django.test import TestCase, RequestFactory
from django.contrib.auth import authenticate, get_user_model
from users.models import PageVisit

User = get_user_model()


class AxesLockoutTests(TestCase):
    """验证 axes 组合锁定不会误封同一 IP 下的其它用户"""

    def setUp(self):
        self.user_a = User.objects.create_user(username='axes_user_a', password='pass-a-123456')
        self.user_b = User.objects.create_user(username='axes_user_b', password='pass-b-123456')
        self.rf = RequestFactory()

    def _request(self):
        # 所有请求都来自同一 IP（127.0.0.1）
        return self.rf.post('/user/login/')

    def _failures(self, req, username):
        from axes.handlers.proxy import AxesProxyHandler
        return AxesProxyHandler.get_failures(req, {'username': username})

    def test_same_ip_other_user_not_blocked(self):
        """user_a 连续失败 5 次被锁，user_b 在同一 IP 应仍可正常登录"""
        req = self._request()
        for _ in range(5):
            authenticate(request=req, username='axes_user_a', password='wrong-password')

        # user_a 失败计数达到阈值，即使密码正确也被拒绝
        self.assertGreaterEqual(self._failures(req, 'axes_user_a'), 5)
        self.assertIsNone(
            authenticate(request=req, username='axes_user_a', password='pass-a-123456'),
            '被锁定的 user_a 即使密码正确也应被拒绝',
        )

        # user_b 在同一 IP 不应受影响
        user = authenticate(request=req, username='axes_user_b', password='pass-b-123456')
        self.assertIsNotNone(user, '同一 IP 下的其它用户不应被误封')
        self.assertEqual(user.username, 'axes_user_b')

    def test_lock_only_applies_to_same_username(self):
        """user_a 被锁不影响其它 IP 下的 user_a，也不影响 user_b"""
        req = self._request()
        for _ in range(5):
            authenticate(request=req, username='axes_user_a', password='wrong-password')

        # user_b 的失败计数应保持 0（组合锁定：user_a 的失败与 user_b 无关）
        self.assertEqual(self._failures(req, 'axes_user_b'), 0)


class PageVisitMiddlewareTests(TestCase):
    """访问埋点：普通页面记录，静态/管理/panel/验证码路径不记录"""

    def test_normal_page_recorded(self):
        self.client.get('/')
        self.assertEqual(PageVisit.objects.count(), 1)
        visit = PageVisit.objects.first()
        self.assertEqual(visit.path, '/')
        self.assertEqual(visit.ip, '127.0.0.1')

    def test_visit_logged_to_django_log(self):
        """每次访问应落一条 PAGE_VISIT 日志（django.log 保留 7 天，是表数据的完整备份）"""
        with self.assertLogs('users.middleware', level='INFO') as cm:
            self.client.get('/')
        self.assertTrue(
            any('PAGE_VISIT 200 GET /' in line for line in cm.output),
            '应输出 PAGE_VISIT 访问日志',
        )

    def test_excluded_paths_not_recorded(self):
        for url in ['/static/anything.css', '/admin/login/', '/panel/', '/captcha/refresh/']:
            self.client.get(url)
        self.assertEqual(PageVisit.objects.count(), 0)


class RequestBlockingHeaderTests(TestCase):
    """缺头检测：Accept 与 Accept-Language 缺一即拦（不能依赖 Connection，平台会注入）"""

    def _middleware(self):
        from users.middleware import RequestBlockingMiddleware
        return RequestBlockingMiddleware(lambda r: None)

    def test_curl_like_request_blocked(self):
        """curl 型请求：伪造 UA + 仅带 Accept，即使平台注入 Connection 也应被拦截"""
        from django.test import RequestFactory
        rf = RequestFactory()
        req = rf.get('/about/', REMOTE_ADDR='8.8.8.8',
                     HTTP_USER_AGENT='luan-ma',
                     HTTP_ACCEPT='*/*',
                     HTTP_CONNECTION='keep-alive')  # 模拟 PythonAnywhere 平台注入
        resp = self._middleware().process_request(req)
        self.assertIsNotNone(resp, '缺 Accept-Language 的 curl 请求应被拦截')
        self.assertEqual(resp.status_code, 403)

    def test_browser_like_request_passes(self):
        """浏览器型请求：UA + Accept + Accept-Language 齐全应放行"""
        from django.test import RequestFactory
        rf = RequestFactory()
        req = rf.get('/about/', REMOTE_ADDR='8.8.8.8',
                     HTTP_USER_AGENT='Mozilla/5.0 (Macintosh; Intel Mac OS X) Chrome/120.0',
                     HTTP_ACCEPT='text/html,application/xhtml+xml',
                     HTTP_ACCEPT_LANGUAGE='zh-CN,zh;q=0.9')
        resp = self._middleware().process_request(req)
        self.assertIsNone(resp, '浏览器请求不应被拦截')



class SessionAdminLeakTests(TestCase):
    """会话管理页绝不能泄露完整 session key（防会话劫持）"""

    def setUp(self):
        from django.contrib.sessions.models import Session
        self.Session = Session
        # 创建一个持有 view_session 权限的 staff 账号
        from django.contrib.auth.models import Permission
        from django.contrib.contenttypes.models import ContentType
        self.observer = User.objects.create_user(username='session_viewer', password='pass-view-123456', is_staff=True)
        ct = ContentType.objects.get_for_model(self.Session)
        self.observer.user_permissions.add(Permission.objects.get(content_type=ct, codename='view_session'))

    def test_session_list_page_never_exposes_key(self):
        # 伪造一条会话记录（完整 32 位 key）
        self.Session.objects.create(session_key='a' * 32, session_data='', expire_date='2030-01-01T00:00:00Z')
        self.client.force_login(self.observer)
        resp = self.client.get('/admin/sessions/session/')
        self.assertEqual(resp.status_code, 200)
        body = resp.content.decode()
        # 完整 key 绝不能出现在页面上（文本/checkbox value/aria-label/URL 均不可）
        self.assertNotIn('a' * 32, body)
        # admin action checkbox 的 value 就是主键，必须确认没有渲染 checkbox
        self.assertNotIn('action-checkbox', body)
        self.assertNotIn('_selected_action', body)


class InviteCodeAdminTests(TestCase):
    """后台新建邀请码：code 留空应自动生成，而不是报必填错误"""

    def setUp(self):
        from django.utils import timezone
        self.admin = User.objects.create_user(username='invite_admin', password='pass-invite-123456', is_staff=True, is_superuser=True)
        self.expires = timezone.now() + timezone.timedelta(days=7)

    def test_blank_code_auto_generated_on_create(self):
        from users.models import InviteCode
        self.client.force_login(self.admin)
        # 关键回归点：提交时 code 留空
        resp = self.client.post('/admin/users/invitecode/add/', {
            'code': '',
            'expires_at_0': self.expires.strftime('%Y-%m-%d'),
            'expires_at_1': self.expires.strftime('%H:%M:%S'),
        })
        # 不应报"必填"错误，应重定向到 changelist
        self.assertEqual(resp.status_code, 302, f'留空被表单拦截：{resp.content[:200]}')
        code = InviteCode.objects.first()
        self.assertIsNotNone(code)
        self.assertTrue(code.code)          # 自动生成了随机码
        self.assertEqual(code.created_by, self.admin)
        self.assertGreaterEqual(len(code.code), 6)

    def test_manual_code_respected(self):
        from users.models import InviteCode
        self.client.force_login(self.admin)
        self.client.post('/admin/users/invitecode/add/', {
            'code': 'MANUAL-CODE',
            'expires_at_0': self.expires.strftime('%Y-%m-%d'),
            'expires_at_1': self.expires.strftime('%H:%M:%S'),
        })
        self.assertTrue(InviteCode.objects.filter(code='MANUAL-CODE').exists())


class InviteCodeLogMaskTests(TestCase):
    """邀请码不得明文进操作日志：admin 日志页与 panel dashboard 事件流均展示 object_repr"""

    def setUp(self):
        from django.utils import timezone
        self.admin = User.objects.create_user(username='inv_log_admin', password='pass-12345678', is_staff=True, is_superuser=True)
        self.expires = timezone.now() + timezone.timedelta(days=7)

    def _create_code(self):
        from users.models import InviteCode
        self.client.force_login(self.admin)
        self.client.post('/admin/users/invitecode/add/', {
            'code': '',
            'expires_at_0': self.expires.strftime('%Y-%m-%d'),
            'expires_at_1': self.expires.strftime('%H:%M:%S'),
        })
        return InviteCode.objects.latest('id')

    def test_log_entry_object_repr_is_masked(self):
        from django.contrib.admin.models import LogEntry, ADDITION
        code = self._create_code()
        entry = LogEntry.objects.filter(content_type__model='invitecode', action_flag=ADDITION).latest('action_time')
        self.assertNotIn(code.code, entry.object_repr)
        self.assertIn('****', entry.object_repr)

    def test_observer_dashboard_stream_hides_code(self):
        from django.contrib.auth.models import Permission
        code = self._create_code()
        # 只读观察员：view_logentry + view_ban_ip（cyx 的授权方案）
        observer = User.objects.create_user(username='inv_observer', password='pass-12345678', is_staff=True)
        observer.user_permissions.add(Permission.objects.get(codename='view_logentry'))
        observer.user_permissions.add(Permission.objects.get(codename='view_ban_ip'))
        self.client.force_login(observer)
        resp = self.client.get('/panel/dashboard/')
        self.assertEqual(resp.status_code, 200)
        body = resp.content.decode()
        # 完整邀请码绝不能出现在 dashboard（事件流含 LogEntry 展示）
        self.assertNotIn(code.code, body)
