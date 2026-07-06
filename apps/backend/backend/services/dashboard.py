from datetime import timedelta

from django.contrib.auth.models import User
from django.utils import timezone

from chat.models import ChatHistory
from django.db.models import Avg, Max, Count, Sum, Q
from django.db.models.functions import TruncDay, TruncWeek, TruncMonth
from monitoring.models import NodeExecutionLog, LLMUsageLog, PriceConfig
from . import prompts


def _pct_change_display(now_value: int, prev_value: int) -> str:
    """이전 대비 증감률을 '+12%' 형태 문자열로 반환. 이전 값이 0이면 신규 발생 여부로 판단."""
    if prev_value == 0:
        return "+100%" if now_value > 0 else "±0%"
    pct = round((now_value - prev_value) / prev_value * 100)
    return f"+{pct}%" if pct > 0 else (f"{pct}%" if pct < 0 else "±0%")


def _daily_activity(days: int = 7) -> list[dict]:
    """최근 N일간 일별 질문 수 / 활동 사용자 수(중복 제거)를 집계."""
    today = timezone.localdate()
    start = today - timedelta(days=days - 1)

    rows = (
        ChatHistory.objects
        .filter(created_at__date__gte=start)
        .annotate(day=TruncDay("created_at"))
        .values("day")
        .annotate(questions=Count("id"), users=Count("user", distinct=True))
    )
    by_date = {row["day"].date(): row for row in rows}

    return [
        {
            "date": f"{(start + timedelta(days=i)).month}/{(start + timedelta(days=i)).day}",
            "questions": by_date.get(start + timedelta(days=i), {}).get("questions", 0),
            "users": by_date.get(start + timedelta(days=i), {}).get("users", 0),
        }
        for i in range(days)
    ]


def _category_distribution() -> list[dict]:
    """category 값이 채워진 질문만 대상으로 비중(%)을 집계 (feedback_context와 동일 기준)."""
    rows = (
        ChatHistory.objects
        .exclude(category__exact="")
        .values("category")
        .annotate(count=Count("id"))
        .order_by("-count")
    )
    total = sum(row["count"] for row in rows)
    if not total:
        return []
    return [{"name": row["category"], "value": round(row["count"] / total * 100)} for row in rows]


def _category_share(start, end) -> dict[str, float]:
    rows = (
        ChatHistory.objects
        .exclude(category__exact="")
        .filter(created_at__date__gte=start, created_at__date__lte=end)
        .values("category")
        .annotate(count=Count("id"))
    )
    total = sum(row["count"] for row in rows)
    if not total:
        return {}
    return {row["category"]: row["count"] / total * 100 for row in rows}


def _category_trends(days: int = 7, top_n: int = 5) -> list[dict]:
    """최근 N일 vs 그 이전 N일의 카테고리별 비중(%p) 변화."""
    today = timezone.localdate()
    now_start = today - timedelta(days=days - 1)
    prev_end = now_start - timedelta(days=1)
    prev_start = prev_end - timedelta(days=days - 1)

    share_now = _category_share(now_start, today)
    share_prev = _category_share(prev_start, prev_end)

    names = sorted(
        set(share_now) | set(share_prev),
        key=lambda name: share_now.get(name, 0),
        reverse=True,
    )[:top_n]
    if not names:
        return []

    changes = [round(share_now.get(name, 0) - share_prev.get(name, 0), 1) for name in names]
    max_abs_change = max((abs(c) for c in changes), default=0) or 1

    trends = []
    for name, change in zip(names, changes):
        direction = "up" if change > 0 else "down" if change < 0 else "flat"
        trends.append({
            "name": name,
            "direction": direction,
            "change_display": f"+{change}%p" if change > 0 else (f"{change}%p" if change < 0 else "±0%p"),
            "bar_width": round(abs(change) / max_abs_change * 45, 1),
        })
    return trends


