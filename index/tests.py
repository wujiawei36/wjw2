from django.test import TestCase


class RobotsTxtTests(TestCase):
    """robots.txt：公开页面放行，后台/私有路径禁止收录"""

    def test_robots_txt_blocks_private_areas(self):
        resp = self.client.get('/robots.txt')
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp['Content-Type'], 'text/plain; charset=utf-8')
        body = resp.content.decode()
        self.assertIn('User-agent: *', body)
        for private in ['/admin/', '/panel/', '/user/', '/captcha/', '/hijack/', '/health/']:
            self.assertIn(f'Disallow: {private}', body)
        self.assertIn('Allow: /', body)


class HealthCheckTests(TestCase):
    """健康检查端点：供脚本/监控探针探测存活，仅返回 200"""

    def test_health_returns_200(self):
        resp = self.client.get('/health/')
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp['Content-Type'], 'text/plain; charset=utf-8')
        self.assertEqual(resp.content.decode(), 'ok')

    def test_health_no_slash_returns_200(self):
        resp = self.client.get('/health')
        self.assertEqual(resp.status_code, 200)
