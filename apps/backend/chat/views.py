# pyright: reportAttributeAccessIssue=false

from django.http import StreamingHttpResponse, JsonResponse
from django.shortcuts import render, get_object_or_404, redirect
from django.views.decorators.csrf import csrf_exempt
import json

from .models import ChatHistory
from engine.router_engine import LawRouterEngine
from engine.rag_engine import RAGEngine
from engine.calculator_engine import CalculatorEngine
from engine.tools.news_search_tool import NewsSearchTool

router_engine = LawRouterEngine()


@csrf_exempt
def chat_view(request):
    """통합 chat view — GET: 템플릿, POST: SSE 스트리밍 또는 동기식 처리"""
    if request.method == 'POST':
        if request.headers.get('accept') == 'text/event-stream':
            return chat_stream(request)
        return chat_sync(request)
    return render(request, 'chat/chat.html')


def chat_sync(request):
    """POST (non-SSE): 동기식 JSON 응답 (fallback)"""
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        data = request.POST.dict()

    question = data.get('question', '').strip()
    if not question:
        return JsonResponse({'error': 'Question is required'}, status=400)

    session_key = request.session.session_key or request.session.create()
    chat = ChatHistory.objects.create(
        session_key=session_key,
        question=question,
        user=request.user if request.user.is_authenticated else None,
    )

    try:
        result = router_engine.run(question)
        chat.answer = result.content
        chat.mode = result.mode
        chat.save()
        return JsonResponse({'answer': result.content, 'mode': result.mode})
    except Exception as e:
        chat.answer = f'오류 발생: {str(e)}'
        chat.save()
        return JsonResponse({'error': str(e)}, status=500)


def chat_stream(request):
    """POST + Accept: text/event-stream — SSE 스트리밍 응답"""
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        data = request.POST.dict()

    question = data.get('question', '').strip()
    if not question:
        return JsonResponse({'error': 'Question is required'}, status=400)

    session_key = request.session.session_key or request.session.create()
    chat = ChatHistory.objects.create(
        session_key=session_key,
        question=question,
        user=request.user if request.user.is_authenticated else None,
    )

    def event_stream():
        final_answer = ''
        final_sources = []
        final_mode = 'rag'

        try:
            # 1. RouterEngine으로 질문 모드 분류
            mode = router_engine.route(question)
            final_mode = mode
            ChatHistory.objects.filter(pk=chat.pk).update(mode=mode)

            # 2. 모드 정보 SSE 전송
            yield f"data: {json.dumps({'type': 'mode', 'mode': mode}, ensure_ascii=False)}\n\n"

            # 3. 모드별 처리
            if mode == 'case_based_answer':
                rag = RAGEngine()
                for node_name, label, detail in rag.stream_answer(question):
                    yield f"data: {json.dumps({'type': 'node', 'name': node_name, 'label': label, 'detail': str(detail)}, ensure_ascii=False)}\n\n"
                    if node_name == 'done':
                        detail_dict = detail if isinstance(detail, dict) else {}
                        final_answer = detail_dict.get('answer', '') or str(detail)
                        final_sources = detail_dict.get('sources', [])

            elif mode == 'procedure_guidance':
                from engine.graph import graph_procedure
                state = graph_procedure.invoke({'question': question})
                final_answer = state.get('procedure_guide', '')
                yield f"data: {json.dumps({'type': 'node', 'name': 'procedure_guide', 'label': '📋 절차 안내', 'detail': '절차 안내 생성 완료'}, ensure_ascii=False)}\n\n"

            elif mode == 'allowance_calculator':
                calc = CalculatorEngine()
                res = calc.calculate(question)
                final_answer = res.get('answer', '')
                yield f"data: {json.dumps({'type': 'node', 'name': 'calculator', 'label': '🧮 수당 계산', 'detail': '계산 완료'}, ensure_ascii=False)}\n\n"

            elif mode == 'latest_news':
                news = NewsSearchTool()
                res = news.run(query=question, display=5)
                if res.success and res.data.get('results'):
                    items = res.data['results']
                    content_lines = ['📰 **관련 최신 뉴스 검색 결과입니다.**', '']
                    for i, item in enumerate(items, 1):
                        title = item.get('title', '제목 없음')
                        link = item.get('link', '#')
                        desc = item.get('description', '')
                        content_lines.append(f'**{i}. [{title}]({link})**')
                        content_lines.append(f'> {desc}...')
                        content_lines.append('')
                    final_answer = '\n'.join(content_lines)
                else:
                    final_answer = '⚠️ 관련 최신 뉴스를 찾을 수 없습니다.'
                yield f"data: {json.dumps({'type': 'node', 'name': 'news', 'label': '📰 뉴스 검색', 'detail': '검색 완료'}, ensure_ascii=False)}\n\n"

            # 4. ChatHistory 업데이트 (answer, mode, sources)
            ChatHistory.objects.filter(pk=chat.pk).update(
                answer=final_answer,
                sources=final_sources,
            )

        except Exception as e:
            import traceback
            traceback.print_exc()
            error_msg = str(e)
            yield f"data: {json.dumps({'type': 'error', 'message': error_msg}, ensure_ascii=False)}\n\n"

        # 5. SSE 종료 신호
        yield "data: [DONE]\n\n"

    return StreamingHttpResponse(event_stream(), content_type='text/event-stream')


def result_view(request, id):
    chat = get_object_or_404(ChatHistory, id=id)
    return render(request, 'chat/result.html', {'chat': chat})


def history_view(request):
    session_key = request.session.session_key
    if not session_key:
        request.session.create()
        session_key = request.session.session_key

    chats = ChatHistory.objects.filter(session_key=session_key)

    # 검색
    q = request.GET.get('q', '')
    if q:
        chats = chats.filter(question__icontains=q)

    # 페이지네이션 (20개/page)
    from django.core.paginator import Paginator
    paginator = Paginator(chats, 20)
    page = request.GET.get('page', 1)
    chats_page = paginator.get_page(page)

    return render(request, 'chat/history.html', {
        'chats': chats_page,
        'q': q,
    })


def delete_view(request, id):
    if request.method == 'POST':
        chat = get_object_or_404(ChatHistory, id=id)
        chat.delete()
    return redirect('chat:history')
