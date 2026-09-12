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
    """后端工具 API 端点：API Key 鉴权 → 限流 → 后端计算 → 审计。"""
    tool = get_tool(slug)
    if tool is None:
        return JsonResponse({'ok': False, 'error': 'UNSUPPORTED_SLUG'}, status=404)
    if tool['kind'] != 'backend':
        return JsonResponse({'ok': False, 'error': 'NOT_API_TOOL'}, status=400)

    api_key, err = _resolve_api_key(request)
    if err:
        _audit(request, slug, None, err)
        return JsonResponse({'ok': False, 'error': err}, status=401)

    ok, err = api_key.validate(slug)
    if not ok:
        _audit(request, slug, api_key, err)
        return JsonResponse({'ok': False, 'error': err}, status=403)

    # 频率限流（Key 维度 + IP 维度，双保险）
    window, max_c = api_key.rate_limit_for(tool.get('rate_limit'))
    if max_c:
        ip = get_ip(request)
        for dim_key in (f'{slug}:key:{api_key.key_hash}', f'{slug}:ip:{ip}'):
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
        data = {'text': (
            'UTC: ' + now.strftime('%Y-%m-%d %H:%M:%S') + '\n'
            '本地: ' + local.strftime('%Y-%m-%d %H:%M:%S') + ' (' + str(local.tzinfo) + ')\n'
            'Unix 时间戳(秒): ' + str(int(now.timestamp()))
        )}
    elif slug == 'ipinfo':
        data = {'text': (
            'IP: ' + (get_ip(request) or '未知') + '\n'
            'User-Agent: ' + request.META.get('HTTP_USER_AGENT', '')
        )}
    else:
        return JsonResponse({'ok': False, 'error': 'UNSUPPORTED_SLUG'}, status=404)

    api_key.used += 1
    api_key.last_used_at = timezone.now()
    api_key.save(update_fields=['used', 'last_used_at'])
    _audit(request, slug, api_key, 'OK')
    return JsonResponse({'ok': True, 'data': data})
