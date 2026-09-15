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
- api_response：详情页展示的 API 成功响应结构（data 字段示例）
- allow_anonymous：backend 工具允许浏览器免 Key 手动获取（按 IP 限频）
- immersive：展示型工具（如大屏时钟），详情页只渲染工具本体，
  不渲染标题/介绍/操作说明/相关工具等装饰区块
"""
TOOLS = [
    {'slug': 'json', 'title': 'JSON 格式化', 'desc': '格式化 / 校验 JSON', 'kind': 'frontend',
     'intro': '将压缩成一行的 JSON 展开为易读的缩进格式，并校验语法是否正确。',
     'usage': ['把 JSON 文本粘贴到输入框', '点击「格式化」', '格式化结果会展开显示，语法错误会给出提示'],
     'related': ['regex', 'text'],
     'rate_limit': {'window': 60, 'max': 30},
     'api_example': '{"input":"[1,2,3]"}',
     'api_response': '''{
  "ok": true,
  "data": {
    "text": "格式化的 JSON"
  }
}'''},
    {'slug': 'timestamp', 'title': '时间戳转换', 'desc': '时间戳 ↔ 日期时间', 'kind': 'frontend',
     'intro': '在 Unix 时间戳（秒/毫秒）与日期时间之间互转，秒和毫秒自动识别。',
     'usage': ['在「转日期」区输入时间戳', '或在「转时间戳」区输入日期时间', '结果在各自下方显示'],
     'related': ['servertime'],
     'rate_limit': {'window': 60, 'max': 30},
     'api_example': '{"input":"1755564444"}',
     'api_response': '''{
  "ok": true,
  "data": {
    "local": "2026-09-12 18:00:00",
    "utc": "2026-09-12 10:00:00",
    "unix_seconds": 1755564444,
    "unix_ms": 1755564444000
  }
}'''},
    {'slug': 'base64', 'title': 'Base64 编解码', 'desc': 'Base64 编码 / 解码', 'kind': 'frontend',
     'intro': 'Base64 编码与解码，完整支持 UTF-8 中文。',
     'usage': ['在「编码」区输入文本得到 Base64', '在「解码」区输入 Base64 还原文本'],
     'related': ['sha', 'md5'],
     'rate_limit': {'window': 60, 'max': 30},
     'api_example': '{"input":"hello","mode":"encode"}',
     'api_response': '''{
  "ok": true,
  "data": {
    "text": "aGVsbG8="
  }
}'''},
    {'slug': 'uuid', 'title': 'UUID 生成', 'desc': '批量生成 UUID v4', 'kind': 'frontend',
     'intro': '批量生成随机 UUID v4（基于 crypto.randomUUID）。',
     'usage': ['输入生成数量（默认 1，最多 1000）', '点击「生成」', '结果每行一个'],
     'related': ['password'],
     'rate_limit': {'window': 60, 'max': 30},
     'api_example': '{"input":"5"}',
     'api_response': '''{
  "ok": true,
  "data": {
    "count": 5,
    "uuids": ["...", "..."]
  }
}'''},
    {'slug': 'password', 'title': '随机密码', 'desc': '批量生成随机密码（数量/长度/字符集）', 'kind': 'frontend',
     'intro': '批量生成随机强密码，可设置长度、数量与字符集（含/不含符号、纯数字等），使用密码学安全随机源，并保证每个字符组至少出现一次。',
     'usage': ['设置长度（默认 16，4~256）', '设置生成数量（默认 1，1~100）', '选择字符集（字母+数字+符号 / 字母+数字 / 小写+数字 / 纯数字）', '点击「生成」，每个密码一行'],
     'related': ['uuid'],
     'rate_limit': {'window': 60, 'max': 30},
     'api_example': '{"input":"16","count":5,"charset":"alnum"}',
     'api_response': '''{
  "ok": true,
  "data": {
    "passwords": ["xK9mP2dF8q...", "..."],
    "count": 5,
    "length": 16,
    "charset": "alnum"
  }
}'''},
    {'slug': 'wordcount', 'title': '字数统计', 'desc': '字符 / 字节 / 行数统计', 'kind': 'frontend',
     'intro': '统计文本的字符数、字节数（UTF-8）、行数、中文字符数等。',
     'usage': ['粘贴或输入文本', '点击「统计」', '各项指标分别显示'],
     'related': ['text', 'json'],
     'rate_limit': {'window': 60, 'max': 30},
     'api_example': '{"input":"hello 你好"}',
     'api_response': '''{
  "ok": true,
  "data": {
    "chars": 6,
    "bytes": 8,
    "lines": 1,
    "no_space": 6,
    "chinese": 2
  }
}'''},
    {'slug': 'sha', 'title': 'SHA 哈希', 'desc': 'SHA-1/256/384/512 哈希', 'kind': 'frontend',
     'intro': '计算文本的 SHA-1 / SHA-256 / SHA-384 / SHA-512 哈希值。',
     'usage': ['输入文本', '点击「计算」', '各算法哈希值分别显示，可直接复制'],
     'related': ['md5', 'base64'],
     'rate_limit': {'window': 60, 'max': 30},
     'api_example': '{"input":"hello"}',
     'api_response': '''{
  "ok": true,
  "data": {
    "sha1": "...",
    "sha256": "...",
    "sha384": "...",
    "sha512": "..."
  }
}'''},
    {'slug': 'color', 'title': '颜色转换', 'desc': 'HEX ↔ RGB 颜色转换', 'kind': 'frontend',
     'intro': 'HEX 与 RGB 颜色值互转。',
     'usage': ['在「转 RGB」区输入 #RRGGBB', '或在「转 HEX」区输入 rgb(r,g,b)', '结果在各自下方显示'],
     'related': ['number'],
     'rate_limit': {'window': 60, 'max': 30},
     'api_example': '{"input":"#ff0000"}',
     'api_response': '''{
  "ok": true,
  "data": {
    "r": 255,
    "g": 0,
    "b": 0,
    "rgb": "rgb(255, 0, 0)"
  }
}'''},
    {'slug': 'number', 'title': '进制转换', 'desc': '2/8/10/16 进制互转', 'kind': 'frontend',
     'intro': '十进制、十六进制、八进制、二进制互转，支持 0x/0b/0o 前缀自动识别。',
     'usage': ['输入任意进制数', '点击「转换」', '四种进制结果分别显示'],
     'related': ['color'],
     'rate_limit': {'window': 60, 'max': 30},
     'api_example': '{"input":"255"}',
     'api_response': '''{
  "ok": true,
  "data": {
    "dec": "255",
    "hex": "0xFF",
    "oct": "0o377",
    "bin": "0b11111111"
  }
}'''},
    {'slug': 'regex', 'title': '正则测试', 'desc': '正则匹配测试', 'kind': 'frontend',
     'intro': '测试正则表达式的匹配结果，正则在浏览器本地执行，不影响服务器。',
     'usage': ['第一行输入正则表达式', '其余行输入待测试文本', '点击「测试」查看匹配结果'],
     'related': ['text', 'json'],
     'rate_limit': {'window': 60, 'max': 30},
     'api_example': '{"input":"abc\\nabc123abc456"}',
     'api_response': '''{
  "ok": true,
  "data": {
    "count": 2,
    "matches": ["abc", "abc"]
  }
}'''},
    {'slug': 'text', 'title': '文本去重', 'desc': '按行去重（保留顺序）', 'kind': 'frontend',
     'intro': '按行去除重复文本，保留首次出现的顺序。',
     'usage': ['粘贴多行文本', '点击「去重」', '结果保留原顺序'],
     'related': ['regex', 'wordcount'],
     'rate_limit': {'window': 60, 'max': 30},
     'api_example': '{"input":"a\\nb\\na\\nc"}',
     'api_response': '''{
  "ok": true,
  "data": {
    "text": "a\\nb\\nc",
    "lines": 4,
    "unique": 3
  }
}'''},
    {'slug': 'md5', 'title': 'MD5 哈希', 'desc': '文本 MD5（浏览器直算）', 'kind': 'frontend',
     'intro': '计算文本的 MD5 哈希。在浏览器本地完成，无需联网、无需 API Key；也支持脚本通过 API 批量调用。',
     'usage': ['输入文本', '点击「计算 MD5」', '哈希值显示在下方，可直接复制'],
     'related': ['sha', 'base64'],
     'rate_limit': {'window': 60, 'max': 30},
     'api_example': '{"input":"hello"}',
     'api_response': '''{
  "ok": true,
  "data": {
    "md5": "5d41402abc4b2a76b9719d911017c592"
  }
}'''},
    {'slug': 'servertime', 'title': '服务器时间', 'desc': '服务器 UTC/本地时间', 'kind': 'backend',
     'allow_anonymous': True,                   # 浏览器免 Key 手动获取（按 IP 限频）
     'rate_limit': {'window': 60, 'max': 5},    # 手动获取与 API 统一限频（降频防刷）
     'intro': '查看服务器当前的 UTC / 本地时间与 Unix 时间戳。浏览器无法直接读取服务器时间，故手动获取也需请求服务器（免 Key，按 IP 限频）。',
     'usage': ['页面点击「获取」查看服务器时间（免 Key，按 IP 限频）', '或脚本调用：POST /tools/api/servertime/ 携带 X-API-Key（body 可为 {}）'],
     'related': ['timestamp'],
     'api_example': '{}',
     'api_response': '''{
  "ok": true,
  "data": {
    "utc": "2026-09-12 10:00:00",
    "local": "2026-09-12 18:00:00",
    "timezone": "Asia/Shanghai",
    "unix": 1755564444
  }
}'''},
    {'slug': 'ipinfo', 'title': '我的 IP', 'desc': '查看访客真实 IP', 'kind': 'backend',
     'allow_anonymous': True,                   # 浏览器免 Key 手动获取（按 IP 限频）
     'rate_limit': {'window': 60, 'max': 5},    # 手动获取与 API 统一限频（降频防刷）
     'intro': '查看访客的真实公网 IP 与 User-Agent（服务器视角）。浏览器无法直接获取公网 IP，故手动获取也需请求服务器（免 Key，按 IP 限频）。',
     'usage': ['页面点击「获取」查看真实 IP（免 Key，按 IP 限频）', '或脚本调用：POST /tools/api/ipinfo/ 携带 X-API-Key（body 可为 {}）'],
     'related': ['servertime'],
     'api_example': '{}',
     'api_response': '''{
  "ok": true,
  "data": {
    "ip": "1.2.3.4",
    "user_agent": "curl/8.0"
  }
}'''},
    {'slug': 'clock', 'title': '大屏时钟', 'desc': '大屏显示当前时间', 'kind': 'frontend',
     'immersive': True,
     'intro': '大屏显示当前时间（时:分:秒）与日期、星期，每秒自动刷新。纯浏览器本地运行，不发请求、无需 API Key，适合投屏或全屏展示（按 F11 全屏）。',
     'usage': ['打开页面即自动显示当前时间，无需操作', '适合投屏 / 全屏展示（F11）', '字号随窗口大小自适应缩放'],
     'related': ['servertime', 'timestamp']},
]


def get_tool(slug):
    for tool in TOOLS:
        if tool['slug'] == slug:
            return tool
    return None


def format_rate_limit(tool):
    """把 rate_limit 格式化为人类可读文本，如 '30 次/分钟'、'30 次/30秒'。无 rate_limit 返回 None。"""
    rl = tool.get('rate_limit')
    if not rl:
        return None
    window, max_c = rl['window'], rl['max']
    if window >= 60 and window % 60 == 0:
        m = window // 60
        win = '分钟' if m == 1 else f'{m} 分钟'
    else:
        win = f'{window} 秒'
    return f'{max_c} 次/{win}'
