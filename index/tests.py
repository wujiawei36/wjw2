from django.test import TestCase


class RobotsTxtTests(TestCase):
    """robots.txt：公开页面放行，后台/私有路径禁止收录"""

    def test_robots_txt_blocks_private_areas(self):
        resp = self.client.get('/robots.txt')
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp['Content-Type'], 'text/plain; charset=utf-8')
        body = resp.content.decode()
        self.assertIn('User-agent: *', body)
        for private in ['/admin/', '/panel/', '/user/', '/captcha/', '/hijack/']:
            self.assertIn(f'Disallow: {private}', body)
        self.assertIn('Allow: /', body)
