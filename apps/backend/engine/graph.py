"""
LangGraph StateGraph 빌드 + compile

7개 노드를 순차적으로 연결한 그래프를 생성합니다.
graph 객체를 외부에서 import하여 사용합니다.
"""
from langgraph.graph import StateGraph, END

from engine.nodes import (
    GraphState,
    retrieve_precedent_node,
    retrieve_law_node,
    generate_answer_node,
    procedure_guide_node,
)


def _build_base_graph() -> StateGraph:
    builder = StateGraph(GraphState)

    builder.add_node("retrieve_precedent", retrieve_precedent_node)
    builder.add_node("retrieve_law", retrieve_law_node)
    builder.add_node("generate_answer", generate_answer_node)
    builder.add_node("procedure_guide", procedure_guide_node)

    # 엣지 연결
    builder.set_entry_point("retrieve_precedent")
    builder.add_edge("retrieve_precedent",        "retrieve_law")
    return builder


# 기존 호환: 통합 그래프 (generate_answer -> procedure_guide)
_builder = _build_base_graph()
_builder.add_edge("retrieve_law", "generate_answer")
_builder.add_edge("generate_answer", "procedure_guide")
_builder.add_edge("procedure_guide", END)
graph = _builder.compile()


# answer-only 그래프: retrieve_law -> generate_answer -> END
_builder_answer = _build_base_graph()
_builder_answer.add_edge("retrieve_law", "generate_answer")
_builder_answer.add_edge("generate_answer", END)
graph_answer = _builder_answer.compile()


# procedure-only 그래프: retrieve_law -> procedure_guide -> END
_builder_procedure = _build_base_graph()
_builder_procedure.add_edge("retrieve_law", "procedure_guide")
_builder_procedure.add_edge("procedure_guide", END)
graph_procedure = _builder_procedure.compile()
