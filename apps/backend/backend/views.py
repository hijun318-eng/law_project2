import json

from django.core.exceptions import ObjectDoesNotExist, ValidationError
from django.http import HttpResponseForbidden, JsonResponse
from django.shortcuts import redirect, render
from django.views.decorators.csrf import ensure_csrf_cookie
from django.views.decorators.http import require_POST

from .services import calculator, dashboard
from engine.router_engine import router_engine
from engine.tools.news_search_tool import NewsSearchTool
from django.contrib.auth import authenticate, login as auth_login, logout as auth_logout
from django.contrib.auth.models import User

from chat.models import ChatHistory

news_search_tool = NewsSearchTool()

# advice.py quick_questions() → 인라인 상수
_QUICK_QUESTIONS = [
    "퇴직금은 어떻게 계산하나요?",
    "임금체불 신고는 어디에 하나요?",
    "부당해고를 당했습니다. 어떻게 해야 하나요?",
    "주휴수당은 어떻게 계산하나요?",
]

def _ensure_default_users():
    """최초 실행 시 데모 계정이 없으면 DB에 생성 (비밀번호 해싱됨)"""
    if User.objects.filter(username="admin@example.com").exists():
        return
    User.objects.create_superuser(
        username="admin@example.com",
        email="admin@example.com",
        password="11111111",
        first_name="관리자",
    )
    User.objects.create_user(
        username="user@example.com",
        email="user@example.com",
        password="11111111",
        first_name="김민준",
    )

try:
    _ensure_default_users()
except Exception:
    # DB 테이블이 아직 생성되지 않은 경우(migrate 전) 무시
    pass

def landing(request):
    user = _current_user(request)
    if user and user["role"] == "admin":
        return redirect("admin_console")
    
    return render(
        request,
        "labor/landing.html",
        {
            "user": user,
            "data_sources": [
                "근로기준법", "산업안전보건법", "노동위원회 판례",
                "고용노동부 행정해석", "중앙노동위원회", "대법원 판례",
            ],
            "feature_cards": [
                {"variant": "dark", "icon": "⚖", "title": "노동법 RAG 상담", "desc": "사용자 질문을 바탕으로 법령·판례·질의회시 벡터 DB를 검색하고, 관련 근거를 함께 정리해 답변합니다.", "stat_label": "검색 대상", "stat_value": "법령·판례·Q&A"},
                {"variant": "light", "icon": "▤", "title": "근거 출처 표시", "desc": "답변 화면에서 참고한 법령명, 조문, 판례 정보를 별도 카드로 보여주도록 설계했습니다.", "stat_label": "표시 정보", "stat_value": "조문·판례"},
                {"variant": "light", "icon": "◈", "title": "질문 유형 라우팅", "desc": "법률 상담, 절차 안내, 수당 계산, 최신 뉴스 질문을 구분해 알맞은 처리 흐름으로 연결합니다.", "stat_label": "처리 흐름", "stat_value": "4종"},
                {"variant": "tan", "icon": "◔", "title": "수당 계산 지원", "desc": "퇴직금, 연차수당, 주휴수당, 최저임금 위반 여부를 입력값 기준으로 계산합니다.", "stat_label": "계산 항목", "stat_value": "4개"},
                {"variant": "dashed", "icon": "✓", "title": "최신 뉴스 검색", "desc": "네이버 뉴스 API를 통해 노동법·노동 이슈 관련 기사를 검색하고 요약 화면에 연결합니다.", "stat_label": "외부 연동", "stat_value": "Naver API"},
                {"variant": "dashed", "icon": "↗", "title": "회원/관리자 화면", "desc": "세션 기반 로그인 후 사용자 앱으로 이동하고, 관리자 계정은 운영 대시보드 화면에 접근합니다.", "stat_label": "접근 구분", "stat_value": "User/Admin"},
            ],
            "steps": [
                {"title": "자연어로 질문", "desc": "“3개월 일하고 갑자기 해고 통보를 받았어요. 실업급여 받을 수 있을까요?” 처럼 편하게 물어보세요."},
                {"title": "AI가 법령·판례 분석", "desc": "GraphRAG가 근로기준법 조항, 노동위원회 판례, 행정해석을 동시에 참조해 근거를 정리합니다."},
                {"title": "근거와 함께 답변 저장", "desc": "답변, 인용 조항, 판례 요약이 함께 히스토리에 저장됩니다. 필요 시 전문가 상담으로 이어집니다."},
            ],
        },
    )


