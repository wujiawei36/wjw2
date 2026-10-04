"""密码强度评估：基于「熵估算（entropy）」的科学模型，与前端 password-strength.js 严格一致。

核心思路（区别于旧的「加分制」）：
- 估算密码的「猜测熵」，单位 bits（= log2(攻击者需要的猜测次数)），
  而不是简单地按「长度 + 字符种类」加分。
- 通过「模式匹配」识别已知的低熵模式，并按真实猜测空间计熵：
  * 常见弱密码黑名单（含 l33t 变体）→ 极低熵
  * 重复字符（aaaa、********…）→ 按「1 个字符 + 重复次数」计熵
  * 连续序列（abc、123、987…）与键盘序列（qwerty、asdf…）→ 高度可预测，低熵
  * 词典词（英文常见词 / 中文常见词 / 项目相关词：域名、错误码、命令）→ 按词计熵
  * l33t 替换（n0t、p@ss、0→o、3→e…）→ 还原后再匹配，替换不增加熵
  * 明确分隔符（空格 / 斜杠 / 下划线 / 点等）→ 低熵
- 最后把 bits 映射回 0~100 分与 5 档（沿用 zxcvbn 的熵阈值）。

说明：本模块仅用于「展示型强度提示」（工具站 API / 前端强度条），
不替代 django.contrib.auth.password_validation.validate_password（真正安全边界）。
"""

import math

# ---- 常见弱密码黑名单（命中即极低熵） ----
COMMON_PASSWORDS = frozenset({
    '123456', 'password', '12345678', 'qwerty', 'abc123', '123456789',
    '111111', '1234567', 'password1', '1234567890', '123123', '000000',
    'iloveyou', '1234', '1q2w3e4r', 'qwertyuiop', '12345678900', '666666',
    '888888', 'abc123456', 'letmein', 'welcome', 'monkey', 'dragon',
    'master', 'login', 'admin', 'passw0rd', 'aa123456', '123456789a',
    '654321', '123321', '11111111', '112233', 'qwerty123', '1qaz2wsx',
    'sunshine', 'princess', 'football', 'baseball', 'superman',
})

# ---- 词典（小写）：识别「语义词」，按词计熵而非按字符 ----
# 英文常见词（>=3 字母）、中文常见词（>=2 字）、项目相关词（域名/错误码/命令）。
DICTIONARY = frozenset({
    # 英文常见词
    'password', 'welcome', 'admin', 'administrator', 'login', 'letmein',
    'monkey', 'dragon', 'master', 'sunshine', 'princess', 'football',
    'baseball', 'superman', 'iloveyou', 'hello', 'google', 'facebook',
    'twitter', 'instagram', 'computer', 'internet', 'secret', 'this',
    'not', 'safe', 'that', 'what', 'world', 'test', 'demo', 'user',
    'guest', 'root', 'system', 'pass', 'pwd',
    # 中文常见词
    '密码', '管理员', '测试', '验证', '安全', '我爱你', '你好', '用户名',
    '登录', '注册', '修改', '长度', '字符', '数字', '符号', '连续',
    '重复', '序列', '弱密码', '黑名单', '相似度', '评级', '提示',
    '校验', '策略', '评估', '强度', '错误',
    # 项目相关（域名 / 协议 / 命令 / 错误码）
    'wujiawei', 'pythonanywhere', 'python', 'django', 'curl', 'https',
    'http', 'www', 'com', 'missing_key', 'invalid_key', 'key_disabled',
    'key_expired', 'quota_exceeded', 'slug_not_allowed', 'rate_limited',
    'bad_param', 'unsupported_slug', 'apikey', 'token', 'jwt',
})

# ---- l33t 替换映射：还原成普通小写字母 ----
_LEET_MAP = str.maketrans({
    '0': 'o', '1': 'l', '3': 'e', '4': 'a', '5': 's', '7': 't',
    '8': 'b', '@': 'a', '$': 's', '!': 'i', '+': 't',
})

# ---- 键盘行（用于键盘序列检测，含逆序）----
_KEYBOARD_ROWS = (
    'qwertyuiop', 'asdfghjkl', 'zxcvbnm',
    'qwertyuiop'[::-1], 'asdfghjkl'[::-1], 'zxcvbnm'[::-1],
)

# ---- 明确分隔符（低熵：空格 / 斜杠 / 下划线 / 点 / 连字符 / 冒号等）----
_SEPARATORS = frozenset(' /_.-:;,\\|')


# ---- 每档评级 ----
LEVELS = [
    {'label': '很弱', 'color': '#e74c3c'},
    {'label': '弱', 'color': '#e67e22'},
    {'label': '中', 'color': '#f1c40f'},
    {'label': '强', 'color': '#2ecc71'},
    {'label': '很强', 'color': '#27ae60'},
]

# 词典按长度降序排列（前缀最长匹配用）
_SORTED_WORDS = sorted(DICTIONARY, key=len, reverse=True)
_WORD_BITS = math.log2(len(DICTIONARY)) if DICTIONARY else 8.0


def _unleet(s: str) -> str:
    """把 l33t 替换还原成普通小写字母。"""
    return s.translate(_LEET_MAP)


def _sequence_len(s: str, i: int) -> int:
    """从 i 开始，连续递增/递减的 ASCII 字符序列长度（如 abc、cba、123、987）。"""
    n = len(s)
    if i + 1 >= n:
        return 1
    inc = dec = 1
    j = i + 1
    while j < n:
        d = ord(s[j]) - ord(s[j - 1])
        if d == 1 and dec == 1:
            inc += 1
        elif d == -1 and inc == 1:
            dec += 1
        else:
            break
        j += 1
    return max(inc, dec)


