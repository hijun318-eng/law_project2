MOCK_USERS = [
    {"id": 1, "name": "김민준", "email": "minjun@example.com", "join_date": "2024-01-15", "last_login": "2026-06-30", "status": "active", "questions": 12},
    {"id": 2, "name": "이서연", "email": "seoyeon@example.com", "join_date": "2024-02-20", "last_login": "2026-06-28", "status": "active", "questions": 8},
    {"id": 3, "name": "박지호", "email": "jiho@example.com", "join_date": "2024-03-10", "last_login": "2026-05-15", "status": "suspended", "questions": 3},
    {"id": 4, "name": "최유진", "email": "yujin@example.com", "join_date": "2024-04-05", "last_login": "2026-06-29", "status": "active", "questions": 24},
    {"id": 5, "name": "정다은", "email": "daeun@example.com", "join_date": "2024-05-12", "last_login": "2026-06-27", "status": "active", "questions": 6},
    {"id": 6, "name": "한승호", "email": "seungho@example.com", "join_date": "2024-06-01", "last_login": "2026-04-10", "status": "suspended", "questions": 1},
    {"id": 7, "name": "오미래", "email": "mirae@example.com", "join_date": "2024-06-15", "last_login": "2026-06-30", "status": "active", "questions": 15},
    {"id": 8, "name": "임태양", "email": "taeyang@example.com", "join_date": "2024-07-20", "last_login": "2026-06-25", "status": "active", "questions": 9},
]

FAQ_DATA = [
    {"name": "임금체불", "count": 342},
    {"name": "부당해고", "count": 287},
    {"name": "퇴직금", "count": 198},
    {"name": "연차휴가", "count": 156},
    {"name": "최저임금", "count": 134},
    {"name": "직장내괴롭힘", "count": 98},
    {"name": "산업재해", "count": 76},
]

CATEGORY_PIE = [
    {"name": "임금체불", "value": 28},
    {"name": "부당해고", "value": 23},
    {"name": "퇴직금", "value": 16},
    {"name": "연차휴가", "value": 13},
    {"name": "최저임금", "value": 11},
    {"name": "기타", "value": 9},
]

CATEGORY_TRENDS = [
    {"name": "임금체불", "change": 8},
    {"name": "부당해고", "change": -3},
    {"name": "연차휴가", "change": 0},
    {"name": "산업재해", "change": 5},
    {"name": "근로계약", "change": -2},
]

DAILY_DATA = [
    {"date": "6/25", "questions": 47, "users": 12},
    {"date": "6/26", "questions": 52, "users": 15},
    {"date": "6/27", "questions": 61, "users": 18},
    {"date": "6/28", "questions": 58, "users": 14},
    {"date": "6/29", "questions": 73, "users": 21},
    {"date": "6/30", "questions": 84, "users": 27},
    {"date": "7/1", "questions": 38, "users": 9},
]
from backend.services.mock_data import FEEDBACK_DATA

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


def feedback_context() -> dict:
    total_likes = sum(1 for item in FEEDBACK_DATA if item.get("liked", False))
    total_dislikes = sum(1 for item in FEEDBACK_DATA if not item.get("liked", False))
    avg_score = round(total_likes / len(FEEDBACK_DATA) * 100, 1) if FEEDBACK_DATA else 0.0

    grouped: dict[str, list] = {}
    for item in FEEDBACK_DATA:
        grouped.setdefault(item.get("category", "미분류"), []).append(item)

    category_groups = []
    for category, items in grouped.items():
        likes = sum(1 for i in items if i.get("liked", False))
        dislikes = len(items) - likes
        score = round(likes / len(items) * 100) if items else 0

        by_date: dict[str, dict] = defaultdict(lambda: {"likes": 0, "dislikes": 0})
        for i in items:
            date_key = i["created_at"].split(" ")[0][5:]
            if i.get("liked", False):
                by_date[date_key]["likes"] += 1
            else:
                by_date[date_key]["dislikes"] += 1

        sorted_dates = sorted(by_date.keys())
        day_totals = {d: by_date[d]["likes"] + by_date[d]["dislikes"] for d in sorted_dates}
        max_day_total = max(day_totals.values(), default=1) or 1

        daily_trend = []
        for date in sorted_dates:
            likes_n = by_date[date]["likes"]
            dislikes_n = by_date[date]["dislikes"]
            daily_trend.append({
                "date": date,
                "likes": likes_n,
                "dislikes": dislikes_n,
                "like_height": round(likes_n / max_day_total * 100),
                "dislike_height": round(dislikes_n / max_day_total * 100),
            })

        category_groups.append({
            "category": category,
            "likes": likes,
            "dislikes": dislikes,
            "low_count": dislikes,
            "avg_score": score,
            "needs_attention": score < 60,
            "daily_trend": daily_trend,
        })

    category_groups.sort(key=lambda g: g["avg_score"])
    for rank, group in enumerate(category_groups, start=1):
        group["rank"] = rank

    return {
        "category_groups": category_groups,
        "score_ranking": category_groups,
        "low_category_count": sum(1 for g in category_groups if g["needs_attention"]),
        "total_likes": f"{total_likes:,}",
        "total_dislikes": f"{total_dislikes:,}",
        "avg_score": f"{avg_score:.1f}%",
    }

