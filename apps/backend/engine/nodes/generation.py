from pathlib import Path

from engine.services.answer_service import answer_service
from engine.services.procedure_service import procedure_service

from engine.nodes.graph_state import GraphState
from engine.utils.execution_logger import log_node


@log_node
def generate_answer_node(state: GraphState) -> dict:
    return answer_service.generate(
        law_analysis=state["law_analysis"],
        precedent_docs=state["precedent_context_docs"],
        question=state["question"],
        law_source=state.get("law_source", "unknown"),
    )


@log_node
def procedure_guide_node(state: GraphState) -> dict:
    used_precedents = state.get("used_precedents", [])
    fallback_docs = state.get("precedent_docs_direct", [])
    fallback_category = ""

    for doc in fallback_docs:
        fallback_category = doc.metadata.get("category", "")
        if fallback_category:
            break

    if not used_precedents:
        used_precedents = [
            Path(doc.metadata.get("source_file", "")).stem
            for doc in fallback_docs[:1]
            if doc.metadata.get("source_file")
        ]

    try:
        if fallback_category:
            return {
                "procedure_guide": procedure_service.generate_for_category(
                    fallback_category,
                ),
            }

        return {
            "procedure_guide": procedure_service.generate(
                used_precedents=used_precedents,
            ),
        }
    except Exception as exc:
        print(f"[procedure_guide_node] failed: {exc}", flush=True)
        return {
            "procedure_guide": "skip",
        }
