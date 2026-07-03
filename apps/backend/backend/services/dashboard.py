from .mock_data import CATEGORY_PIE, DAILY_DATA, FAQ_DATA, FEEDBACK_DATA, MOCK_USERS


def dashboard_context() -> dict:
    max_questions = max(item["questions"] for item in DAILY_DATA)
    max_faq = max(item["count"] for item in FAQ_DATA)
    return {
        "stats": [
            {"label": "오늘 질문 수", "value": "84", "change": "+12%", "tone": "blue"},
            {"label": "신규 가입자", "value": "27", "change": "+34%", "tone": "green"},
            {"label": "평균 만족도", "value": "87.2점", "change": "+2.1", "tone": "purple"},
            {"label": "전체 사용자", "value": "1,243", "change": "+8명", "tone": "amber"},
        ],
        "daily": [{**item, "question_height": round(item["questions"] / max_questions * 100), "user_height": round(item["users"] / max_questions * 100)} for item in DAILY_DATA],
        "categories": CATEGORY_PIE,
        "faq": [{**item, "percent": round(item["count"] / max_faq * 100)} for item in FAQ_DATA],
        "low_feedback": [item for item in FEEDBACK_DATA if item["score"] < 60],
        "notices": [
            {"id": 1, "title": "2026년 최저임금 고시 반영 완료", "date": "2026-06-28", "type": "법령"},
            {"id": 2, "title": "포괄임금제 행정지침 업데이트", "date": "2026-06-20", "type": "지침"},
        ],
    }


def users_context() -> dict:
    active_count = sum(1 for user in MOCK_USERS if user["status"] == "active")
    return {"users": MOCK_USERS, "active_count": active_count, "suspended_count": len(MOCK_USERS) - active_count}


def feedback_context() -> dict:
    total_likes = sum(item["likes"] for item in FEEDBACK_DATA)
    total_dislikes = sum(item["dislikes"] for item in FEEDBACK_DATA)
    avg_score = sum(item["score"] for item in FEEDBACK_DATA) / len(FEEDBACK_DATA)
    return {
        "feedbacks": FEEDBACK_DATA,
        "low_count": sum(1 for item in FEEDBACK_DATA if item["score"] < 60),
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
        "content": "당신은 노동법 전문 AI입니다...\n질문: {question}\n컨텍스트: {context}",
        "placeholders": ["{question}", "{context}"],
        "updated_at": "2026-06-28 14:20",
        "updated_by": "관리자",
        "history": [
            {"version": 3, "updated_at": "2026-06-28 14:20", "updated_by": "관리자", "summary": "컨텍스트 강조 문구 추가", "content": "..."},
            {"version": 2, "updated_at": "2026-06-20 09:10", "updated_by": "관리자", "summary": "초기 버전 개선", "content": "..."},
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


def test_prompt_template(template_id: str, content: str, query: str) -> str:
    return f'"{query}"에 대한 테스트 응답입니다.\n\n수정된 프롬프트 기반 예시 답변이며, 실제 운영 환경에서는 LangGraph 파이프라인을 통해 처리됩니다.'


def rollback_prompt_template(template_id: str, version) -> None:
    template = _PROMPT_TEMPLATES.get(template_id)
    if not template:
        return
    match = next((v for v in template["history"] if str(v["version"]) == str(version)), None)
    if match:
        template["content"] = match["content"]