"""工具站注册表：定义所有工具的元数据。

kind 取值：
- 'frontend'：浏览器 JS 直算（零请求、零 Key）；同时开放 API（脚本带 Key 调用）
- 'backend'  ：后端 Python 计算（浏览器无法直算，如服务器时间/真实 IP）

字段说明：
- intro  ：详细介绍（详情页展示）
- usage  ：操作说明（步骤列表）
- related：相关工具 slug（详情页底部链接）
- rate_limit：API/手动获取的默认频率（window 秒 / max 次），None = 不限
- api_example：详情页 curl 示例的 -d 参数
- allow_anonymous：backend 工具允许浏览器免 Key 手动获取（按 IP 限频）
"""
TOOLS = [
    {'slug': 'json', 'title': 'JSON 格式化', 'desc': '格式化 / 校验 JSON', 'kind': 'frontend',
     'intro': '将压缩成一行的 JSON 展开为易读的缩进格式，并校验语法是否正确。',
     'usage': ['把 JSON 文本粘贴到输入框', '点击「格式化」', '格式化结果会展开显示，语法错误会给出提示'],
     'related': ['regex', 'text'],
     'rate_limit': {'window': 60, 'max': 30},
     'api_example': '{"input":"[1,2,3]"}'},
    {'slug': 'timestamp', 'title': '时间戳转换', 'desc': '时间戳 ↔ 日期时间', 'kind': 'frontend',
     'intro': '在 Unix 时间戳（秒/毫秒）与日期时间之间互转，秒和毫秒自动识别。',
     'usage': ['在「转日期」区输入时间戳', '或在「转时间戳」区输入日期时间', '结果在各自下方显示'],
     'related': ['servertime']},
    {'slug': 'base64', 'title': 'Base64 编解码', 'desc': 'Base64 编码 / 解码', 'kind': 'frontend',
     'intro': 'Base64 编码与解码，完整支持 UTF-8 中文。',
     'usage': ['在「编码」区输入文本得到 Base64', '在「解码」区输入 Base64 还原文本'],
     'related': ['sha', 'md5'],
     'rate_limit': {'window': 60, 'max': 30},
     'api_example': '{"input":"hello","mode":"encode"}'},
    {'slug': 'uuid', 'title': 'UUID 生成', 'desc': '批量生成 UUID v4', 'kind': 'frontend',
     'intro': '批量生成随机 UUID v4（基于 crypto.randomUUID）。',
     'usage': ['输入生成数量（默认 1，最多 1000）', '点击「生成」', '结果每行一个'],
     'related': ['password']},
    {'slug': 'password', 'title': '随机密码', 'desc': '生成随机强密码', 'kind': 'frontend',
     'intro': '生成随机强密码，包含大写、小写、数字和符号，使用密码学安全随机源。',
     'usage': ['输入密码长度（默认 16，4~256）', '点击「生成」'],
     'related': ['uuid']},
    {'slug': 'wordcount', 'title': '字数统计', 'desc': '字符 / 字节 / 行数统计', 'kind': 'frontend',
     'intro': '统计文本的字符数、字节数（UTF-8）、行数、中文字符数等。',
     'usage': ['粘贴或输入文本', '点击「统计」', '各项指标分别显示'],
     'related': ['text', 'json']},
    {'slug': 'sha', 'title': 'SHA 哈希', 'desc': 'SHA-1/256/384/512 哈希', 'kind': 'frontend',
     'intro': '计算文本的 SHA-1 / SHA-256 / SHA-384 / SHA-512 哈希值。',
     'usage': ['输入文本', '点击「计算」', '各算法哈希值分别显示，可直接复制'],
     'related': ['md5', 'base64'],
     'rate_limit': {'window': 60, 'max': 30},
     'api_example': '{"input":"hello"}'},
    {'slug': 'color', 'title': '颜色转换', 'desc': 'HEX ↔ RGB 颜色转换', 'kind': 'frontend',
     'intro': 'HEX 与 RGB 颜色值互转。',
     'usage': ['在「转 RGB」区输入 #RRGGBB', '或在「转 HEX」区输入 rgb(r,g,b)', '结果在各自下方显示'],
     'related': ['number']},
    {'slug': 'number', 'title': '进制转换', 'desc': '2/8/10/16 进制互转', 'kind': 'frontend',
     'intro': '十进制、十六进制、八进制、二进制互转，支持 0x/0b/0o 前缀自动识别。',
     'usage': ['输入任意进制数', '点击「转换」', '四种进制结果分别显示'],
     'related': ['color']},
    {'slug': 'regex', 'title': '正则测试', 'desc': '正则匹配测试', 'kind': 'frontend',
     'intro': '测试正则表达式的匹配结果，正则在浏览器本地执行，不影响服务器。',
     'usage': ['第一行输入正则表达式', '其余行输入待测试文本', '点击「测试」查看匹配结果'],
     'related': ['text', 'json']},
    {'slug': 'text', 'title': '文本去重', 'desc': '按行去重（保留顺序）', 'kind': 'frontend',
     'intro': '按行去除重复文本，保留首次出现的顺序。',
     'usage': ['粘贴多行文本', '点击「去重」', '结果保留原顺序'],
     'related': ['regex', 'wordcount']},
    {'slug': 'md5', 'title': 'MD5 哈希', 'desc': '文本 MD5（浏览器直算）', 'kind': 'frontend',
     'intro': '计算文本的 MD5 哈希。在浏览器本地完成，无需联网、无需 API Key；也支持脚本通过 API 批量调用。',
     'usage': ['输入文本', '点击「计算 MD5」', '哈希值显示在下方，可直接复制'],
     'related': ['sha', 'base64'],
     'rate_limit': {'window': 60, 'max': 30},
     'api_example': '{"input":"hello"}'},
    {'slug': 'servertime', 'title': '服务器时间', 'desc': '服务器 UTC/本地时间', 'kind': 'backend',
     'allow_anonymous': True,                   # 浏览器免 Key 手动获取（按 IP 限频）
     'rate_limit': {'window': 60, 'max': 30},   # 手动获取与 API 统一限频
     'intro': '查看服务器当前的 UTC / 本地时间与 Unix 时间戳。浏览器无法直接读取服务器时间，故手动获取也需请求服务器（免 Key，按 IP 限频）。',
     'usage': ['页面点击「获取」查看服务器时间（免 Key，按 IP 限频）', '或脚本调用：POST /tools/api/servertime/ 携带 X-API-Key（body 可为 {}）'],
     'related': ['timestamp'],
     'api_example': '{}'},
    {'slug': 'ipinfo', 'title': '我的 IP', 'desc': '查看访客真实 IP', 'kind': 'backend',
     'allow_anonymous': True,                   # 浏览器免 Key 手动获取（按 IP 限频）
     'rate_limit': {'window': 60, 'max': 30},   # 手动获取与 API 统一限频
     'intro': '查看访客的真实公网 IP 与 User-Agent（服务器视角）。浏览器无法直接获取公网 IP，故手动获取也需请求服务器（免 Key，按 IP 限频）。',
     'usage': ['页面点击「获取」查看真实 IP（免 Key，按 IP 限频）', '或脚本调用：POST /tools/api/ipinfo/ 携带 X-API-Key（body 可为 {}）'],
     'related': ['servertime'],
     'api_example': '{}'},
]


def get_tool(slug):
    for tool in TOOLS:
        if tool['slug'] == slug:
            return tool
    return None
