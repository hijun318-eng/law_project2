"""
뉴스 검색 서비스 — engine/tools/news_search_tool 기반
"""
from django.utils import timezone

from engine.tools.news_search_tool import NewsSearchTool

_news_tool = NewsSearchTool()


def categories() -> list[str]:
    """정적 카테고리 목록 (Naver API는 category 필드 미제공)"""
    return [
        "전체", "최저임금", "직장내괴롭힘", "임금", "육아휴직",
        "노조", "해고", "퇴직금", "산재",
    ]


def search_news(query: str = "", category: str = "전체", display: int = 10) -> list[dict]:
    """NewsSearchTool로 뉴스를 검색하고 서비스 계층 형식으로 반환"""
    search_query = query.strip() or "노동법"
    res = _news_tool.run(query=search_query, display=display)

    if not res.success or not res.data.get("results"):
        return []

    items = []
    for i, item in enumerate(res.data["results"], start=1):
        items.append({
            "id": i,
            "title": item.get("title", ""),
            "date": _format_pubdate(item.get("pubDate", "")),
            "category": category,
            "summary": item.get("description", ""),
        })
    return items


def summarize(query: str, items: list[dict]) -> str:
    """검색 결과 요약 텍스트 생성"""
    if not items:
        return ""
    categories_text = ", ".join(
        dict.fromkeys(item["category"] for item in items)
    )
    top_titles = ", ".join(item["title"] for item in items[:2])
    if not query.strip():
        return (
            f"선택한 조건에서 {len(items)}건의 뉴스가 있습니다. "
            f"주요 분야는 {categories_text}입니다."
        )
    return (
        f"'{query}'와 관련해 {len(items)}건을 찾았습니다. "
        f"{categories_text} 이슈가 주로 연결되며, "
        f"대표 기사로 {top_titles} 등이 있습니다."
    )


def _format_pubdate(pubdate: str) -> str:
    """Naver API pubDate → 'YYYY-MM-DD'"""
    import datetime
    try:
        dt = datetime.datetime.strptime(
            pubdate.split(" +")[0].split(" -")[0],
            "%a, %d %b %Y %H:%M:%S",
        )
        return dt.strftime("%Y-%m-%d")
    except (ValueError, IndexError):
        return pubdate[:10] if len(pubdate) >= 10 else ""
