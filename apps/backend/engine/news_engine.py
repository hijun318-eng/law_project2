import json
import logging
import re
import time

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

# advice_api의 supervisor NODE_LABELS와 동일한 방식으로, 진행상황 콜백이 전달하는
# node_name을 프론트엔드에 보여줄 한글 라벨로 변환하기 위한 매핑
NODE_LABELS = {
    "news_rewrite": "🔎 질문 분석",
    "news_search": "📰 뉴스 검색",
}


class NewsEngine:
    def __init__(self, llm):
        self.llm = llm
        self.rewriter = NewsQueryRewriter(llm)
        self.executor = NewsExecutor()

    def answer(self, question: str, progress_callback=None) -> dict:
        def progress(node: str, phase: str, log: str | None = None, elapsed: float | None = None):
            if progress_callback:
                try:
                    progress_callback(node, phase, log, elapsed)
                except Exception:
                    pass

        progress("news_rewrite", "start")
        rewrite_start = time.time()
        rewritten_question = self.rewriter.rewrite(question)
        progress("news_rewrite", "end", None, time.time() - rewrite_start)
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
            step_start = time.time()
            progress("news_search", "start", f"검색 시도 {step + 1}/{MAX_STEPS}")

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
                progress("news_search", "end", "답변 정리 완료", time.time() - step_start)
                return {
                    "answer": final,
                    "steps": steps
                }

            action = parse_action(text)
            if not action:
                progress("news_search", "end", "응답 형식 오류, 재시도", time.time() - step_start)
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
                progress("news_search", "end", f"'{tool}'은 지원하지 않는 도구", time.time() - step_start)
                messages.append({
                    "role": "user",
                    "content": f"ERROR: '{tool}'은 존재하지 않는 tool입니다. 사용 가능: {sorted(valid_tools)}",
                })
                continue

            action_key = json.dumps({"tool": tool, "args": args}, sort_keys=True, ensure_ascii=False)
            recent = action_history[-MAX_TOOL_RETRY:]
            if len(recent) == MAX_TOOL_RETRY and all(k == action_key for k in recent):
                progress("news_search", "end", "동일 검색 반복으로 중단", time.time() - step_start)
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

            # 검색 결과가 없는 것과 API 자체 오류(한도초과/타임아웃 등)는 다르게 처리.
            # 후자는 재검색해도 해결되지 않으므로 즉시 중단하고 상위(services.news)에서
            # 캐시 폴백을 시도하도록 신호를 넘긴다.
            if isinstance(obs, dict) and obs.get("error"):
                progress("news_search", "end", "뉴스 API 오류", time.time() - step_start)
                return {
                    "answer": "",
                    "steps": steps,
                    "api_error": True,
                }

            evidence_list = obs.get("evidence", []) if isinstance(obs, dict) else []

            if not evidence_list:
                rule = (
                    "검색 결과가 없습니다. "
                    "다른 키워드나 법령명으로 반드시 재검색하세요. "
                    "포기하지 말고 유사어로 시도하세요."
                )
                progress("news_search", "end", "검색 결과 없음, 재검색 예정", time.time() - step_start)
            else:
                rule = (
                    "evidence 외 정보 사용 금지. "
                    "evidence가 질문을 충분히 커버하지 못하면 "
                    "Final Answer 대신 다른 쿼리로 재검색하세요."
                )
                progress("news_search", "end", f"{len(evidence_list)}건 검색됨", time.time() - step_start)

            messages.append(
                build_observation_message(obs, rule,)
            )

        return {
            "answer":  "질문을 더 구체적으로 입력해주세요.",
            "steps":   steps,
            "warning": True,
        }
