import re

from .mock_data import NEWS_DATA

NEWS_QUERY_EXPANSIONS = {
    "임금": ["임금", "월급", "급여", "수당", "포괄임금", "체불"],
    "최저임금": ["최저임금", "최저시급", "시급"],
    "괴롭힘": ["괴롭힘", "폭언", "따돌림", "직장내괴롭힘"],
    "육아": ["육아", "육아휴직", "모성보호", "출산"],
    "노조": ["노조", "노동조합", "교섭", "파업", "대기업"],
    "해고": ["해고", "부당해고", "권고사직", "구제신청"],
    "퇴직": ["퇴직", "퇴직금", "퇴직연금", "퇴직급여"],
    "산재": ["산재", "산업재해", "업무상", "재해"],
}


def categories() -> list[str]:
    return ["전체", *dict.fromkeys(item["category"] for item in NEWS_DATA)]


def search_news(query: str = "", category: str = "전체") -> list[dict]:
    tokens = _tokens(query)
    items = [item for item in NEWS_DATA if category == "전체" or item["category"] == category]
    scored = [(item, _score(item, tokens)) for item in items]
    if query.strip():
        scored = [(item, score) for item, score in scored if score > 0]
    return [item for item, _ in sorted(scored, key=lambda row: (-row[1], row[0]["date"]), reverse=False)]


def summarize(query: str, items: list[dict]) -> str:
    if not items:
        return ""
    categories_text = ", ".join(dict.fromkeys(item["category"] for item in items))
    top_titles = ", ".join(item["title"] for item in items[:2])
    if not query.strip():
        return f"선택한 조건에서 {len(items)}건의 뉴스가 있습니다. 주요 분야는 {categories_text}입니다."
    return f"'{query}'와 관련해 {len(items)}건을 찾았습니다. {categories_text} 이슈가 주로 연결되며, 대표 기사로 {top_titles} 등이 있습니다."


def _tokens(query: str) -> list[str]:
    base = [
        token
        for token in re.sub(r"[^\w\s가-힣]", " ", query.lower()).split()
        if len(token) >= 2 and token not in {"관련", "뉴스", "알려줘", "검색", "최신", "기사", "소식"}
    ]
    expanded = set(base)
    for token in base:
        for key, values in NEWS_QUERY_EXPANSIONS.items():
            if key in token or token in key or any(value in token or token in value for value in values):
                expanded.update(value.lower() for value in values)
    return list(expanded)


def _score(news: dict, tokens: list[str]) -> int:
    if not tokens:
        return 1
    title = news["title"].lower()
    category = news["category"].lower()
    summary = news["summary"].lower()
    score = 0
    for token in tokens:
        if category in token or token in category:
            score += 5
        if token in title:
            score += 4
        if token in summary:
            score += 2
    return score

