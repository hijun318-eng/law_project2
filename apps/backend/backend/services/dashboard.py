from .mock_data import MOCK_USERS, MOCK_QUESTIONS, CATEGORY_TRENDS, CATEGORY_PIE, DAILY_DATA
from chat.models import ChatHistory
from django.db.models import Avg, Max, Count, Sum, Q
from django.db.models.functions import TruncDay, TruncWeek, TruncMonth
from monitoring.models import NodeExecutionLog, LLMUsageLog, PriceConfig
from . import prompts


def dashboard_context() -> dict:
    max_questions = max(item["questions"] for item in DAILY_DATA)
    max_abs_change = max(abs(item["change"]) for item in CATEGORY_TRENDS) or 1

    trends = []
    for item in CATEGORY_TRENDS:
        change = item["change"]
        direction = "up" if change > 0 else "down" if change < 0 else "flat"
        trends.append({
            "name": item["name"],
            "direction": direction,
            "change_display": f"+{change}%p" if change > 0 else (f"{change}%p" if change < 0 else "±0%p"),
            "bar_width": round(abs(change) / max_abs_change * 45, 1),
        })

    active_users = sum(1 for user in MOCK_USERS if user["status"] == "active")

    # 피드백 관리 화면과 동일한 카테고리 집계를 재사용
    feedback_groups = feedback_context()["category_groups"]
    low_feedback = [g for g in feedback_groups if g["needs_attention"]]

    return {
        "stats": [
            {"label": "오늘 질문 수", "value": "84", "change": "+12%", "tone": "blue"},
            {"label": "신규 가입자", "value": "27", "change": "+34%", "tone": "green"},
            {"label": "평균 만족도", "value": "87.2점", "change": "+2.1", "tone": "purple"},
            {"label": "전체 사용자", "value": "1,243", "change": "+8명", "tone": "amber"},
        ],
        "daily": [{**item, "question_height": round(item["questions"] / max_questions * 100), "user_height": round(item["users"] / max_questions * 100)} for item in DAILY_DATA],
        "categories": CATEGORY_PIE,
        "category_trends": trends,
        "low_feedback": low_feedback,
        "total_users": len(MOCK_USERS),
        "active_users": active_users,
        "suspended_users": len(MOCK_USERS) - active_users,
    }


def users_context() -> dict:
    active_count = sum(1 for user in MOCK_USERS if user["status"] == "active")
    return {"users": MOCK_USERS, "active_count": active_count, "suspended_count": len(MOCK_USERS) - active_count}

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
 
 
def _short_date(raw_date):
    """'2026-06-30 14:23' -> '06-30'. 날짜가 없거나 형식이 다르면 None을 반환해 차트 집계에서 제외."""
    if not raw_date:
        return None
    try:
        return datetime.strptime(raw_date[:10], "%Y-%m-%d").strftime("%m-%d")
    except ValueError:
        return None
 
 
def feedback_context() -> dict:
    by_category = defaultdict(lambda: {
        "likes": 0, "dislikes": 0, "items": [],
        "daily": defaultdict(lambda: {"likes": 0, "dislikes": 0}),
    })
 
    total_likes = 0
    total_dislikes = 0
 
    for raw in MOCK_QUESTIONS:
        category = raw.get("category") or "미분류"  # 카테고리 누락 -> "미분류"
        likes = _safe_int(raw.get("likes"))
        dislikes = _safe_int(raw.get("dislikes"))
 
        total_likes += likes
        total_dislikes += dislikes
 
        bucket = by_category[category]
        bucket["likes"] += likes
        bucket["dislikes"] += dislikes
        bucket["items"].append(raw)
 
        date_key = _short_date(raw.get("date"))
        if date_key:  # 날짜 없으면 일별 차트 집계에서만 제외, 요약 통계에는 포함
            bucket["daily"][date_key]["likes"] += likes
            bucket["daily"][date_key]["dislikes"] += dislikes
 
    score_ranking = []
 
    for category, bucket in by_category.items():
        avg_score = _score(bucket["likes"], bucket["dislikes"])
        needs_attention = avg_score < LOW_SCORE_THRESHOLD
 
        low_count = sum(
            1 for item in bucket["items"]
            if _score(_safe_int(item.get("likes")), _safe_int(item.get("dislikes"))) < LOW_SCORE_THRESHOLD
        )
 
        daily_items = sorted(bucket["daily"].items())  # 날짜 오름차순
        max_count = max(
            [v["likes"] for _, v in daily_items] + [v["dislikes"] for _, v in daily_items] + [1]
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
            "likes": bucket["likes"],
            "dislikes": bucket["dislikes"],
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
        usages = LLMUsageLog.objects.filter(model=model_name).values('call_type').annotate(
            total_prompt=Sum('prompt_tokens'),
            total_completion=Sum('completion_tokens'),
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
            "question": row['session_id'],
            "user": "",
            "duration_sec": total_sec,
            "bottleneck": bottleneck,
            "date": "",
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

    # LLM 사용량 통계
    llm_agg = LLMUsageLog.objects.aggregate(
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
        "total_cost": f"{total_cost:.2f}",
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