def login_view(request):
    if request.method == "POST":
        email = request.POST.get("email", "").strip().lower()
        password = request.POST.get("password", "").strip()

        user = authenticate(request, username=email, password=password)

        if user is not None:
            auth_login(request, user)
            request.session["labor_user"] = {
                "name": user.first_name,
                "email": user.username,
                "role": "admin" if user.is_staff else "user",
                "join_date": user.date_joined.strftime("%Y-%m-%d"),
            }
            return redirect("admin_console") if user.is_staff else redirect("landing")

        return render(
            request,
            "labor/_login.html",
            {"error": "이메일 또는 비밀번호가 일치하지 않습니다.", "email": email},
            status=401,
        )

    return render(request, "labor/_login.html")


def register_view(request):
    if request.method == "POST":
        name = request.POST.get("name", "").strip()
        email = request.POST.get("email", "").strip().lower()
        password = request.POST.get("password", "")
        password_confirm = request.POST.get("password_confirm", "")

        error = None
        if not name or not email or not password or not password_confirm:
            error = "모든 항목을 입력해주세요."
        elif User.objects.filter(username=email).exists():
            error = "이미 가입된 이메일이 있습니다."
        elif password != password_confirm:
            error = "비밀번호가 일치하지 않습니다."
        elif len(password) < 8:
            error = "비밀번호는 8자 이상이어야 합니다."

        if error:
            return render(
                request,
                "labor/_register.html",
                {"error": error, "name": name, "email": email},
                status=400,
            )

        user = User.objects.create_user(
            username=email,
            email=email,
            password=password,
            first_name=name,
        )

        # 회원가입 후 자동 로그인
        auth_login(request, user)
        request.session["labor_user"] = {
            "name": user.first_name,
            "email": user.username,
            "role": "user",
            "join_date": user.date_joined.strftime("%Y-%m-%d"),
        }
        return redirect("landing")

    return render(request, "labor/_register.html")


def logout_view(request):
    request.session.pop("labor_user", None)
    auth_logout(request)
    return redirect("landing")


def user_app(request):
    user = _current_user(request)
    if not user:
        return redirect("login")
    # 세션에 가입일이 없으면 DB에서 조회 (기존 로그인 사용자 대응)
    if "join_date" not in user:
        try:
            db_user = User.objects.get(username=user["email"])
            user["join_date"] = db_user.date_joined.strftime("%Y-%m-%d")
        except User.DoesNotExist:
            pass
    page = request.GET.get("page", "home")
    if page not in {"home", "calculator", "news", "mypage"}:
        page = "home"

    # NewsSearchTool 직접 호출
    news_res = news_search_tool.run(query="노동법", display=10)
    news_items = []
    if news_res.success and news_res.data.get("results"):
        for i, item in enumerate(news_res.data["results"], start=1):
            news_items.append({
                "id": i,
                "title": item.get("title", ""),
                "date": _format_pubdate(item.get("pubDate", "")),
                "summary": item.get("description", ""),
            })
    news_summary_text = (
        f"최신 노동법 뉴스 {len(news_items)}건" if news_items
        else "뉴스를 불러오지 못했습니다."
    )

    return render(
        request,
        "labor/app.html",
        {
            "user": user,
            "page": page,
            "initial_question": request.GET.get("question", "").strip(),
            "quick_questions": _QUICK_QUESTIONS,
            "minimum_wage": calculator.MINIMUM_WAGE_2026,
            "news_items": news_items,
            "news_summary": news_summary_text,
            "history": [
                {
                    "id": h.id,
                    "q": h.question,
                    "date": h.created_at.strftime("%Y-%m-%d"),
                    "category": h.mode or "rag",
                    "feedback": h.feedback,
                }
                for h in ChatHistory.objects.filter(user__first_name=user["name"]).order_by("-created_at")[:20]
            ],
            "history_count": ChatHistory.objects.filter(user__first_name=user["name"]).count(),
        },
    )

