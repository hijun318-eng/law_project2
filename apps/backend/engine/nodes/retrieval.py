from pathlib import Path
import re
import requests
import logging

logger = logging.getLogger(__name__)

def _call_ranker(query: str, documents: list[str], timeout: int | None = None) -> list[float]:
    """랭커 마이크로서비스를 HTTP로 호출. 실패 시 균등 점수 fallback."""
    try:
        from django.conf import settings
        ranker_url = settings.RANKER_URL
        timeout = timeout or getattr(settings, "RANKER_TIMEOUT_SECONDS", 30)
    except (ImportError, AttributeError):
        ranker_url = 'http://localhost:8001'
        timeout = timeout or 30

    try:
        resp = requests.post(
            f'{ranker_url}/rerank/',
            json={'query': query, 'documents': documents},
            timeout=(5, timeout),
        )
        resp.raise_for_status()
        data = resp.json()
        scores = data.get('scores', [])
        if len(scores) != len(documents):
            logger.warning("ranker score count mismatch: expected=%s actual=%s", len(documents), len(scores))
            return [0.5] * len(documents)
        return scores
    except requests.RequestException as e:
        logger.warning(f'랭커 호출 실패: {e}')
        return [0.5] * len(documents)

from engine.database import precedent_db
from engine.retrievers.law_retriever import law_retriever
from engine.utils.law_normalizer import normalize_law_name, normalize_article_no

from engine.nodes.graph_state import GraphState
from engine.utils.execution_logger import log_node

# ==========================================================
# NODE 1: 판례 직접 검색
# ==========================================================
@log_node
def retrieve_precedent_node(state: GraphState) -> dict:

    question = state["question"]

    candidates = precedent_db.similarity_search(question, k=30)
    seen = set()
    unique = []
    for doc in candidates:
        cn = Path(doc.metadata.get("source_file", "")).stem
        if cn not in seen:
            seen.add(cn)
            unique.append(doc)

    pairs = [
        (question, doc.metadata.get("llm_brief", "") or doc.page_content[:1000])
        for doc in unique
    ]
    documents_for_rerank = [p[1] for p in pairs]
    scores = _call_ranker(question, documents_for_rerank) if documents_for_rerank else []

    reranked = sorted(zip(unique, scores), key=lambda x: x[1], reverse=True)

    final = []
    for doc, score in reranked[:5]:
        doc.metadata["rerank_score"] = float(score)
        final.append(doc)

    ref_articles_from_precedent = []
    seen_refs = set()

    for doc in final:
        brief = doc.metadata.get("llm_brief", "")
        matches = re.findall(
            r'([가-힣\s·]{2,30}(?:법|법률))\s*(제\d+조(?:의\d+)?)',
            brief
        )
        for raw_law, raw_article in matches:
            law_name = normalize_law_name(raw_law)
            article_no = normalize_article_no(raw_article)
            article_id = f"{law_name}|{article_no}"
            if article_id not in seen_refs:
                seen_refs.add(article_id)
                ref_articles_from_precedent.append(article_id)

    precedent_analysis = "\n\n".join(
        f"[사건번호: {Path(doc.metadata.get('source_file', '')).stem}]\n"
        f"{doc.metadata.get('llm_brief', '')[:500]}"
        for doc in final
    )

    return {
        "precedent_docs_direct": final,
        "precedent_analysis": precedent_analysis,
        "precedent_context_docs": final[:3],
        "ref_articles_from_precedent": ref_articles_from_precedent,
    }


# ==========================================================
# NODE 2: 법령 검색
# ==========================================================
@log_node
def retrieve_law_node(state: GraphState) -> dict:
    result = law_retriever.retrieve(state)

    law_docs = result.get("docs", [])
    law_source = result.get("source", "unknown")
    law_confidence = result.get("confidence", 0.0)

    law_analysis = [
        {
            "law_name": d.metadata.get("law_name", ""),
            "article_no": d.metadata.get("article_no", ""),
            "article_title": d.metadata.get("article_title", ""),
            "page_content": d.page_content,
            "score": d.metadata.get("final_score", 0.0),
        }
        for d in law_docs[:5]
    ]

    return {
        "law_docs": law_docs,
        "law_analysis": law_analysis,
        "law_source": law_source,
        "law_confidence": law_confidence,
    }
