import base64
import hashlib
import json
import logging

from django.http import JsonResponse
from django.shortcuts import render
from django.templatetags.static import static
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from utils.get_ip import get_ip
from .models import ApiKey, hash_api_key
from .ratelimit import allow as rate_allow
from .registry import TOOLS, get_tool

logger = logging.getLogger(__name__)


def tool_index(request):
    return render(request, 'tool/index.html', {'tools': TOOLS})


def tool_detail(request, slug):
    tool = get_tool(slug)
    if tool is None:
        return render(request, 'tool/not_found.html', status=404)
    context = {'tool': tool}
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
    else:
        return JsonResponse({'ok': False, 'error': 'UNSUPPORTED_SLUG'}, status=404)

    if api_key:
        api_key.used += 1
        api_key.last_used_at = timezone.now()
        api_key.save(update_fields=['used', 'last_used_at'])
    _audit(request, slug, api_key, 'OK')
    return JsonResponse({'ok': True, 'data': data})
