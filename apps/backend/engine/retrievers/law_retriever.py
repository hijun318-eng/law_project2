"""
법령 검색기

판례 참조조문 기반(정밀) + 질의 기반(재현율) 두 경로로 법령을 검색하고
점수를 합산하여 최적 법령 조합을 반환합니다.
"""
from typing import List, Dict, Tuple

from langchain_core.documents import Document

from engine.database import law_db
from engine.utils.law_normalizer import normalize_law_name, normalize_article_no


PRECEDENT_SCORE  = 1.0   # 판례에서 직접 참조된 조문
QUERY_SCORE      = 0.6   # 질의 유사도 기반 조문
EMBEDDING_WEIGHT = 0.3   # 임베딩 유사도 가중치
MAX_REF_ARTICLES = 7     # 판례 참조조문 최대 처리 수
MAX_QUERY_DOCS   = 7     # 질의 기반 검색 수
MAX_OUTPUT_DOCS  = 7     # 최종 반환 수
PRECEDENT_SOURCE_THRESHOLD = 2  # 이 수 이상이면 "precedent" source


class LawRetriever:
    """
    두 경로로 법령을 검색:
    1. 판례 llm_brief의 참조조문 → Chroma metadata 정확 매칭 (정밀)
    2. 사용자 질의 → similarity_search (재현율)
    """

    def retrieve(self, state: dict) -> Dict:
        question       = state["question"]
        precedent_docs = self._retrieve_from_precedent(state)
        query_docs     = self._retrieve_from_query(question)
        merged, confidence = self._merge_and_score(precedent_docs, query_docs)

        return {
            "docs":       merged,
            "source":     self._determine_source(precedent_docs, query_docs),
            "confidence": confidence,
        }

    # ── 1. 판례 기반 법령 검색 ─────────────────────────────
    def _retrieve_from_precedent(self, state: dict) -> List[Document]:
        """
        ref_articles_from_precedent 목록에서
        'law_name|article_no' 형식으로 Chroma metadata 정확 매칭
        """
        ref_articles = state.get("ref_articles_from_precedent", [])
        docs         = []
        seen         = set()

        for article_id in ref_articles[:MAX_REF_ARTICLES]:
            if "|" not in article_id:
                continue

            raw_law, raw_article = article_id.split("|", 1)
            law_name   = normalize_law_name(raw_law)
            article_no = normalize_article_no(raw_article)
            key        = f"{law_name}|{article_no}"

            if key in seen:
                continue
            seen.add(key)

            result = law_db.get(where={
                "$and": [
                    {"law_name":   {"$eq": law_name}},
                    {"article_no": {"$eq": article_no}},
                ]
            })

            if not result or not result.get("documents"):
                continue

            for i, content in enumerate(result.get("documents", [])):
                docs.append(Document(
                    page_content=content,
                    metadata=result["metadatas"][i],
                ))

        return docs

    # ── 2. 질의 기반 법령 검색 ─────────────────────────────
    def _retrieve_from_query(self, question: str) -> List[Document]:
        """사용자 질의로 유사 법령 검색 """
        docs = law_db.similarity_search(question, k=MAX_QUERY_DOCS)
        return [d for d in docs if d.metadata.get("article_no")]

    # ── 3. 합산 + 점수 정렬 ───────────────────────────────
    def _merge_and_score(
        self,
        precedent_docs: List[Document],
        query_docs:     List[Document],
    ) -> Tuple[List[Document], float]:
        """
        판례 참조 조문(1.0) > 질의 기반 조문(0.6)
        임베딩 유사도가 metadata에 있으면 추가 가산
        """
        seen   = set()
        scored = []

        def _add(doc: Document, base_score: float) -> None:
            key = (
                normalize_law_name(doc.metadata.get("law_name", ""))
                + "|"
                + normalize_article_no(doc.metadata.get("article_no", ""))
            )
            if key in seen:
                return
            seen.add(key)

            final_score = base_score
            if "score" in doc.metadata:
                final_score += float(doc.metadata["score"]) * EMBEDDING_WEIGHT

            doc.metadata["final_score"] = round(final_score, 4)
            scored.append(doc)

        for d in precedent_docs:
            _add(d, PRECEDENT_SCORE)

        for d in query_docs:
            _add(d, QUERY_SCORE)

        scored.sort(key=lambda x: x.metadata.get("final_score", 0), reverse=True)

        total      = len(precedent_docs) + len(query_docs)
        confidence = (
            len(precedent_docs) / total
            if total > 0
            else 0.0
        )

        return scored[:MAX_OUTPUT_DOCS], round(confidence, 3)

    # ── 4. source 판단 ────────────────────────────────────
    def _determine_source(
        self,
        precedent_docs: List[Document],
        query_docs:     List[Document],
    ) -> str:
        has_precedent = len(precedent_docs) >= PRECEDENT_SOURCE_THRESHOLD
        has_query     = len(query_docs) > 0

        if has_precedent and has_query:
            return "hybrid"
        if has_precedent:
            return "precedent_based"
        if has_query:
            return "query_based"
        return "unknown"


law_retriever = LawRetriever()
