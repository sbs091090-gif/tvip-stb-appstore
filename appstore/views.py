from django.http import HttpResponse, HttpResponseNotModified, JsonResponse
from django.utils.http import parse_etags
from django.views.decorators.http import require_safe
from . import cache


@require_safe
def catalog(request):
    address = request.META.get('HTTP_X_REAL_IP')
    if not address:
        return JsonResponse({'error': 'Missing client address'}, status=400)
    try:
        snapshot = cache.current()
        body, etag = snapshot.response(address)
    except ValueError:
        return JsonResponse({'error': 'Invalid client address'}, status=400)
    except cache.Unavailable:
        return JsonResponse({'error': 'Catalog is warming up'}, status=503)
    tags = parse_etags(request.META.get('HTTP_IF_NONE_MATCH', ''))
    if '*' in tags or etag in [tag.removeprefix('W/') for tag in tags]:
        response = HttpResponseNotModified()
    else:
        response = HttpResponse(body if request.method != 'HEAD' else b'', content_type='application/json; charset=utf-8')
    response['ETag'] = etag
    response['Cache-Control'] = 'private, no-cache'
    response['Vary'] = 'X-Real-IP'
    return response


@require_safe
def health(request):
    try:
        cache.current()
        return JsonResponse({'status': 'ok'})
    except cache.Unavailable:
        return JsonResponse({'status': 'warming'}, status=503)
