# engine/news/news_normalizer.py
from __future__ import annotations
import re
from datetime import datetime, timezone

STOPWORDS = {"의", "을", "를", "이", "가", "은", "는", "에", "와", "과"}

def _score(query: str, item: dict) -> float:
    """제목/본문 키워드 매칭 + 최신성 점수"""
    keywords = [w for w in re.split(r"\s+", query) if w not in STOPWORDS]
    text = f"{item['title']} {item['description']}".lower()

    keyword_score = sum(1 for kw in keywords if kw.lower() in text) / max(len(keywords), 1)

    try:
        pub = datetime.strptime(item["pubDate"], "%a, %d %b %Y %H:%M:%S %z")
        days_old = (datetime.now(timezone.utc) - pub).days
        recency_score = max(0.0, 1.0 - days_old / 365)
    except Exception:
        recency_score = 0.0

    return round(keyword_score * 0.5 + recency_score * 0.5, 4)

def normalize_news(query: str, items: list[dict], top_k: int = 5) -> dict:
    scored = [
        {**item, "_score": _score(query, item)}
        for item in items
    ]
    scored.sort(key=lambda x: x["_score"], reverse=True)
    scored = [
        s for s in scored
        if s["_score"] >= 0.4
    ]
    top = scored[:top_k]

    return {
        "query":    query,
        "count":    len(top),
        "evidence": [
            {
                "title":       i["title"],
                "description": i["description"],
                "pubDate":     i["pubDate"],
                "link":        i["link"],
                "score":       i["_score"],
            }
            for i in top
        ],
    }
