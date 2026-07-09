"""
뉴스 검색 서비스 — engine/news_engine.NewsEngine 기반
"""
import hashlib
import logging
import queue
import threading

from django.core.cache import cache

from engine.config import llm
from engine.news_engine import NewsEngine, NODE_LABELS
from engine.utils.llm_errors import llm_error_message

logger = logging.getLogger(__name__)

_news_engine = NewsEngine(llm)
_SENTINEL = object()

CACHE_TTL_SECONDS = 600  # 같은 쿼리는 10분간 재사용
BACKUP_CACHE_TTL_SECONDS = 60 * 60 * 24  # API 오류 시 대체 응답으로 쓸 마지막 성공 결과 보관 기간
STALE_NOTICE = "\n\n※ 뉴스 API 응답 오류로 이전에 조회된 결과를 표시하고 있어 최신 내용이 아닐 수 있습니다."


def _search_query(query: str) -> str:
    return query.strip() or "노동법 관련 최신 뉴스 알려줘"


def _backup_or_error(backup_key: str, error_message: str) -> tuple[list[dict], str]:
    backup = cache.get(backup_key)
    if backup is not None:
        items, summary_text = backup
        return items, summary_text + STALE_NOTICE
    return [], error_message


def _finalize_result(res: dict, cache_key: str, backup_key: str) -> tuple[list[dict], str]:
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


def get_news(query: str = "") -> tuple[list[dict], str]:
    """NewsEngine으로 뉴스를 검색하고 (news_items, summary_text)를 반환. 같은 쿼리는 10분간 캐시 재사용.
    뉴스 API 오류/한도초과 시에는 마지막 성공 결과(백업 캐시)를 대신 반환한다."""
    search_query = _search_query(query)
    key_hash = hashlib.sha256(search_query.encode()).hexdigest()
    cache_key = f"news_engine:{key_hash}"
    backup_key = f"news_engine_backup:{key_hash}"

    cached = cache.get(cache_key)
    if cached is not None:
        return cached

    try:
        res = _news_engine.answer(search_query)
    except Exception as e:
        logger.exception("news_engine 호출 실패")
        return _backup_or_error(backup_key, llm_error_message(e))

    if res.get("api_error", False):
        return _backup_or_error(backup_key, "뉴스 API 오류로 결과를 불러오지 못했습니다. 잠시 후 다시 시도해주세요.")

    return _finalize_result(res, cache_key, backup_key)


def stream_news(query: str = ""):
    """advice_api의 SupervisorEngine.stream_answer()와 동일한 방식으로, NewsEngine의
    진행상황을 실시간으로 yield하는 제너레이터.

    NewsEngine.answer()는 LangGraph 노드가 아니라 평범한 for-루프(ReAct)이므로
    progress_callback 인자를 직접 넘겨 루프 내부에서 호출하게 하고, 그 호출을
    백그라운드 스레드 + 큐를 통해 이 제너레이터로 실시간 전달한다.

    ("progress", node_name, phase, label, log, elapsed) 또는
    ("done", items, summary_text)를 yield한다."""
    search_query = _search_query(query)
    key_hash = hashlib.sha256(search_query.encode()).hexdigest()
    cache_key = f"news_engine:{key_hash}"
    backup_key = f"news_engine_backup:{key_hash}"

    cached = cache.get(cache_key)
    if cached is not None:
        items, summary_text = cached
        yield ("done", items, summary_text)
        return

    progress_queue: "queue.Queue" = queue.Queue()
    result_holder: dict = {}

    def on_progress(node_name, phase, log, elapsed):
        label = NODE_LABELS.get(node_name, node_name)
        progress_queue.put((node_name, phase, label, log, elapsed))

    def run():
        try:
            result_holder["res"] = _news_engine.answer(search_query, progress_callback=on_progress)
        except Exception as e:
            result_holder["exc"] = e
        finally:
            progress_queue.put(_SENTINEL)

    threading.Thread(target=run, daemon=True).start()

    while True:
        item = progress_queue.get()
        if item is _SENTINEL:
            break
        yield ("progress", *item)

    if "exc" in result_holder:
        logger.exception("news_engine 스트리밍 호출 실패", exc_info=result_holder["exc"])
        items, summary_text = _backup_or_error(backup_key, llm_error_message(result_holder["exc"]))
        yield ("done", items, summary_text)
        return

    res = result_holder.get("res", {})
    if res.get("api_error", False):
        items, summary_text = _backup_or_error(backup_key, "뉴스 API 오류로 결과를 불러오지 못했습니다. 잠시 후 다시 시도해주세요.")
        yield ("done", items, summary_text)
        return

    items, summary_text = _finalize_result(res, cache_key, backup_key)
    yield ("done", items, summary_text)


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
