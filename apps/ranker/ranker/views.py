import json
import logging
from django.conf import settings
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

from .services.reranker import rerank

logger = logging.getLogger(__name__)


@csrf_exempt
@require_http_methods(['POST'])
def rerank_view(request):
    """
    POST /rerank/

    Request body:
        {"query": "검색어", "documents": ["문서1", "문서2", ...]}

    Response:
        {"scores": [0.95, 0.23, ...], "count": 2}

    Error response:
        {"error": "message"}
    """
    if settings.RANKER_API_KEY:
        auth_header = request.headers.get('Authorization', '')
        token = auth_header.removeprefix('Bearer ').strip()
        if token != settings.RANKER_API_KEY:
            return JsonResponse({'error': 'unauthorized'}, status=401)

    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)

    query = data.get('query', '').strip()
    documents = data.get('documents', [])

    if not query:
        return JsonResponse({'error': 'query is required'}, status=400)
    if not isinstance(documents, list) or len(documents) == 0:
        return JsonResponse({'error': 'documents list is required'}, status=400)

    try:
        scores = rerank(query, documents)
        return JsonResponse({
            'scores': scores,
            'count': len(scores),
        })
    except Exception as e:
        logger.exception('Rerank failed')
        return JsonResponse({'error': str(e)}, status=500)
