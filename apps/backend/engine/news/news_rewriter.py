import logging

logger = logging.getLogger(__name__)

class NewsQueryRewriter:

    def __init__(self, llm):
        self.llm = llm

    def rewrite(self, query: str) -> str:

        prompt = f"""
사용자 질문을 네이버 뉴스 검색용 키워드로 변환하세요.

규칙
- 2~4 단어
- 설명 금지
- 키워드만 출력

질문:
{query}
"""

        try:
            return (
                self.llm
                .invoke(prompt)
                .content
                .strip()
                .split("\n")[0]
            )

        except Exception as e:
            logger.warning(f"query rewrite failed: {e}")
            return query