def prompts_context() -> dict:
    templates = [
        {
            "id": "answer_prompt",
            "name": "answer_prompt",
            "description": "AI 상담 답변 생성 프롬프트",
            "version": 3,
            "content": "당신은 노동법 전문 AI입니다...\n질문: {question}\n컨텍스트: {context}",
            "placeholders": ["{question}", "{context}"],
            "updated_at": "2026-06-28 14:20",
            "updated_by": "관리자",
            "history": [
                {"version": 3, "updated_at": "2026-06-28 14:20", "updated_by": "관리자", "summary": "컨텍스트 강조 문구 추가"},
                {"version": 2, "updated_at": "2026-06-20 09:10", "updated_by": "관리자", "summary": "초기 버전 개선"},
            ],
        },
    ]
    return {"prompt_templates": templates}


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


def performance_context() -> dict:
    nodes = [
        {"id": "retrieve", "label": "retrieve_context", "avg_ms": 820, "max_ms": 2100, "calls": 4210, "load_percent": 60},
        {"id": "rerank", "label": "cross_encoder_rerank", "avg_ms": 410, "max_ms": 1500, "calls": 4210, "load_percent": 30},
        {"id": "generate_answer", "label": "generate_answer", "avg_ms": 3200, "max_ms": 9800, "calls": 4210, "load_percent": 90},
        {"id": "postprocess", "label": "postprocess", "avg_ms": 120, "max_ms": 400, "calls": 4210, "load_percent": 10},
    ]
    llm_usage = [
        {"date": "06-26", "calls": 210, "calls_height": 70, "emb_calls_height": 40},
        {"date": "06-27", "calls": 180, "calls_height": 60, "emb_calls_height": 35},
    ]
    return {
        "langgraph_nodes": nodes,
        "llm_usage": llm_usage,
        "total_calls": 413,
        "total_tokens": "1,100K",
        "total_cost": "34.64",
        "slow_queries": [
            {"question": "회사가 임금을 3개월째 안 줘요, 어떻게 해야 하나요?", "user": "kim***@example.com", "duration_sec": 24.1, "bottleneck": "generate_answer", "date": "2026-06-30 10:12"},
        ],
    }
    
    
## 프롬프트 더미
_PROMPT_TEMPLATES = {
    "answer_prompt": {
        "id": "answer_prompt",
        "name": "answer_prompt",
        "description": "AI 상담 답변 생성 프롬프트",
        "version": 3,
        "content": "당신은 노동법 전문 AI입니다. 아래 컨텍스트를 반드시 참고하여 정확하게 답변하세요.\n질문: {question}\n컨텍스트: {context}",
        "placeholders": ["{question}", "{context}"],
        "updated_at": "2026-06-28 14:20",
        "updated_by": "관리자",
        "history": [
            {
                "version": 3,
                "updated_at": "2026-06-28 14:20",
                "updated_by": "관리자",
                "summary": "컨텍스트 강조 문구 추가",
                "content": "당신은 노동법 전문 AI입니다. 아래 컨텍스트를 반드시 참고하여 정확하게 답변하세요.\n질문: {question}\n컨텍스트: {context}",
            },
            {
                "version": 2,
                "updated_at": "2026-06-20 09:10",
                "updated_by": "관리자",
                "summary": "초기 버전 개선",
                "content": "당신은 노동법 전문 AI입니다.\n질문: {question}\n컨텍스트: {context}",
            },
            {
                "version": 1,
                "updated_at": "2026-06-10 11:00",
                "updated_by": "관리자",
                "summary": "최초 등록",
                "content": "노동법 관련 질문에 답변하세요.\n질문: {question}",
            },
        ],
    },
}

def prompts_context() -> dict:
    return {"prompt_templates": list(_PROMPT_TEMPLATES.values())}


def get_prompt_template(template_id: str) -> dict:
    return _PROMPT_TEMPLATES.get(template_id, {})


def validate_prompt_content(template_id: str, content: str) -> list[str]:
    template = _PROMPT_TEMPLATES.get(template_id, {})
    return [f"필수 플레이스홀더 {p} 가 누락되었습니다." for p in template.get("placeholders", []) if p not in content]


def save_prompt_template(template_id: str, content: str) -> None:
    template = _PROMPT_TEMPLATES.get(template_id)
    if not template:
        return
    new_version = template["version"] + 1
    template["history"].insert(0, {
        "version": new_version,
        "updated_at": "2026-07-02 17:30",
        "updated_by": "관리자",
        "summary": "내용 업데이트",
        "content": content,
    })
    template["content"] = content
    template["version"] = new_version
    template["updated_at"] = "2026-07-02 17:30"

def rollback_prompt_template(template_id: str, version) -> None:
    template = _PROMPT_TEMPLATES.get(template_id)
    if not template:
        return
    match = next((v for v in template["history"] if str(v["version"]) == str(version)), None)
    if not match:
        return
    new_version = template["version"] + 1
    template["history"].insert(0, {
        "version": new_version,
        "updated_at": "2026-07-03 15:00",  # 실제로는 timezone.now() 등으로 대체
        "updated_by": "관리자",
        "summary": f"v{version}으로 롤백",
        "content": match["content"],
    })
    template["content"] = match["content"]
    template["version"] = new_version
    template["updated_at"] = "2026-07-03 15:00"