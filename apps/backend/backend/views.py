import json

from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.core.cache import cache
from django.core.exceptions import ObjectDoesNotExist, ValidationError
from django.http import HttpResponseForbidden, JsonResponse, StreamingHttpResponse
from django.shortcuts import redirect, render
from django.views import View
from django.views.decorators.csrf import ensure_csrf_cookie
from django.views.decorators.http import require_POST

from .services import calculator, dashboard, news
from engine.supervisor.engine import SupervisorEngine
from django.contrib.auth import authenticate, login as auth_login, logout as auth_logout
from django.contrib.auth.models import User

from chat.models import ChatHistory
from monitoring.models import PriceConfig
from engine.utils.execution_logger import clear_logger, get_logger, init_logger
from engine.utils.llm_errors import llm_error_message
import logging

logger = logging.getLogger(__name__)

supervisor_engine = SupervisorEngine()

# 로그인 잠금 (FR-009): 동일 계정 5회 연속 실패 시 10분간 로그인 차단
LOGIN_FAIL_LIMIT = 5
LOGIN_LOCKOUT_SECONDS = 10 * 60

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

        fail_key = f"login_fail:{email}"
        fail_count = cache.get(fail_key, 0)
        if fail_count >= LOGIN_FAIL_LIMIT:
            return render(
                request,
                "labor/_login.html",
                {"error": "로그인 시도가 너무 많습니다. 10분 후 다시 시도해주세요.", "email": email},
                status=429,
            )

        user = authenticate(request, username=email, password=password)

        if user is not None:
            cache.delete(fail_key)
            auth_login(request, user)
            request.session["labor_user"] = {
                "name": user.first_name,
                "email": user.username,
                "role": "admin" if user.is_staff else "user",
                "join_date": user.date_joined.strftime("%Y-%m-%d"),
            }
            return redirect("admin_console") if user.is_staff else redirect("landing")

        fail_count += 1
        cache.set(fail_key, fail_count, LOGIN_LOCKOUT_SECONDS)
        if fail_count >= LOGIN_FAIL_LIMIT:
            return render(
                request,
                "labor/_login.html",
                {"error": "로그인 5회 실패로 10분간 로그인이 제한됩니다.", "email": email},
                status=429,
            )

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

    # 뉴스 탭일 때만 NewsEngine 호출 (다른 탭에서는 불필요한 LLM 호출을 피함)
    if page == "news":
        news_items, news_summary_text = news.get_news()
    else:
        news_items, news_summary_text = [], ""

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
    is_active = payload.get("is_active")  # boolean

    try:
        user = User.objects.get(id=user_id)
    except User.DoesNotExist:
        return JsonResponse({"error": "User not found"}, status=404)

    if user.is_staff:
        return JsonResponse({"error": "관리자 계정은 정지할 수 없습니다."}, status=403)

    user.is_active = is_active
    user.save(update_fields=["is_active"])
    return JsonResponse({"ok": True, "user_id": user_id, "is_active": user.is_active})


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


class PriceConfigView(UserPassesTestMixin, View):
    """관리자 전용 토큰당 가격 설정 조회(GET)/등록·수정(POST) API.
    GET/POST 분기 + 권한 체크가 뚜렷해 CBV(UserPassesTestMixin)로 표현하기 적절한 케이스."""

    def test_func(self):
        return self.request.user.is_authenticated and self.request.user.is_staff

    def handle_no_permission(self):
        return JsonResponse({"error": "Unauthorized"}, status=403)

    def get(self, request):
        configs = PriceConfig.objects.all().values(
            "id", "model_name", "prompt_token_price", "completion_token_price"
        )
        return JsonResponse(list(configs), safe=False)

    def post(self, request):
        try:
            data = json.loads(request.body)
        except json.JSONDecodeError:
            return JsonResponse({"error": "Invalid JSON"}, status=400)

        model_name = data.get("model_name", "").strip()
        if not model_name:
            return JsonResponse({"error": "model_name is required"}, status=400)

        try:
            prompt_price = float(data.get("prompt_token_price", 0))
            completion_price = float(data.get("completion_token_price", 0))
        except (TypeError, ValueError):
            return JsonResponse({"error": "Prices must be numbers"}, status=400)

        if prompt_price < 0 or completion_price < 0:
            return JsonResponse({"error": "Prices cannot be negative"}, status=400)

        user_name = request.user.get_full_name() or request.user.username or "admin"
        PriceConfig.objects.update_or_create(
            model_name=model_name,
            defaults={
                "prompt_token_price": prompt_price,
                "completion_token_price": completion_price,
                "updated_by": user_name,
            }
        )
        return JsonResponse({"ok": True})


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

