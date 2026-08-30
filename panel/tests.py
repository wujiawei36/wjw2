from django.test import TestCase
from django.contrib.auth import get_user_model

User = get_user_model()


class DashboardTests(TestCase):
    """仪表盘：今日访问统计与权限控制"""

    def setUp(self):
        self.staff = User.objects.create_user(
            username='dash_staff', password='pass-123456', is_staff=True)

    def test_dashboard_shows_today_visits(self):
        # force_login 直接注入 session，绕开 axes 对 authenticate 必须带 request 的限制
        self.client.force_login(self.staff, backend='django.contrib.auth.backends.ModelBackend')
        # 先访问一个普通页面产生一条埋点记录
        self.client.get('/')
        resp = self.client.get('/panel/dashboard/')
        self.assertEqual(resp.status_code, 200)
        # /panel/dashboard/ 自身路径被排除，因此今日访问应为 1
        self.assertEqual(resp.context['stats']['today_visits'], 1)

    def test_dashboard_requires_staff(self):
        resp = self.client.get('/panel/dashboard/')
        self.assertNotEqual(resp.status_code, 200)  # 未登录应被重定向