def dashboard_context() -> dict:
    today = timezone.localdate()
    yesterday = today - timedelta(days=1)

    daily_data = _daily_activity()
    max_questions = max((item["questions"] for item in daily_data), default=0) or 1

    active_users = User.objects.filter(is_active=True).count()
    total_users = User.objects.count()

    # 피드백 관리 화면과 동일한 카테고리 집계를 재사용
    feedback_groups = feedback_context()["category_groups"]
    low_feedback = [g for g in feedback_groups if g["needs_attention"]]

    today_questions = ChatHistory.objects.filter(created_at__date=today).count()
    yesterday_questions = ChatHistory.objects.filter(created_at__date=yesterday).count()

    today_new_users = User.objects.filter(date_joined__date=today).count()
    yesterday_new_users = User.objects.filter(date_joined__date=yesterday).count()

    overall_likes = ChatHistory.objects.filter(feedback=True).count()
    overall_dislikes = ChatHistory.objects.filter(feedback=False).count()
    overall_feedback_count = overall_likes + overall_dislikes
    overall_score = _score(overall_likes, overall_dislikes) if overall_feedback_count else None

    today_score, today_fb_count = _avg_score_for_day(today)
    yesterday_score, yesterday_fb_count = _avg_score_for_day(yesterday)
    if today_fb_count == 0 or yesterday_fb_count == 0:
        score_change = "-"
    else:
        diff = round(today_score - yesterday_score, 1)
        score_change = f"+{diff}" if diff > 0 else (f"{diff}" if diff < 0 else "±0")

    return {
        "stats": [
            {"label": "오늘 질문 수", "value": str(today_questions), "change": _pct_change_display(today_questions, yesterday_questions), "tone": "blue"},
            {"label": "신규 가입자", "value": str(today_new_users), "change": _pct_change_display(today_new_users, yesterday_new_users), "tone": "green"},
            {"label": "평균 만족도", "value": f"{overall_score}점" if overall_score is not None else "-", "change": score_change, "tone": "purple"},
            {"label": "전체 사용자", "value": f"{total_users:,}", "change": f"+{today_new_users}명", "tone": "amber"},
        ],
        "daily": [{**item, "question_height": round(item["questions"] / max_questions * 100), "user_height": round(item["users"] / max_questions * 100)} for item in daily_data],
        "categories": _category_distribution(),
        "category_trends": _category_trends(),
        "low_feedback": low_feedback,
        "total_users": total_users,
        "active_users": active_users,
        "suspended_users": total_users - active_users,
    }


def users_context() -> dict:
    users = User.objects.filter(is_staff=False).annotate(questions=Count('chathistory'))
    active_count = users.filter(is_active=True).count()
    total_count = users.count()
    return {
        "users": users,
        "active_count": active_count,
        "suspended_count": total_count - active_count,
    }

from collections import defaultdict
from datetime import datetime

LOW_SCORE_THRESHOLD = 60  # 평균 만족도 60% 미만이면 "개선 필요"

def _safe_int(value, default=0):
    """좋아요/싫어요 값이 없거나 숫자가 아니면 0으로 처리 (요구사항: 값 누락 시 False 취급과 동일한 효과)."""
    try:
        return int(value)
    except (TypeError, ValueError):
        return default
 
 
def _score(likes, dislikes):
    total = likes + dislikes
    if total == 0:
        return 0
    return round(likes / total * 100)


def _avg_score_for_day(day) -> tuple[int, int]:
    """특정 날짜의 (평균 만족도 점수, 집계 대상 피드백 수)를 반환."""
    qs = ChatHistory.objects.filter(created_at__date=day, feedback__isnull=False)
    likes = qs.filter(feedback=True).count()
    dislikes = qs.filter(feedback=False).count()
    return _score(likes, dislikes), likes + dislikes


def _short_date(raw_date):
    """'2026-06-30 14:23' -> '06-30'. 날짜가 없거나 형식이 다르면 None을 반환해 차트 집계에서 제외."""
    if not raw_date:
        return None
    try:
        return datetime.strptime(raw_date[:10], "%Y-%m-%d").strftime("%m-%d")
    except ValueError:
        return None
 
 