def _sse(data: dict) -> str:
    return f"data: {json.dumps(data, ensure_ascii=False)}\n\n"


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

    def event_stream():
        answer = ""
        try:
            init_logger(question)
            for event in supervisor_engine.stream_answer(question):
                kind = event[0]
                if kind == "done":
                    result = event[1]
                    answer = result.get("answer", "")
                    chat.mode = result.get("mode", "supervisor")
                    chat.category = result.get("category", "")
                    chat.sources = {"law": result.get("sources", []), "precedent": result.get("precedents", [])}
                else:
                    _, node_name, phase, label, log, elapsed = event
                    yield _sse({
                        "type": "progress",
                        "node": node_name,
                        "phase": phase,
                        "label": label,
                        "log": log,
                        "elapsed": round(elapsed, 2) if elapsed is not None else None,
                    })
        except Exception as e:
            logger.exception("advice_api 답변 생성 실패")
            answer = llm_error_message(e)
        finally:
            query_logger = get_logger()
            if query_logger:
                query_logger.finish(answer)
                print(
                    "[advice_api timing]",
                    {
                        "total": query_logger.total_elapsed(),
                        "nodes": query_logger.nodes,
                    },
                    flush=True,
                )
                query_logger.save()
            clear_logger()
            chat.answer = answer
            chat.save()

        yield _sse({"type": "done", "answer": answer, "message_id": chat.id, "mode": chat.mode})

    response = StreamingHttpResponse(event_stream(), content_type="text/event-stream; charset=utf-8")
    response["Cache-Control"] = "no-cache"
    response["X-Accel-Buffering"] = "no"
    return response


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


def _sanitize_conversation_history(raw) -> list | None:
    """요청으로 들어온 history를 [{"role": "user"/"assistant", "content": str}, ...] 형태로만 정제.
    형식이 어긋난 항목은 조용히 걸러내 ReAct 에이전트 쪽 코드가 신뢰할 수 있는 입력만 받게 한다."""
    if not isinstance(raw, list):
        return None
    cleaned = []
    for item in raw:
        if not isinstance(item, dict):
            continue
        role = item.get("role")
        content = item.get("content")
        if role in ("user", "assistant") and isinstance(content, str) and content.strip():
            cleaned.append({"role": role, "content": content})
    return cleaned or None


@require_POST
def calculate_api(request):
    payload = _json_payload(request)
    mode = payload.get("mode", "form")
    if mode == "chat":
        try:
            history = _sanitize_conversation_history(payload.get("history"))
            message, result = calculator.calculate_natural(payload.get("text", ""), history)
        except Exception as e:
            logger.exception("calculate_api 자연어 계산 실패")
            return JsonResponse({"message": llm_error_message(e), "result": None})
    else:
        result = calculator.calculate_form(
            payload.get("calc_type", "severance"),
            _float(payload.get("salary"), 0),
            _float(payload.get("months"), 14),
            _float(payload.get("hours"), 40),
        )
        message = f"{result.label}은 {calculator.format_won(result.amount)}입니다."
    return JsonResponse({"message": message, "result": result.to_dict() if result else None})


class HistoryDetailView(LoginRequiredMixin, View):
    """로그인한 사용자 본인의 상담 이력 상세 조회 API (IDOR 방지를 위해 user로 스코프 제한).
    인증 체크 + 단건 조회라는 전형적인 패턴이라 LoginRequiredMixin 기반 CBV로 표현."""

    def handle_no_permission(self):
        return JsonResponse({"error": "로그인이 필요합니다."}, status=401)

    def get(self, request, history_id):
        try:
            chat = ChatHistory.objects.get(pk=history_id, user=request.user)
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
    items, summary_text = news.get_news(query)
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
