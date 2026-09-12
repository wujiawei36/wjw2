from django.test import TestCase

from .models import ApiKey, generate_api_key, hash_api_key


class ApiKeyModelTests(TestCase):
    """API Key 生成、哈希存储与校验逻辑"""

    def test_generate_and_hash(self):
        full_key, key_hash = generate_api_key()
        self.assertTrue(full_key.startswith('wjw2_live_'))
        self.assertEqual(hash_api_key(full_key), key_hash)

    def test_validate_active(self):
        key = ApiKey.objects.create(name='test', key_hash='x' * 64)
        ok, err = key.validate('md5')
        self.assertTrue(ok)
        self.assertIsNone(err)

    def test_validate_disabled(self):
        key = ApiKey.objects.create(name='test', key_hash='x' * 64, is_active=False)
        ok, err = key.validate('md5')
        self.assertFalse(ok)
        self.assertEqual(err, 'KEY_DISABLED')

    def test_validate_quota_exceeded(self):
        key = ApiKey.objects.create(name='test', key_hash='x' * 64, quota=1, used=1)
        ok, err = key.validate('md5')
        self.assertEqual(err, 'QUOTA_EXCEEDED')

    def test_validate_slug_not_allowed(self):
        key = ApiKey.objects.create(name='test', key_hash='x' * 64, allowed_slugs='md5')
        ok, err = key.validate('other')
        self.assertEqual(err, 'SLUG_NOT_ALLOWED')


class ToolPagesTests(TestCase):
    """工具列表页与详情页渲染"""

    def test_index_lists_tools(self):
        resp = self.client.get('/tools/')
        self.assertEqual(resp.status_code, 200)
        body = resp.content.decode()
        self.assertIn('JSON 格式化', body)
        self.assertIn('MD5 哈希', body)

    def test_frontend_tool_detail_loads_js(self):
        resp = self.client.get('/tools/json/')
        self.assertEqual(resp.status_code, 200)
        body = resp.content.decode()
        self.assertIn('tool/js/json.js', body)

    def test_backend_tool_detail_has_api_key_field(self):
        resp = self.client.get('/tools/md5/')
        self.assertEqual(resp.status_code, 200)
        body = resp.content.decode()
        self.assertIn('api-key', body)

    def test_unknown_tool_404(self):
        resp = self.client.get('/tools/nonexistent/')
        self.assertEqual(resp.status_code, 404)

    def test_index_lists_second_batch_tools(self):
        resp = self.client.get('/tools/')
        body = resp.content.decode()
        for name in ['SHA 哈希', '颜色转换', '进制转换', '正则测试',
                     '文本去重', '服务器时间', '我的 IP']:
            self.assertIn(name, body)

    def test_frontend_tools_detail_load_js(self):
        for slug in ['sha', 'color', 'number', 'regex', 'text']:
            resp = self.client.get(f'/tools/{slug}/')
            self.assertEqual(resp.status_code, 200)
            self.assertIn(f'tool/js/{slug}.js', resp.content.decode())

    def test_backend_tools_detail_have_api_key_field(self):
        for slug in ['servertime', 'ipinfo']:
            resp = self.client.get(f'/tools/{slug}/')
            self.assertEqual(resp.status_code, 200)
            self.assertIn('api-key', resp.content.decode())


class ToolApiTests(TestCase):
    """后端工具 API：API Key 鉴权 + MD5 计算"""

    def setUp(self):
        self.full_key, self.key_hash = generate_api_key()
        ApiKey.objects.create(name='test', key_hash=self.key_hash)

    def _post(self, payload='{}', key=None):
        headers = {'HTTP_X_API_KEY': key} if key else {}
        return self.client.post('/tools/api/md5/', data=payload,
                                content_type='application/json', **headers)

    def test_md5_with_valid_key(self):
        resp = self._post('{"input":"hello"}', self.full_key)
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertTrue(data['ok'])
        self.assertEqual(data['data']['md5'], '5d41402abc4b2a76b9719d911017c592')

    def test_md5_without_key(self):
        resp = self._post()
        self.assertEqual(resp.status_code, 401)
        self.assertFalse(resp.json()['ok'])

    def test_md5_with_invalid_key(self):
        resp = self._post('{}', 'wjw2_live_wrong_key')
        self.assertEqual(resp.status_code, 401)
        self.assertEqual(resp.json()['error'], 'INVALID_KEY')

    def test_used_increment(self):
        self._post('{"input":"x"}', self.full_key)
        key = ApiKey.objects.get(key_hash=self.key_hash)
        self.assertEqual(key.used, 1)
        self.assertIsNotNone(key.last_used_at)

    def test_servertime_with_valid_key(self):
        resp = self.client.post('/tools/api/servertime/', data='{}',
                                content_type='application/json',
                                HTTP_X_API_KEY=self.full_key)
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertTrue(data['ok'])
        self.assertIn('UTC:', data['data']['text'])

    def test_ipinfo_with_valid_key(self):
        resp = self.client.post('/tools/api/ipinfo/', data='{}',
                                content_type='application/json',
                                HTTP_X_API_KEY=self.full_key)
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertTrue(data['ok'])
        self.assertIn('IP:', data['data']['text'])

    def test_servertime_without_key(self):
        resp = self.client.post('/tools/api/servertime/', data='{}',
                                content_type='application/json')
        self.assertEqual(resp.status_code, 401)

    def test_frontend_tool_not_api(self):
        # 纯前端工具没有 API 端点，调其 API 应返回 NOT_API_TOOL
        resp = self.client.post('/tools/api/json/', data='{}',
                                content_type='application/json',
                                HTTP_X_API_KEY=self.full_key)
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(resp.json()['error'], 'NOT_API_TOOL')


class ApiKeyAdminTests(TestCase):
    """后台新建 API Key：留空 key_hash 自动生成，默认激活"""

    def test_admin_create_generates_key(self):
        from django.contrib.auth import get_user_model
        User = get_user_model()
        admin_user = User.objects.create_user(
            username='t_admin', password='p-12345678', is_staff=True, is_superuser=True)
        self.client.force_login(admin_user)
        resp = self.client.post('/admin/tool/apikey/add/', {'name': 'my-key'})
        self.assertEqual(resp.status_code, 302, f'创建失败：{resp.content[:200]}')
        key = ApiKey.objects.get(name='my-key')
        self.assertTrue(key.key_hash)      # 自动生成了 key_hash
        self.assertTrue(key.is_active)     # 默认激活


class MiddlewareApiExemptionTests(TestCase):
    """API 路径应跳过爬虫检测（缺头/UA 黑名单），但普通路径仍拦截"""

    def _make_request(self, path, ua):
        from django.test import RequestFactory
        rf = RequestFactory()
        req = rf.post(path, data='{}', content_type='application/json',
                      REMOTE_ADDR='8.8.8.8')
        req.META['HTTP_USER_AGENT'] = ua
        return req

    def test_api_path_exempt_from_crawler_detection(self):
        from users.middleware import RequestBlockingMiddleware
        req = self._make_request('/tools/api/md5/', 'curl/8.0')
        mw = RequestBlockingMiddleware(lambda r: None)
        self.assertIsNone(mw.process_request(req))

    def test_normal_path_still_blocked(self):
        from users.middleware import RequestBlockingMiddleware
        req = self._make_request('/', 'curl/8.0')
        mw = RequestBlockingMiddleware(lambda r: None)
        resp = mw.process_request(req)
        self.assertIsNotNone(resp)
        self.assertEqual(resp.status_code, 403)
