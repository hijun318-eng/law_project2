import json
from django.http import JsonResponse
from django.shortcuts import render, get_object_or_404
from .models import NewsBookmark
from engine.tools.news_search_tool import NewsSearchTool

news_tool = NewsSearchTool()

def news_list(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
        except json.JSONDecodeError:
            data = request.POST.dict()

        keyword = data.get('keyword', '').strip()
        if not keyword:
            return JsonResponse({'error': 'Keyword is required'}, status=400)

        res = news_tool.run(query=keyword, display=10)
        if res.success and res.data.get('results'):
            return JsonResponse({'results': res.data['results']})
        else:
            return JsonResponse({'error': res.error or '검색 결과가 없습니다.'}, status=404)

    return render(request, 'news/news.html')

def news_detail(request, id):
    bookmark = get_object_or_404(NewsBookmark, id=id)
    return render(request, 'news/detail.html', {'bookmark': bookmark})
