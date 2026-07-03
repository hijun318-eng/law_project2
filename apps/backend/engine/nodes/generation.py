"""
LLM 답변 및 절차 안내 생성 노드 함수
"""
from pathlib import Path

from engine.services.answer_service import answer_service
from engine.services.procedure_service import procedure_service

from engine.nodes.graph_state import GraphState
from engine.utils.execution_logger import log_node


# ==========================================================
# NODE 3: LLM 답변
# ==========================================================
@log_node
def generate_answer_node(state: GraphState) -> dict:
    return answer_service.generate(
        law_analysis=state["law_analysis"],
        precedent_docs=state["precedent_context_docs"],
        question=state["question"],
        law_source=state.get("law_source", "unknown"),
    )


# ==========================================================
# NODE 4: 절차 안내
# ==========================================================
@log_node
def procedure_guide_node(state: GraphState) -> dict:
    used_precedents = state.get("used_precedents", [])

    # case_based_answer 단계(generate_answer_node)를 거치지 않은 경로
    # (예: procedure_guidance 전용 라우트)는 used_precedents가 비어 있다.
    # 이 경우 검색 단계(retrieve_precedent_node)에서 가장 관련성 높은
    # 판례를 fallback으로 사용한다.
    if not used_precedents:
        fallback_docs = state.get("precedent_docs_direct", [])
        used_precedents = [
            Path(doc.metadata.get("source_file", "")).stem
            for doc in fallback_docs[:1]
            if doc.metadata.get("source_file")
        ]

    try:
        return {
            "procedure_guide": procedure_service.generate(
                used_precedents=used_precedents,
            ),
        }
    except Exception:
        return {
            "procedure_guide": "skip",
        }
