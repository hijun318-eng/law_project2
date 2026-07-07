"""
뉴스 검색 서비스 — engine/news_engine.NewsEngine 기반
"""
import hashlib

from django.core.cache import cache

from engine.config import llm
from engine.news_engine import NewsEngine

_news_engine = NewsEngine(llm)

CACHE_TTL_SECONDS = 600  # 같은 쿼리는 10분간 재사용


def get_news(query: str = "") -> tuple[list[dict], str]:
    """NewsEngine으로 뉴스를 검색하고 (news_items, summary_text)를 반환. 같은 쿼리는 10분간 캐시 재사용."""
    search_query = query.strip() or "노동법 관련 최신 뉴스 알려줘"
    cache_key = f"news_engine:{hashlib.sha256(search_query.encode()).hexdigest()}"

    cached = cache.get(cache_key)
    if cached is not None:
        return cached

    res = _news_engine.answer(search_query)

    steps = res.get("steps", [])
    evidence = steps[-1]["observation"].get("evidence", []) if steps else []

    items = [
        {
            "title": e.get("title", ""),
            "date": _format_pubdate(e.get("pubDate", "")),
            "summary": e.get("description", ""),
            "link": e.get("link", ""),
        }
        for e in evidence
    ]
    summary_text = res.get("answer", "").strip() or "관련 뉴스를 찾지 못했습니다."

    cache.set(cache_key, (items, summary_text), CACHE_TTL_SECONDS)
    return items, summary_text


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
