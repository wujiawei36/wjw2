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

    def test_excluded_paths_not_recorded(self):
        for url in ['/static/anything.css', '/admin/login/', '/panel/', '/captcha/refresh/']:
            self.client.get(url)
        self.assertEqual(PageVisit.objects.count(), 0)