_TAB_CONTEXT_BUILDERS = {
    "dashboard": dashboard.dashboard_context,
    "users": dashboard.users_context,
    "feedback": dashboard.feedback_context,
    "prompts": dashboard.prompts_context,
    "vectordb": dashboard.vectordb_context,
    "performance": dashboard.performance_context,
}


@ensure_csrf_cookie
def admin_console(request):
    user = _current_user(request)
    if not user:
        return redirect("login")
    if user["role"] != "admin":
        return HttpResponseForbidden("이 페이지에 접근할 권한이 없습니다.")
    tab = request.GET.get("tab", "dashboard")
    if tab not in _TAB_CONTEXT_BUILDERS:
        tab = "dashboard"
    context = {"user": user, "tab": tab}
    context.update(_TAB_CONTEXT_BUILDERS[tab]())
    return render(request, "labor/admin.html", context)


@require_POST
def admin_toggle_user_status(request):
    payload = _json_payload(request)
    user_id = payload.get("user_id")
    new_status = payload.get("status")  # "active" 또는 "suspended"

    from .services.dashboard import MOCK_USERS
    for user in MOCK_USERS:
        if user["id"] == user_id:
            user["status"] = new_status
            return JsonResponse({"ok": True, "user_id": user_id, "status": new_status})

    return JsonResponse({"error": "User not found"}, status=404)


@require_POST
def admin_rebuild_vectordb(request):
    payload = _json_payload(request)
    db_id = payload.get("id", "")
    return JsonResponse({"ok": True, "status": "completed", "db_id": db_id})


@require_POST
def admin_reprocess_failed(request):
    payload = _json_payload(request)
    failed_id = payload.get("id")
    return JsonResponse({"ok": True, "failed_id": failed_id})


def admin_performance_data(request):
    from .services.dashboard import performance_context, _get_period_usage
    data = performance_context()
    period = request.GET.get("period", "day")
    data["llm_usage"] = _get_period_usage(period)
    return JsonResponse(data)


@require_POST
def prompt_api(request):
    payload = _json_payload(request)
    action = payload.get("action")
    template_id = payload.get("id")
    user = _current_user(request) or {}
    updated_by = user.get("name") or user.get("email") or "관리자"

    if action == "get":
        return JsonResponse(dashboard.get_prompt_template(template_id))

    if action == "validate":
        errors = dashboard.validate_prompt_content(template_id, payload.get("content", ""))
        return JsonResponse({"errors": errors})

    if action == "save":
        try:
            dashboard.save_prompt_template(template_id, payload.get("content", ""), updated_by=updated_by)
            return JsonResponse({"ok": True})
        except (ObjectDoesNotExist, ValidationError, ValueError, TypeError) as exc:
            return JsonResponse({"error": str(exc)}, status=400)

    if action == "rollback":
        try:
            dashboard.rollback_prompt_template(template_id, payload.get("version"), updated_by=updated_by)
            return JsonResponse({"ok": True})
        except (ObjectDoesNotExist, ValidationError, ValueError, TypeError) as exc:
            return JsonResponse({"error": str(exc)}, status=400)

    return JsonResponse({"error": "unknown action"}, status=400)

@require_POST
def advice_api(request):
    payload = _json_payload(request)
    question = payload.get("question", "")
    if not question:
        return JsonResponse({"error": "질문을 입력해주세요."}, status=400)

    mode = payload.get("mode", "rag")
    session_key = request.session.session_key or request.session.create()
    user = request.user if request.user.is_authenticated else None

    chat = ChatHistory.objects.create(
        session_key=session_key,
        question=question,
        mode=mode,
        user=user,
    )

    answer = ""
    try:
        result = router_engine.run(question, session_id=str(chat.id))
        answer = result.content
        chat.mode = result.mode
    except Exception as e:
        answer = f"오류 발생: {str(e)}"
    finally:
        chat.answer = answer
        chat.save()

    return JsonResponse({"answer": answer, "message_id": chat.id})


