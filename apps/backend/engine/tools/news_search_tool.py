import os
import requests
import html
import re
import logging
from engine.tools.base import BaseTool, ToolResult

logger = logging.getLogger(__name__)

NAVER_NEWS_URL = "https://openapi.naver.com/v1/search/news.json"
REQUEST_TIMEOUT = 5

class NewsSearchTool(BaseTool):
    name = "news_search"
    description = (
        "네이버 뉴스 API로 한국 노동법·법령 관련 최신 뉴스를 검색합니다. "
        "판결, 개정, 시행, 위반 등 최신 동향 질문에 사용하세요."
    )
    input_schema = {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "검색어 (예: '중대재해처벌법 판결 2026')",
            },
            "display": {
                "type": "integer",
                "description": "결과 수 (기본 5, 최대 10)",
                "default": 5,
            },
        },
        "required": ["query"],
    }

    def __init__(self):
        self._client_id     = os.getenv("NAVER_CLIENT_ID")
        self._client_secret = os.getenv("NAVER_CLIENT_SECRET")
        if not self._client_id or not self._client_secret:
            logger.warning("NAVER_CLIENT_ID or NAVER_CLIENT_SECRET not set.")

    def _clean(self, text: str) -> str:
        return re.sub(r"<[^>]+>", "", html.unescape(text)).strip()

    def _execute(self, query: str, display: int = 5) -> ToolResult:
        display = max(1, min(display, 10))  # 범위 강제
        try:
            res = requests.get(
                NAVER_NEWS_URL,
                headers={
                    "X-Naver-Client-Id":     self._client_id,
                    "X-Naver-Client-Secret": self._client_secret,
                },
                params={"query": query, "display": display, "sort": "date"},
                timeout=REQUEST_TIMEOUT,
            )
            res.raise_for_status()

            items = [
                {
                    "title":       self._clean(i["title"]),
                    "description": self._clean(i["description"]),
                    "link":        i["link"],
                    "pubDate":     i["pubDate"],
                    "source":      i.get("originallink", i["link"]),
                }
                for i in res.json().get("items", [])
            ]
            logger.info(f"news_search '{query}' → {len(items)} results")
            return ToolResult(success=True, data={"query": query, "results": items})

        except requests.HTTPError as e:
            logger.error(f"Naver API HTTP error: {e}")
            return ToolResult(False, None, f"HTTP error: {e.response.status_code}")
        except requests.Timeout:
            return ToolResult(False, None, "Request timed out")
        except Exception as e:
            logger.exception(f"Unexpected error in news_search: {e}")
            return ToolResult(False, None, str(e))

# 등록
from engine.tools.registry import registry
registry.register(NewsSearchTool())
