import re

from engine.config import llm
from engine.utils.prompt_loader import (
    load_prompt
)


class PrecedentSummaryService:

    def __init__(self):
        self.cache = {}
        self.prompt_template = load_prompt(
            "precedent_summary_prompt.md"
        )

    def make_dual_summary(
        self,
        content: str,
        category: str = ""
    ) -> tuple[str, str]:

        if content in self.cache:
            cached = self.cache[content]

            return (
                self._extract_section(
                    cached,
                    "search"
                ),
                self._extract_section(
                    cached,
                    "brief"
                )
            )

        prompt = self.prompt_template.format(
            content=content[:30000],
            category=category
        )

        try:
            result = llm.invoke(
                prompt
            ).content.strip()

        except Exception as e:
            print(f"[SAC ERROR] {e}")

            fallback = content[:300]

            return (
                fallback,
                fallback
            )

        self.cache[content] = result

        return (
            self._extract_section(
                result,
                "search"
            ),
            self._extract_section(
                result,
                "brief"
            )
        )

    @staticmethod
    def _extract_section(
        text: str,
        tag: str
    ) -> str:

        match = re.search(
            rf"<{tag}>(.*?)</{tag}>",
            text,
            re.DOTALL
        )

        return (
            match.group(1).strip()
            if match
            else text.strip()
        )


summary_service = (
    PrecedentSummaryService()
)
