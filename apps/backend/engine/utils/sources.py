"""
그래프 실행 결과(state)에서 소스 문서(법령/판례) 리스트를 추출하는 공용 유틸
"""


def format_sources(state: dict) -> list:
    """법령/판례 검색 그래프의 state에서 프론트엔드 표시용 소스 리스트를 추출"""
    sources = []

    for doc in state.get("law_docs", []):
        m = doc.metadata
        sources.append({
            "type": "law",
            "law_name": m.get("law_name", ""),
            "article_no": m.get("article_no", ""),
            "article_title": m.get("article_title", ""),
            "chapter_title": m.get("chapter_title", ""),
        })

    for doc in state.get("precedent_context_docs", []):
        m = doc.metadata
        sources.append({
            "type": "precedent",
            "case_no": (
                m.get("source_file", "")
                .replace(".md", "")
                .replace(".json", "")
            ),
            "category": m.get("category", ""),
        })

    return sources
