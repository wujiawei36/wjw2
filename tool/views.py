import base64
import hashlib
import json
import logging
import re
import secrets
import uuid
from datetime import datetime, timezone as dt_timezone

from django.http import JsonResponse
from django.shortcuts import render
from django.templatetags.static import static
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from utils.get_ip import get_ip
from .models import ApiKey, hash_api_key, bump_api_counter
from .ratelimit import allow as rate_allow
from .registry import TOOLS, get_tool, format_rate_limit

logger = logging.getLogger(__name__)

# 随机密码字符集预设（与前端 password.js 保持一致）
PASSWORD_CHARSETS = {
    'all': ['ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz',
            '0123456789', '!@#$%^&*()-_=+[]{};:,.<>?'],
    'alnum': ['ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz',
              '0123456789'],
    'lower_digit': ['abcdefghijklmnopqrstuvwxyz', '0123456789'],
    'digits': ['0123456789'],
}


def tool_index(request):
    tools = [{**t, 'rate_limit_text': format_rate_limit(t)} for t in TOOLS]
    return render(request, 'tool/index.html', {'tools': tools})


def tool_detail(request, slug):
    tool = get_tool(slug)
    if tool is None:
        return render(request, 'tool/not_found.html', status=404)
    context = {'tool': tool, 'rate_limit_text': format_rate_limit(tool)}
    if tool['kind'] == 'frontend':
        # 用 static() 生成带 manifest hash 的完整静态 URL（生产 manifest 存储要求精确文件名）
        context['tool_js'] = static(f"tool/js/{slug}.js")
    # related：把 slug 转成 {slug, title} 供模板渲染链接
    context['related'] = [
        {'slug': r, 'title': get_tool(r)['title']}
        for r in tool.get('related', []) if get_tool(r)
    ]
    return render(request, 'tool/detail.html', context)


def _resolve_api_key(request):
    """从请求头提取 API Key，返回 (ApiKey | None, error_code | None)。"""
    key = request.headers.get('X-API-Key', '').strip()
    if not key:
        auth = request.headers.get('Authorization', '')
        if auth.startswith('Bearer '):
            key = auth[7:].strip()
    if not key:
        return None, 'MISSING_KEY'
    try:
        return ApiKey.objects.get(key_hash=hash_api_key(key)), None
    except ApiKey.DoesNotExist:
        return None, 'INVALID_KEY'


def _audit(request, slug, api_key, status):
    key_label = api_key.masked() if api_key else '-'
    logger.info('TOOL_API %s slug=%s key=%s ip=%s',
                status, slug, key_label, get_ip(request))


