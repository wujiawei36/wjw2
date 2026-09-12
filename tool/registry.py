"""工具站注册表：定义所有工具的元数据。

kind 取值：
- 'frontend'：纯前端 JS 直算（浏览器内完成，零请求、零 Key）
- 'backend'  ：后端 Python 计算（需 API Key，POST /tools/api/<slug>/）
"""
TOOLS = [
    {'slug': 'json', 'title': 'JSON 格式化', 'desc': '格式化 / 校验 JSON', 'kind': 'frontend'},
    {'slug': 'timestamp', 'title': '时间戳转换', 'desc': '时间戳 ↔ 日期时间', 'kind': 'frontend'},
    {'slug': 'base64', 'title': 'Base64 编解码', 'desc': 'Base64 编码 / 解码', 'kind': 'frontend'},
    {'slug': 'uuid', 'title': 'UUID 生成', 'desc': '批量生成 UUID v4', 'kind': 'frontend'},
    {'slug': 'password', 'title': '随机密码', 'desc': '生成随机强密码', 'kind': 'frontend'},
    {'slug': 'wordcount', 'title': '字数统计', 'desc': '字符 / 字节 / 行数统计', 'kind': 'frontend'},
    {'slug': 'sha', 'title': 'SHA 哈希', 'desc': 'SHA-1/256/384/512 哈希', 'kind': 'frontend'},
    {'slug': 'color', 'title': '颜色转换', 'desc': 'HEX ↔ RGB 颜色转换', 'kind': 'frontend'},
    {'slug': 'number', 'title': '进制转换', 'desc': '2/8/10/16 进制互转', 'kind': 'frontend'},
    {'slug': 'regex', 'title': '正则测试', 'desc': '正则匹配测试', 'kind': 'frontend'},
    {'slug': 'text', 'title': '文本去重', 'desc': '按行去重（保留顺序）', 'kind': 'frontend'},
    {'slug': 'md5', 'title': 'MD5 哈希', 'desc': '文本 MD5（后端计算，需 API Key）', 'kind': 'backend',
     'rate_limit': {'window': 60, 'max': 30}},   # 工具默认频率：每 60 秒最多 30 次
    {'slug': 'servertime', 'title': '服务器时间', 'desc': '服务器 UTC/本地时间（后端，需 API Key）', 'kind': 'backend',
     'rate_limit': None},                        # 轻量工具，默认不限频
    {'slug': 'ipinfo', 'title': '我的 IP', 'desc': '查看访客真实 IP（后端，需 API Key）', 'kind': 'backend',
     'rate_limit': None},                        # 轻量工具，默认不限频
]


def get_tool(slug):
    for tool in TOOLS:
        if tool['slug'] == slug:
            return tool
    return None