@require_POST
def feedback_api(request):
    try:
        payload = _json_payload(request)
    except (ValueError, TypeError):
        return JsonResponse({"error": "요청 본문을 해석할 수 없습니다."}, status=400)

    if not isinstance(payload, dict):
        return JsonResponse({"error": "요청 본문을 해석할 수 없습니다."}, status=400)

    try:
        message_id = int(payload.get("message_id"))
    except (TypeError, ValueError):
        return JsonResponse({"error": "message_id가 필요합니다."}, status=400)

    action = payload.get("action", "")

    # action validation
    if action not in ("like", "dislike"):
        return JsonResponse({"error": "올바르지 않은 action입니다."}, status=400)

    try:
        chat = ChatHistory.objects.get(pk=message_id)
    except ChatHistory.DoesNotExist:
        return JsonResponse({"error": "메시지를 찾을 수 없습니다."}, status=404)

    # Toggle logic
    if chat.feedback is None:
        if action == "like":
            chat.feedback = True
        else:  # dislike
            chat.feedback = False
    elif chat.feedback is True:
        if action == "like":
            chat.feedback = None  # cancel
        else:  # dislike
            chat.feedback = False  # switch
    else:  # chat.feedback is False
        if action == "like":
            chat.feedback = True  # switch
        else:  # dislike
            chat.feedback = None  # cancel

    try:
        chat.save(update_fields=["feedback"])
    except Exception:
        return JsonResponse({"error": "피드백 저장 중 오류가 발생했습니다."}, status=500)

    return JsonResponse({"ok": True, "feedback": chat.feedback})


@require_POST
def calculate_api(request):
    payload = _json_payload(request)
    mode = payload.get("mode", "form")
    if mode == "chat":
        message, result = calculator.calculate_natural(payload.get("text", ""))
    else:
        result = calculator.calculate_form(
            payload.get("calc_type", "severance"),
            _float(payload.get("salary"), 0),
            _float(payload.get("months"), 14),
            _float(payload.get("hours"), 40),
        )
        message = f"{result.label}은 {calculator.format_won(result.amount)}입니다."
    return JsonResponse({"message": message, "result": result.to_dict() if result else None})


def history_detail_api(request, history_id):
    try:
        chat = ChatHistory.objects.get(pk=history_id)
    except ChatHistory.DoesNotExist:
        return JsonResponse({"error": "not found"}, status=404)

    return JsonResponse({
        "id": chat.id,
        "question": chat.question,
        "answer": chat.answer,
        "mode": chat.mode,
        "feedback": chat.feedback,
        "sources": chat.sources,
        "created_at": chat.created_at.isoformat(),
    })


def news_api(request):
    query = request.GET.get("q", "")

    res = news_search_tool.run(query=query if query.strip() else "노동법", display=10)

    if res.success and res.data.get("results"):
        items = []
        for item in res.data["results"]:
            items.append({
                "title": item.get("title", ""),
                "summary": item.get("description", ""),
                "date": _format_pubdate(item.get("pubDate", "")),
            })
        summary_text = f"'{query}' 관련 {len(items)}건의 뉴스를 찾았습니다." if query else f"최신 노동법 뉴스 {len(items)}건"
    else:
        items = []
        summary_text = "뉴스를 불러오지 못했습니다."

    return JsonResponse({"items": items, "summary": summary_text})


def _current_user(request):
    return request.session.get("labor_user")


def _json_payload(request) -> dict:
    try:
        return json.loads(request.body.decode("utf-8") or "{}")
    except json.JSONDecodeError:
        return {}


def _float(value, default: float) -> float:
    try:
        return float(str(value).replace(",", ""))
    except (TypeError, ValueError):
        return default


def _format_pubdate(pubdate: str) -> str:
    """Naver API pubDate (예: 'Tue, 30 Jun 2026 10:30:00 +0900') → '2026-06-30'"""
    import datetime
    try:
        dt = datetime.datetime.strptime(pubdate.split(" +")[0].split(" -")[0], "%a, %d %b %Y %H:%M:%S")
        return dt.strftime("%Y-%m-%d")
    except (ValueError, IndexError):
        return pubdate[:10] if len(pubdate) >= 10 else ""