def feedback_context() -> dict:
    # feedback이 있는 모든 레코드를 집계. category가 빈 레코드도 상단 총계(총 좋아요/싫어요/평균 만족도)에는
    # 포함하되, 카테고리별 카드 목록(score_ranking/category_groups)에는 노출하지 않는다.
    base_qs = ChatHistory.objects.filter(feedback__isnull=False)

    # 카테고리별 likes/dislikes 집계
    cat_agg = (
        base_qs
        .values("category")
        .annotate(
            likes=Count("pk", filter=Q(feedback=True)),
            dislikes=Count("pk", filter=Q(feedback=False)),
        )
    )

    # 일별 트렌드 (TruncDay로 날짜 단위 집계)
    daily_qs = (
        base_qs
        .annotate(day=TruncDay("created_at"))
        .values("category", "day")
        .annotate(
            likes=Count("pk", filter=Q(feedback=True)),
            dislikes=Count("pk", filter=Q(feedback=False)),
        )
        .order_by("day")
    )

    # daily_qs를 카테고리별·일별로 그룹핑
    daily_by_cat: dict[str, dict[str, dict[str, int]]] = defaultdict(
        lambda: defaultdict(lambda: {"likes": 0, "dislikes": 0})
    )
    for row in daily_qs:
        cat = row["category"]
        day = row["day"].strftime("%m-%d") if row["day"] else None
        if day:
            daily_by_cat[cat][day]["likes"] += row["likes"]
            daily_by_cat[cat][day]["dislikes"] += row["dislikes"]

    total_likes = 0
    total_dislikes = 0
    score_ranking = []

    for cat_row in cat_agg:
        raw_category = cat_row["category"]
        likes = cat_row["likes"] or 0
        dislikes = cat_row["dislikes"] or 0

        total_likes += likes
        total_dislikes += dislikes

        if not raw_category:
            # category 없는 항목(예: allowance_calculator)은 총계에는 반영하되 카드로는 노출하지 않음
            continue

        category = raw_category
        avg_score = _score(likes, dislikes)
        needs_attention = avg_score < LOW_SCORE_THRESHOLD

        # low_count: 해당 카테고리 내 feedback=False(싫어요) 레코드 수 = dislikes
        low_count = dislikes

        # 일별 트렌드
        daily_items = sorted(daily_by_cat.get(raw_category, {}).items())
        max_count = max(
            [v["likes"] for _, v in daily_items]
            + [v["dislikes"] for _, v in daily_items]
            + [1]
        )
        daily_trend = [
            {
                "date": date,
                "likes": v["likes"],
                "dislikes": v["dislikes"],
                "like_height": round(v["likes"] / max_count * 100),
                "dislike_height": round(v["dislikes"] / max_count * 100),
            }
            for date, v in daily_items
        ]

        score_ranking.append({
            "category": category,
            "avg_score": avg_score,
            "likes": likes,
            "dislikes": dislikes,
            "needs_attention": needs_attention,
            "low_count": low_count,
            "daily_trend": daily_trend,
        })

    # 만족도 낮은 순 정렬(개선 우선순위) + 순위 부여
    score_ranking.sort(key=lambda x: x["avg_score"])
    for i, entry in enumerate(score_ranking, start=1):
        entry["rank"] = i

    # 카테고리 아코디언 목록도 동일 순서(낮은 만족도 우선) 사용
    category_groups = score_ranking

    low_category_count = sum(1 for e in category_groups if e["needs_attention"])
    # 개선 대상 없음 -> "개선 필요 (0)"으로 정상 표시 (low_category_count = 0)

    return {
        "total_likes": total_likes,
        "total_dislikes": total_dislikes,
        "avg_score": _score(total_likes, total_dislikes),  # 피드백 데이터 없으면 0
        "score_ranking": score_ranking,
        "category_groups": category_groups,
        "low_category_count": low_category_count,
    }

def vectordb_context() -> dict:
    return {
        "vector_dbs": [
            {"id": "law", "name": "법령 DB", "status": "healthy", "doc_count": 4210, "size": "812MB", "last_build": "2026-06-30 03:00"},
            {"id": "precedent", "name": "판례 DB", "status": "outdated", "doc_count": 18320, "size": "3.1GB", "last_build": "2026-06-15 03:00"},
            {"id": "faq", "name": "질의회시 DB", "status": "healthy", "doc_count": 6120, "size": "1.4GB", "last_build": "2026-06-30 03:00"},
        ],
        "upload_history": [
            {"filename": "labor_standards_2026.pdf", "type": "법령", "size": "2.1MB", "uploaded_at": "2026-06-30 03:00", "docs": 412},
        ],
        "failed_embeddings": [
            {"id": 1, "filename": "precedent_2026_0512.json", "type": "판례", "reason": "토큰 길이 초과", "failed_at": "2026-06-29 11:40"},
        ],
    }


# ──────────────────────────────────────────────
# performance_context 헬퍼 함수들
# ──────────────────────────────────────────────


def _calculate_total_cost(price_configs: dict) -> float:
    """PriceConfig 딕셔너리를 받아 LLMUsageLog의 실제 사용량으로 비용 계산."""
    total = 0.0
    for model_name, price in price_configs.items():
        usages = (
            LLMUsageLog.objects.filter(model=model_name)
            .exclude(node_name='test')
            .values('call_type')
            .annotate(
                total_prompt=Sum('prompt_tokens'),
                total_completion=Sum('completion_tokens'),
            )
        )
        for u in usages:
            prompt_tokens = u['total_prompt'] or 0
            completion_tokens = u['total_completion'] or 0
            total += prompt_tokens * price.prompt_token_price / 1_000_000
            total += completion_tokens * price.completion_token_price / 1_000_000
    return total


