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


class ApiKeysTests(TestCase):
    """生成 API Key 快捷页：明文仅显示一次，库中只存加盐哈希"""

    def setUp(self):
        from tool.models import hash_api_key
        self.hash_api_key = hash_api_key
        self.developer = User.objects.create_user(
            username='api_dev', password='pass-123456', is_staff=True, can_develop=True)
        self.plain_staff = User.objects.create_user(
            username='api_plain', password='pass-123456', is_staff=True)

    def test_api_keys_requires_can_develop(self):
        self.client.force_login(self.plain_staff, backend='django.contrib.auth.backends.ModelBackend')
        resp = self.client.get('/panel/api_keys/')
        self.assertEqual(resp.status_code, 302)
        self.assertTrue(resp.url.startswith('/panel'))

    def test_generate_shows_full_key_once_and_stores_hash(self):
        from tool.models import ApiKey
        self.client.force_login(self.developer, backend='django.contrib.auth.backends.ModelBackend')
        resp = self.client.post('/panel/api_keys/', {
            'name': '自己的脚本', 'unlimited': 'on', 'confirm': 'on',
        })
        self.assertEqual(resp.status_code, 200)
        full_key = resp.context['full_key']
        self.assertTrue(full_key.startswith('wjw2_live_'))
        key = ApiKey.objects.get(key_hash=self.hash_api_key(full_key))
        self.assertEqual(key.owner, self.developer)
        self.assertEqual(key.name, '自己的脚本')
        self.assertTrue(key.unlimited)
        # 明文不落库：库里只存加盐哈希，不等于明文
        self.assertNotEqual(key.key_hash, full_key)
        # 响应中明文完整出现一次
        self.assertIn(full_key, resp.content.decode())

    def test_get_does_not_expose_plaintext(self):
        self.client.force_login(self.developer, backend='django.contrib.auth.backends.ModelBackend')
        resp = self.client.get('/panel/api_keys/')
        self.assertEqual(resp.status_code, 200)
        self.assertNotIn('full_key', resp.context)
        self.assertNotIn('wjw2_live_', resp.content.decode())
