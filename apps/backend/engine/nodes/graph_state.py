"""
LangGraph State 정의
"""
from typing import TypedDict


class GraphState(TypedDict):
    question: str
    precedent_docs_direct: list
    ref_articles_from_precedent: list[str]
    law_docs: list
    law_analysis: list
    law_source: str
    law_context: str
    law_confidence: float
    precedent_docs: list
    precedent_analysis: str
    precedent_context_docs: list
    final_answer: str
    used_precedents: list[str]
    procedure_guide: str
    skip_rerank: bool