def _get_period_usage(period: str = 'day') -> list:
    """LLMUsageLog를 period(day/week/month) 단위로 집계해 차트용 리스트 반환."""
    trunc_map = {'day': TruncDay, 'week': TruncWeek, 'month': TruncMonth}
    trunc_fn = trunc_map.get(period, TruncDay)
    qs = (
        LLMUsageLog.objects
        .exclude(node_name='test')
        .annotate(period_date=trunc_fn('created_at'))
        .values('period_date')
        .annotate(
            calls=Count('id'),
            total_tokens=Sum('total_tokens'),
        )
        .order_by('period_date')
    )
    max_calls = max((row['calls'] for row in qs), default=1)
    result = []
    for row in qs:
        date_str = row['period_date'].strftime('%m-%d') if row['period_date'] else ''
        result.append({
            "date": date_str,
            "calls": row['calls'],
            "calls_height": round(row['calls'] / max_calls * 100),
            "emb_calls_height": 0,
        })
    return result


def _get_slow_queries() -> list:
    """elapsed_ms 총합이 10초를 초과하는 세션을 최대 5건 반환."""
    slow_sessions = (
        NodeExecutionLog.objects
        .values('session_id')
        .annotate(total_ms=Sum('elapsed_ms'))
        .filter(total_ms__gte=10.0)
        .order_by('-total_ms')[:5]
    )
    # 막대 너비용 최댓값
    all_durations = [row['total_ms'] for row in slow_sessions]
    max_duration = max(all_durations) if all_durations else 1
    result = []
    for row in slow_sessions:
        total_sec = round(row['total_ms'], 1)
        # bottleneck: 해당 세션에서 가장 오래 걸린 노드
        bottleneck_row = (
            NodeExecutionLog.objects
            .filter(session_id=row['session_id'])
            .order_by('-elapsed_ms')
            .first()
        )
        bottleneck = bottleneck_row.node_name if bottleneck_row else 'unknown'
        result.append({
            "bottleneck_label": bottleneck.replace('_', ' '),
            "load_percent": round(row['total_ms'] / max_duration * 100),
            "duration_sec": total_sec,
        })
    return result


def performance_context() -> dict:
    # LangGraph 노드별 통계
    nodes_agg = NodeExecutionLog.objects.values('node_name').annotate(
        avg_ms=Avg('elapsed_ms'),
        max_ms=Max('elapsed_ms'),
        calls=Count('id'),
    )
    total_calls_all = sum(n['calls'] for n in nodes_agg) or 1
    langgraph_nodes = [
        {
            "id": n['node_name'],
            "label": n['node_name'].replace('_', ' '),
            "avg_ms": round(n['avg_ms'], 1) if n['avg_ms'] else 0,
            "max_ms": round(n['max_ms'], 1) if n['max_ms'] else 0,
            "calls": n['calls'],
            "load_percent": round(n['calls'] / total_calls_all * 100),
        }
        for n in nodes_agg
    ]

    # LLM 사용량 통계 (test 노드 제외)
    llm_agg = LLMUsageLog.objects.exclude(node_name='test').aggregate(
        total_calls=Count('id'),
        total_tokens=Sum('total_tokens'),
    )
    total_calls = llm_agg['total_calls'] or 0
    total_tokens = llm_agg['total_tokens'] or 0

    # 비용 계산 (PriceConfig 기반)
    price_configs = {p.model_name: p for p in PriceConfig.objects.all()}
    total_cost = _calculate_total_cost(price_configs)

    # 느린 쿼리
    slow_queries = _get_slow_queries()

    return {
        "langgraph_nodes": langgraph_nodes,
        "llm_usage": [],
        "total_calls": total_calls,
        "total_tokens": f"{total_tokens:,}",
        "total_cost": f"{total_cost:.6f}",
        "slow_queries": slow_queries,
    }



def prompts_context() -> dict:
    return {"prompt_templates": prompts.list_prompt_templates()}


def get_prompt_template(template_id: str) -> dict:
    return prompts.get_prompt_template(template_id)


def validate_prompt_content(template_id: str, content: str) -> list[str]:
    return prompts.validate_prompt_content(template_id, content)


def save_prompt_template(template_id: str, content: str, updated_by: str = "관리자") -> None:
    prompts.save_prompt_template(template_id, content, updated_by=updated_by)


def rollback_prompt_template(template_id: str, version, updated_by: str = "관리자") -> None:
    prompts.rollback_prompt_template(template_id, version, updated_by=updated_by)
