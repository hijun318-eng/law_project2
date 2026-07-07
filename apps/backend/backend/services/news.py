"""
뉴스 검색 서비스 — engine/news_engine.NewsEngine 기반
"""
import hashlib
import logging

from django.core.cache import cache

from engine.config import llm
from engine.news_engine import NewsEngine
from engine.utils.llm_errors import llm_error_message

logger = logging.getLogger(__name__)

_news_engine = NewsEngine(llm)

CACHE_TTL_SECONDS = 600  # 같은 쿼리는 10분간 재사용
BACKUP_CACHE_TTL_SECONDS = 60 * 60 * 24  # API 오류 시 대체 응답으로 쓸 마지막 성공 결과 보관 기간
STALE_NOTICE = "\n\n※ 뉴스 API 응답 오류로 이전에 조회된 결과를 표시하고 있어 최신 내용이 아닐 수 있습니다."


def get_news(query: str = "") -> tuple[list[dict], str]:
    """NewsEngine으로 뉴스를 검색하고 (news_items, summary_text)를 반환. 같은 쿼리는 10분간 캐시 재사용.
    뉴스 API 오류/한도초과 시에는 마지막 성공 결과(백업 캐시)를 대신 반환한다."""
    search_query = query.strip() or "노동법 관련 최신 뉴스 알려줘"
    key_hash = hashlib.sha256(search_query.encode()).hexdigest()
    cache_key = f"news_engine:{key_hash}"
    backup_key = f"news_engine_backup:{key_hash}"

    cached = cache.get(cache_key)
    if cached is not None:
        return cached

    try:
        res = _news_engine.answer(search_query)
        api_error = res.get("api_error", False)
        error_message = "뉴스 API 오류로 결과를 불러오지 못했습니다. 잠시 후 다시 시도해주세요."
    except Exception as e:
        logger.exception("news_engine 호출 실패")
        res = {}
        api_error = True
        error_message = llm_error_message(e)

    if api_error:
        backup = cache.get(backup_key)
        if backup is not None:
            items, summary_text = backup
            return items, summary_text + STALE_NOTICE
        return [], error_message

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
    if items:
        cache.set(backup_key, (items, summary_text), BACKUP_CACHE_TTL_SECONDS)
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
