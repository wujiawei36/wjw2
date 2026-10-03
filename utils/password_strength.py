"""密码强度评估：与前端 tool/static/tool/js/password-strength.js 严格一致。

打分规则（0~100 分，映射 5 档）：
- 长度：每字符 3 分，封顶 60（20 字符）
- 字符集多样性：小写 +8 / 大写 +8 / 数字 +8 / 符号 +12；仅 1 类字符集额外 -10
- 连续序列（abc/123 等，3 个及以上递增或递减）：-10（至多一次）
- 重复字符（aaa/111 等，3 个及以上）：-8（至多一次）
- 常见弱密码黑名单：命中直接 0 分
- 用户名相似度（简化版，后端 validate_password 做精确校验）：
    密码 == 用户名 -20；密码包含用户名 -15

说明：本模块仅用于「展示型强度提示」（工具站 API / 前端强度条），
不替代 django.contrib.auth.password_validation.validate_password（真正安全边界）。
"""

COMMON_PASSWORDS = frozenset({
    '123456', 'password', '12345678', 'qwerty', 'abc123', '123456789',
    '111111', '1234567', 'password1', '1234567890', '123123', '000000',
    'iloveyou', '1234', '1q2w3e4r', 'qwertyuiop', '12345678900', '666666',
    '888888', 'abc123456', 'letmein', 'welcome', 'monkey', 'dragon',
    'master', 'login', 'admin', 'passw0rd', 'aa123456', '123456789a',
    '654321', '123321', '11111111', '112233', 'qwerty123', '1qaz2wsx',
    'sunshine', 'princess', 'football', 'baseball', 'superman',
})

LEVELS = [
    {'label': '很弱', 'color': '#e74c3c'},
    {'label': '弱', 'color': '#e67e22'},
    {'label': '中', 'color': '#f1c40f'},
    {'label': '强', 'color': '#2ecc71'},
    {'label': '很强', 'color': '#27ae60'},
]


def _level(score: int) -> int:
    if score < 20:
        return 0
    if score < 40:
        return 1
    if score < 60:
        return 2
    if score < 80:
        return 3
    return 4


def _has_sequence(s: str) -> bool:
    """是否存在 3 个及以上连续递增或递减的 ASCII 字符（如 abc、cba、123、987）。"""
    inc = dec = 1
    for i in range(1, len(s)):
        d = ord(s[i]) - ord(s[i - 1])
        if d == 1:
            inc += 1
            dec = 1
        elif d == -1:
            dec += 1
            inc = 1
        else:
            inc = dec = 1
        if inc >= 3 or dec >= 3:
            return True
    return False


def _has_repeat(s: str) -> bool:
    """是否存在 3 个及以上连续相同字符（如 aaa、111）。"""
    run = 1
    for i in range(1, len(s)):
        if s[i] == s[i - 1]:
            run += 1
        else:
            run = 1
        if run >= 3:
            return True
    return False


def password_strength(password: str, username: str | None = None) -> dict:
    """评估密码强度，返回结构化结果。

    返回字段：score(0~100)、level(0~4)、label、color、length、
    has_lower/has_upper/has_digit/has_symbol、is_common。
    """
    pw = password or ''
    is_common = pw.lower() in COMMON_PASSWORDS

    has_lower = any('a' <= c <= 'z' for c in pw)
    has_upper = any('A' <= c <= 'Z' for c in pw)
    has_digit = any('0' <= c <= '9' for c in pw)
    has_symbol = any(
        not ('a' <= c <= 'z' or 'A' <= c <= 'Z' or '0' <= c <= '9') for c in pw)

    score = 0
    if not is_common:
        score += min(len(pw), 20) * 3
        if has_lower:
            score += 8
        if has_upper:
            score += 8
        if has_digit:
            score += 8
        if has_symbol:
            score += 12
        classes = sum([has_lower, has_upper, has_digit, has_symbol])
        if classes <= 1:
            score -= 10
        if _has_sequence(pw):
            score -= 10
        if _has_repeat(pw):
            score -= 8
        if username and len(username) >= 3:
            u = username.lower()
            p = pw.lower()
            if p == u:
                score -= 20
            elif u in p:
                score -= 15
        score = max(0, min(100, score))

    level = _level(score)
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
