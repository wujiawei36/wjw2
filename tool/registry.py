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
    {'slug': 'md5', 'title': 'MD5 哈希', 'desc': '文本 MD5（后端计算，需 API Key）', 'kind': 'backend'},
]


def get_tool(slug):
    for tool in TOOLS:
        if tool['slug'] == slug:
            return tool
    return None