def _keyboard_len(s: str, i: int) -> int:
    """从 i 开始，在键盘行上的连续匹配长度（如 qwerty、asdf、zxcv 及逆序）。"""
    best = 0
    for row in _KEYBOARD_ROWS:
        pos = row.find(s[i])
        if pos == -1:
            continue
        j, k = i, pos
        while j < len(s) and k < len(row) and s[j] == row[k]:
            j += 1
            k += 1
        if j - i > best:
            best = j - i
    return best


def _match_word_len(lower: str, unleet: str, i: int) -> int:
    """从 i 开始，在 lower 与 unleet 中做前缀最长词典匹配，返回词长（无匹配返回 0）。"""
    best = 0
    for text in (lower, unleet):
        for w in _SORTED_WORDS:
            if len(w) <= best:
                break
            if text.startswith(w, i):
                best = len(w)
                break
    return best


def _estimate_bits(pw: str) -> float:
    """估算密码的猜测熵（bits）。"""
    n = len(pw)
    if n == 0:
        return 0.0

    lower = pw.lower()
    unleet = _unleet(lower)

    # 黑名单（含 l33t 变体）→ 攻击者第一个就试，熵趋近 0
    if lower in COMMON_PASSWORDS or unleet in COMMON_PASSWORDS:
        return 0.0

    # 字符集统计
    has_lower = any('a' <= c <= 'z' for c in pw)
    has_upper = any('A' <= c <= 'Z' for c in pw)
    has_digit = any('0' <= c <= '9' for c in pw)
    has_symbol = any(
        not ('a' <= c <= 'z' or 'A' <= c <= 'Z' or '0' <= c <= '9') for c in pw)

    pool = 0
    if has_lower:
        pool += 26
    if has_upper:
        pool += 26
    if has_digit:
        pool += 10
    if has_symbol:
        pool += 33
    per_char = math.log2(pool) if pool > 0 else 0.0

    bits = 0.0
    i = 0
    while i < n:
        # 1) 重复字符（>=3 个连续相同）：熵 = 字符集 + 重复次数
        run = 1
        while i + run < n and pw[i + run] == pw[i]:
            run += 1
        if run >= 3:
            bits += (math.log2(pool) + math.log2(run)) if pool > 0 else math.log2(run)
            i += run
            continue

        # 2) 键盘序列（>=4）
        kb = _keyboard_len(lower, i)
        if kb >= 4:
            bits += kb * 1.0
            i += kb
            continue

        # 3) 连续序列（abc / 123，>=3）
        seq = _sequence_len(pw, i)
        if seq >= 3:
            bits += seq * 1.0
            i += seq
            continue

        # 4) 词典词（>=2 字）
        wl = _match_word_len(lower, unleet, i)
        if wl >= 2:
            bits += _WORD_BITS
            i += wl
            continue

        # 5) 单字符
        c = pw[i]
        if '\u4e00' <= c <= '\u9fff':
            bits += 3.5          # 自然语言汉字：低熵
        elif c in _SEPARATORS:
            bits += 1.5          # 分隔符/标点：低熵
        else:
            bits += per_char
        i += 1

    return bits


def _interp(x, lo_b, hi_b, lo_s, hi_s) -> int:
    """把 bits 在 [lo_b, hi_b] 线性映射到 [lo_s, hi_s]，四舍五入并夹紧。"""
    if hi_b <= lo_b:
        return lo_s
    t = (x - lo_b) / (hi_b - lo_b)
    v = round(lo_s + t * (hi_s - lo_s))
    return max(lo_s, min(hi_s, v))


def _bits_to_score_level(bits: float):
    """把熵(bits)映射为 (score 0~99, level 0~4)。沿用 zxcvbn 的熵阈值。

    分数上限封顶 99（而非 100）：刻意保留缺口，暗示「没有绝对安全的密码」。
    """
    if bits < 28:
        return _interp(bits, 0, 28, 0, 19), 0
    if bits < 36:
        return _interp(bits, 28, 36, 20, 39), 1
    if bits < 60:
        return _interp(bits, 36, 60, 40, 59), 2
    if bits < 128:
        return _interp(bits, 60, 128, 60, 79), 3
    return _interp(bits, 128, 256, 80, 99), 4


def password_strength(password: str, username: str | None = None) -> dict:
    """评估密码强度，返回结构化结果。

    返回字段：score(0~100)、level(0~4)、label、color、length、
    has_lower/has_upper/has_digit/has_symbol、is_common。
    """
    pw = password or ''
    lower = pw.lower()
    unleet = _unleet(lower)
    is_common = lower in COMMON_PASSWORDS or unleet in COMMON_PASSWORDS

    has_lower = any('a' <= c <= 'z' for c in pw)
    has_upper = any('A' <= c <= 'Z' for c in pw)
    has_digit = any('0' <= c <= '9' for c in pw)
    has_symbol = any(
        not ('a' <= c <= 'z' or 'A' <= c <= 'Z' or '0' <= c <= '9') for c in pw)

    bits = _estimate_bits(pw)

    # 用户名相似度：密码等于/包含用户名时，熵按「被定向猜测」大幅下调
    if username and len(username) >= 3:
        u = username.lower()
        if lower == u or unleet == u:
            bits = min(bits, 0.0)
        elif u in lower or u in unleet:
            bits = min(bits, bits * 0.5)

    score, level = _bits_to_score_level(bits)
    return {
        'score': score,
        'level': level,
        'label': LEVELS[level]['label'],
        'color': LEVELS[level]['color'],
        'length': len(pw),
        'has_lower': has_lower,
        'has_upper': has_upper,
        'has_digit': has_digit,
        'has_symbol': has_symbol,
        'is_common': is_common,
    }
