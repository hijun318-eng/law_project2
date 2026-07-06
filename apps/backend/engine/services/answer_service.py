import re

from engine.config import llm
from engine.utils.prompt_loader import load_prompt
from string import Template
from pathlib import Path

class AnswerService:

    def __init__(self):
        pass

    def generate(self, law_analysis, precedent_docs, question, law_source: str = "unknown"):

        law_context = self._build_law_context(law_analysis)

        precedent_context = "\n\n".join(
            f"[사건번호:{Path(doc.metadata.get('source_file','')).stem}]\n"
            f"{doc.metadata.get('llm_brief','')}"
            for doc in precedent_docs
        )

        prompt_template = load_prompt("answer_prompt.md")
        prompt = Template(prompt_template).safe_substitute(
            law_context=law_context,
            precedent_context=precedent_context,
            question=question,
            law_source=law_source,
        )

        response = llm.invoke(prompt)
        token_usage = getattr(response, 'response_metadata', {}).get('token_usage', {})
        prompt_tokens = token_usage.get('prompt_tokens', 0)
        completion_tokens = token_usage.get('completion_tokens', 0)
        total_tokens = token_usage.get('total_tokens', 0)

        # QueryLogger에 LLM 사용량 기록
        from engine.utils.execution_logger import get_logger
        logger = get_logger()
        if logger:
            logger.record_llm_usage(
                node_name="generate_answer",
                model="gpt-5.4-nano",
                call_type="llm",
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                total_tokens=total_tokens,
            )

        answer = response.content

        return {
            "final_answer": answer,
            "law_context": law_context,
        }

    @staticmethod
    def _build_law_context(law_analysis: list) -> str:
        parts = []
        seen = set()
        
        for d in law_analysis[:5]:
            aid = f"{d['law_name']}_{d['article_no']}"
            
            if aid in seen:
                continue
            seen.add(aid)
            
            block = (
                f"<article>\n"
                f"<source>{d['law_name']} {d['article_no']} {d['article_title']}</source>\n"
                f"<content>{d['page_content']}</content>\n"
                f"</article>"
            )

            parts.append(block)
        return "\n".join(parts)


answer_service = AnswerService()
