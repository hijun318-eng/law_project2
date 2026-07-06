import json
import logging
import re

from engine.tools.registry import registry
from engine.utils.prompt_loader import load_prompt

from engine.news.constants import MAX_STEPS, MAX_TOOL_RETRY
from engine.news.news_parser import parse_action
from engine.news.news_rewriter import NewsQueryRewriter
from engine.news.news_executor import NewsExecutor
from engine.news.news_message_builder import (
    build_initial_messages,
    build_observation_message,
)

logger = logging.getLogger(__name__)


class NewsEngine:
    def __init__(self, llm):
        self.llm = llm
        self.rewriter = NewsQueryRewriter(llm)
        self.executor = NewsExecutor()

    def answer(self, question: str) -> dict:
        rewritten_question = self.rewriter.rewrite(question)
        logger.info(f"[USER QUESTION] {question} -> {rewritten_question}")

        tool_specs = json.dumps(registry.list_specs(), ensure_ascii=False, indent=2)
        prompt = load_prompt("news_prompt.md").replace("{tool_specs}", tool_specs)

        messages = build_initial_messages(
            prompt,
            question,
            rewritten_question,
        )

        steps: list[dict] = []
        action_history: list[str] = []
        valid_tools = self.executor.valid_tools()

        for step in range(MAX_STEPS):
            res  = self.llm.invoke(messages)
            text = res.content.strip()
            messages.append({"role": "assistant", "content": text})

            has_action = "Action:" in text
            
            has_final_answer = bool(
                re.search(r"(^|\n)\s*##\s+", text)
            )
            if "Final Answer:" in text:
                has_final_answer = True
            
            if has_action and text.find("## ") > -1:
                text = text[:text.find("## ")]

            if has_final_answer and not has_action:
                if "Final Answer:" in text:
                    final = text.split("Final Answer:", 1)[-1].strip()
                else:
                    final = text.strip()
                return {
                    "answer": final,
                    "steps": steps
                }

            action = parse_action(text)
            if not action:
                messages.append({
                    "role": "user",
                    "content": (
                        "Action이 감지되지 않았습니다. "
                        "반드시 아래 형식으로 한 줄만 출력하세요:\n"
                        f'Action: {{"tool": "news_search", "args": {{"query": "{rewritten_question}"}}}}'
                    ),
                })
                continue

            tool = action.get("tool")
            args = action.get("args", {})

            if step == 0 and tool == "news_search":
                args["query"] = rewritten_question

            if tool not in valid_tools:
                messages.append({
                    "role": "user",
                    "content": f"ERROR: '{tool}'은 존재하지 않는 tool입니다. 사용 가능: {sorted(valid_tools)}",
                })
                continue

            action_key = json.dumps({"tool": tool, "args": args}, sort_keys=True, ensure_ascii=False)
            recent = action_history[-MAX_TOOL_RETRY:]
            if len(recent) == MAX_TOOL_RETRY and all(k == action_key for k in recent):
                return {
                    "answer":  "동일한 검색이 반복되어 답변을 제공할 수 없습니다. 질문을 구체적으로 바꿔주세요.",
                    "steps":   steps,
                    "warning": True,
                }
            action_history.append(action_key)

            obs = self.executor.execute(tool, args)

            steps.append({
                "step":            step,
                "action":          action,
                "rewritten_query": args.get("query"),
                "observation":     obs,
            })

            evidence_list = obs.get("evidence", []) if isinstance(obs, dict) else []

            if not evidence_list:
                rule = (
                    "검색 결과가 없습니다. "
                    "다른 키워드나 법령명으로 반드시 재검색하세요. "
                    "포기하지 말고 유사어로 시도하세요."
                )
            else:
                rule = (
                    "evidence 외 정보 사용 금지. "
                    "evidence가 질문을 충분히 커버하지 못하면 "
                    "Final Answer 대신 다른 쿼리로 재검색하세요."
                )

            messages.append(
                build_observation_message(obs, rule,)
            )

        return {
            "answer":  "질문을 더 구체적으로 입력해주세요.",
            "steps":   steps,
            "warning": True,
        }
