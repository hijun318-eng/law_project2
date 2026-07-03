import json

from django.http import HttpResponseForbidden, JsonResponse
from django.shortcuts import redirect, render
from django.views.decorators.csrf import ensure_csrf_cookie
from django.views.decorators.http import require_POST

from .services import advice, calculator, dashboard, news

# DB 연결하고 삭제 필요
_DEMO_USERS = {
    "admin@example.com": {
        "name": "관리자",
        "password": "11111111",
        "role": "admin",
    },
    "user@example.com": {
        "name": "김민준",
        "password": "11111111",
        "role": "user",
    },
}

def example(request):
    return render(request, 'example/example.html')


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

        account = _DEMO_USERS.get(email) if email else None

        # 데모 구현: 비밀번호 해시 비교는 없지만, "가입된 이메일인지" +
        # "값이 비어있지 않은지"는 검증해 실패 케이스를 만들어둔다.
        if not email or not password or account is None or account["password"] != password:
            return render(
                request,
                "labor/_login.html",
                {
                    "error": "이메일 또는 비밀번호가 일치하지 않습니다.",
                    "email": email,
                },
                status=401,
            )

        request.session["labor_user"] = {
            "name": account["name"],
            "email": email,
            "role": account["role"],
        }

        if account["role"] == "admin":
            return redirect("admin_console")
        return redirect("landing")

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
        elif email in _DEMO_USERS:
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

        _DEMO_USERS[email] = {"name": name, "password": password, "role": "user"}
        request.session["labor_user"] = {"name": name, "email": email, "role": "user"}
        return redirect("landing")
    
    return render(request, "labor/_register.html")


def logout_view(request):
    request.session.pop("labor_user", None)
    return redirect("landing")


def user_app(request):
    user = _current_user(request)
    if not user:
        return redirect("login")
    page = request.GET.get("page", "home")
    if page not in {"home", "calculator", "news", "mypage"}:
        page = "home"
    news_items = news.search_news()
    return render(
        request,
        "labor/app.html",
        {
            "user": user,
            "page": page,
            "quick_questions": advice.quick_questions(),
            "minimum_wage": calculator.MINIMUM_WAGE_2026,
            "news_categories": news.categories(),
            "news_items": news_items,
            "news_summary": news.summarize("", news_items),
            "history": [
                {"q": "퇴직금 계산 방법이 궁금합니다", "date": "2026-06-29", "category": "퇴직금"},
                {"q": "임금체불 신고는 어디에 하나요?", "date": "2026-06-28", "category": "임금체불"},
                {"q": "연차가 남아있는데 퇴직 시 어떻게 되나요?", "date": "2026-06-25", "category": "연차휴가"},
            ],
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
def prompt_api(request):
    payload = _json_payload(request)
    action = payload.get("action")
    template_id = payload.get("id")

    if action == "get":
        return JsonResponse(dashboard.get_prompt_template(template_id))

    if action == "validate":
        errors = dashboard.validate_prompt_content(template_id, payload.get("content", ""))
        return JsonResponse({"errors": errors})

    if action == "save":
        dashboard.save_prompt_template(template_id, payload.get("content", ""))
        return JsonResponse({"ok": True})

    if action == "test":
        preview = dashboard.test_prompt_template(template_id, payload.get("content", ""), payload.get("query", ""))
        return JsonResponse({"preview": preview})

    if action == "rollback":
        dashboard.rollback_prompt_template(template_id, payload.get("version"))
        return JsonResponse({"ok": True})

    return JsonResponse({"error": "unknown action"}, status=400)

@require_POST
def advice_api(request):
    payload = _json_payload(request)
    question = payload.get("question", "")
    return JsonResponse({"answer": advice.answer_question(question)})


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


def news_api(request):
    query = request.GET.get("q", "")
    category = request.GET.get("category", "전체")
    items = news.search_news(query, category)
    return JsonResponse({"items": items, "summary": news.summarize(query, items)})


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