@csrf_exempt
@require_POST
def tool_api(request, slug):
    """工具 API 端点：API Key 鉴权 → 限流 → 后端计算 → 审计。

    所有工具（frontend/backend）均开放 API：浏览器用户走前端直算无需 Key，
    脚本通过本端点调用需携带 X-API-Key。
    """
    tool = get_tool(slug)
    if tool is None:
        return JsonResponse({'ok': False, 'error': 'UNSUPPORTED_SLUG'}, status=404)

    # 合法工具的 API 调用计数 +1（今日 + 累计）
    bump_api_counter()

    api_key, err = _resolve_api_key(request)
    anonymous = bool(tool.get('allow_anonymous') and err == 'MISSING_KEY')
    if anonymous:
        api_key = None
    elif err:
        _audit(request, slug, None, err)
        return JsonResponse({'ok': False, 'error': err}, status=401)

    if not anonymous:
        ok, err = api_key.validate(slug)
        if not ok:
            _audit(request, slug, api_key, err)
            return JsonResponse({'ok': False, 'error': err}, status=403)

    # 频率限流（带 Key 走 Key+IP 双维度；匿名手动获取仅 IP 维度）
    if anonymous:
        rl = tool.get('rate_limit')
        window, max_c = (rl['window'], rl['max']) if rl else (None, None)
        dim_keys = [f'{slug}:ip:{get_ip(request)}']
    else:
        window, max_c = api_key.rate_limit_for(tool.get('rate_limit'))
        dim_keys = [f'{slug}:key:{api_key.key_hash}', f'{slug}:ip:{get_ip(request)}']
    if max_c:
        for dim_key in dim_keys:
            ok, retry = rate_allow(dim_key, window, max_c)
            if not ok:
                _audit(request, slug, api_key, 'RATE_LIMITED')
                return JsonResponse(
                    {'ok': False, 'error': 'RATE_LIMITED'},
                    status=429,
                    headers={'Retry-After': str(retry)},
                )

    try:
        body = json.loads(request.body.decode('utf-8') or '{}')
    except json.JSONDecodeError:
        return JsonResponse({'ok': False, 'error': 'BAD_PARAM'}, status=400)
    text = str(body.get('input', ''))[:10000]

    if slug == 'md5':
        data = {'md5': hashlib.md5(text.encode('utf-8')).hexdigest()}
    elif slug == 'servertime':
        now = timezone.now()
        local = timezone.localtime(now)
        data = {
            'utc': now.strftime('%Y-%m-%d %H:%M:%S'),
            'local': local.strftime('%Y-%m-%d %H:%M:%S'),
            'timezone': str(local.tzinfo),
            'unix': int(now.timestamp()),
        }
    elif slug == 'ipinfo':
        data = {
            'ip': get_ip(request) or 'unknown',
            'user_agent': request.META.get('HTTP_USER_AGENT', ''),
        }
    elif slug == 'json':
        try:
            obj = json.loads(text)
        except json.JSONDecodeError as e:
            return JsonResponse(
                {'ok': False, 'error': 'BAD_PARAM', 'detail': f'Invalid JSON: {e}'}, status=400)
        data = {'text': json.dumps(obj, indent=2, ensure_ascii=False)}
    elif slug == 'sha':
        raw = text.encode('utf-8')
        data = {
            'sha1': hashlib.sha1(raw).hexdigest(),
            'sha256': hashlib.sha256(raw).hexdigest(),
            'sha384': hashlib.sha384(raw).hexdigest(),
            'sha512': hashlib.sha512(raw).hexdigest(),
        }
    elif slug == 'base64':
        mode = str(body.get('mode', 'encode')).lower()
        if mode == 'encode':
            data = {'text': base64.b64encode(text.encode('utf-8')).decode('ascii')}
        elif mode == 'decode':
            try:
                data = {'text': base64.b64decode(text.encode('ascii')).decode('utf-8')}
            except Exception as e:
                return JsonResponse(
                    {'ok': False, 'error': 'BAD_PARAM', 'detail': f'Invalid Base64: {e}'}, status=400)
        else:
            return JsonResponse(
                {'ok': False, 'error': 'BAD_PARAM', 'detail': 'mode must be "encode" or "decode"'}, status=400)
    elif slug == 'timestamp':
        s = text.strip()
        if not s:
            return JsonResponse({'ok': False, 'error': 'BAD_PARAM', 'detail': 'input is required'}, status=400)
        if re.fullmatch(r'-?\d+', s):
            n = int(s)
            ms = n * 1000 if abs(n) < 100_000_000_000 else n
            try:
                dt = datetime.fromtimestamp(ms / 1000, tz=timezone.get_current_timezone())
            except (ValueError, OverflowError, OSError):
                return JsonResponse({'ok': False, 'error': 'BAD_PARAM', 'detail': 'Invalid timestamp'}, status=400)
            data = {
                'local': dt.strftime('%Y-%m-%d %H:%M:%S'),
                'utc': dt.astimezone(dt_timezone.utc).strftime('%Y-%m-%d %H:%M:%S'),
                'unix_seconds': int(dt.timestamp()),
                'unix_ms': int(dt.timestamp() * 1000),
            }
        else:
            try:
                dt = datetime.fromisoformat(s.replace(' ', 'T'))
            except ValueError:
                return JsonResponse({'ok': False, 'error': 'BAD_PARAM', 'detail': 'Invalid date (use YYYY-MM-DD HH:mm:ss)'}, status=400)
            if dt.tzinfo is None:
                dt = timezone.make_aware(dt)
            data = {
                'seconds': int(dt.timestamp()),
                'milliseconds': int(dt.timestamp() * 1000),
            }
    elif slug == 'uuid':
        s = text.strip()
        if s == '':
            n = 1
        else:
            if not s.isdigit():
                return JsonResponse({'ok': False, 'error': 'BAD_PARAM',
                                     'detail': 'count must be an integer (1~1000)'}, status=400)
            n = int(s)
            if n < 1 or n > 1000:
                return JsonResponse({'ok': False, 'error': 'BAD_PARAM',
                                     'detail': 'count must be between 1 and 1000'}, status=400)
        data = {'count': n, 'uuids': [str(uuid.uuid4()) for _ in range(n)]}
    elif slug == 'password':
        # 长度（input）
        s = text.strip()
        if s == '':
            n = 16
        else:
            if not s.isdigit():
                return JsonResponse({'ok': False, 'error': 'BAD_PARAM',
                                     'detail': 'length must be an integer (4~256)'}, status=400)
            n = int(s)
            if n < 4 or n > 256:
                return JsonResponse({'ok': False, 'error': 'BAD_PARAM',
                                     'detail': 'length must be between 4 and 256'}, status=400)
        # 数量（count）
        cnt_s = str(body.get('count', '1')).strip()
        if cnt_s == '':
            cnt = 1
        else:
            if not cnt_s.isdigit():
                return JsonResponse({'ok': False, 'error': 'BAD_PARAM',
                                     'detail': 'count must be an integer (1~100)'}, status=400)
            cnt = int(cnt_s)
            if cnt < 1 or cnt > 100:
                return JsonResponse({'ok': False, 'error': 'BAD_PARAM',
                                     'detail': 'count must be between 1 and 100'}, status=400)
        # 字符集（charset）
        cs = str(body.get('charset', 'all')).strip().lower()
        if cs not in PASSWORD_CHARSETS:
            return JsonResponse({'ok': False, 'error': 'BAD_PARAM',
                                 'detail': 'charset must be one of: all, alnum, lower_digit, digits'}, status=400)
        groups = PASSWORD_CHARSETS[cs]
        pool = ''.join(groups)

        def _gen():
            # 保证每个字符组至少出现一次，再随机填充，最后打乱
            chars = [secrets.choice(g) for g in groups]
            chars += [secrets.choice(pool) for _ in range(n - len(groups))]
            secrets.SystemRandom().shuffle(chars)
            return ''.join(chars)

        data = {'passwords': [_gen() for _ in range(cnt)],
                'count': cnt, 'length': n, 'charset': cs}
    elif slug == 'wordcount':
        data = {
            'chars': len(text),
            'bytes': len(text.encode('utf-8')),
            'lines': len(text.split('\n')) if text else 0,
            'no_space': len(re.sub(r'\s', '', text)),
            'chinese': len(re.findall(r'[\u4e00-\u9fa5]', text)),
        }
    elif slug == 'color':
        s = text.strip()
        if not s:
            return JsonResponse({'ok': False, 'error': 'BAD_PARAM', 'detail': 'input is required'}, status=400)
        if s.startswith('#'):
            hex_s = s[1:]
            if len(hex_s) == 3:
                hex_s = ''.join(c + c for c in hex_s)
            if not re.fullmatch(r'[0-9a-fA-F]{6}', hex_s):
                return JsonResponse({'ok': False, 'error': 'BAD_PARAM', 'detail': 'Invalid HEX (use #RRGGBB or #RGB)'}, status=400)
            r, g, b = int(hex_s[0:2], 16), int(hex_s[2:4], 16), int(hex_s[4:6], 16)
            data = {'r': r, 'g': g, 'b': b, 'rgb': f'rgb({r}, {g}, {b})'}
        else:
            m = re.match(r'rgba?\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*', s, re.I)
            if not m:
                return JsonResponse({'ok': False, 'error': 'BAD_PARAM', 'detail': 'Use rgb(r,g,b) format'}, status=400)
            r, g, b = (max(0, min(255, int(x))) for x in m.groups())
            data = {'hex': '#' + ''.join(f'{v:02X}' for v in (r, g, b))}
    elif slug == 'number':
        s = text.strip()
        if not s:
            return JsonResponse({'ok': False, 'error': 'BAD_PARAM', 'detail': 'input is required'}, status=400)
        if re.fullmatch(r'0x[0-9a-f]+', s, re.I):
            n = int(s, 16)
        elif re.fullmatch(r'0b[01]+', s, re.I):
            n = int(s[2:], 2)
        elif re.fullmatch(r'0o[0-7]+', s, re.I):
            n = int(s[2:], 8)
        elif re.fullmatch(r'-?\d+', s):
            n = int(s, 10)
        else:
            return JsonResponse({'ok': False, 'error': 'BAD_PARAM', 'detail': 'Enter a decimal integer or 0x/0b/0o prefixed number'}, status=400)
        data = {'dec': str(n), 'hex': '0x' + format(n, 'X'), 'oct': '0o' + format(n, 'o'), 'bin': '0b' + format(n, 'b')}
    elif slug == 'regex':
        parts = text.split('\n')
        pattern = parts[0] if parts else ''
        subject = '\n'.join(parts[1:])
        if not pattern:
            return JsonResponse({'ok': False, 'error': 'BAD_PARAM', 'detail': 'First line must be the regex pattern'}, status=400)
        try:
            matches = [m.group(0) for m in re.finditer(pattern, subject)]
        except re.error as e:
            return JsonResponse({'ok': False, 'error': 'BAD_PARAM', 'detail': f'Invalid regex: {e}'}, status=400)
        data = {'count': len(matches), 'matches': matches}
    elif slug == 'text':
        lines = text.split('\n')
        seen = set()
        out = []
        for line in lines:
            if line not in seen:
                seen.add(line)
                out.append(line)
        data = {'text': '\n'.join(out), 'lines': len(lines), 'unique': len(out)}
    else:
        return JsonResponse({'ok': False, 'error': 'UNSUPPORTED_SLUG'}, status=404)

    if api_key:
        api_key.used += 1
        api_key.last_used_at = timezone.now()
        api_key.save(update_fields=['used', 'last_used_at'])
    _audit(request, slug, api_key, 'OK')
    return JsonResponse({'ok': True, 'data': data})
