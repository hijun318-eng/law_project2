from pathlib import Path
import json

from engine.config import llm, BASE_DIR
from engine.constants.procedure_map import PROCEDURE_MAP
from engine.utils.prompt_loader import load_prompt


class ProcedureService:

    def __init__(self):
        pass

    def generate(self, used_precedents: list[str]) -> str:

        if not used_precedents:
            return "관련 판례를 찾을 수 없습니다."

        precedent_no = used_precedents[0]
        root = BASE_DIR / "data" / "process" / "case"
        category = None

        for path in root.rglob(f"{precedent_no}.json"):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    precedent = json.load(f)

                # 리스트 또는 dict 모두 처리
                item = precedent[0] if isinstance(precedent, list) else precedent
                category = item.get("metadata", {}).get("category")
                break

            except Exception as e:
                print(f"[ProcedureService] 파일 읽기 실패 {path}: {e}")
                continue
            
        print(f"[DEBUG] precedent_no={precedent_no}, category={category}")

        if not category:
            return f"판례({precedent_no})의 카테고리를 찾을 수 없습니다."

        info = PROCEDURE_MAP.get(category)

        if not info:
            return f"{category} 카테고리에 대한 절차 정보가 없습니다."

        prompt = load_prompt("procedure_prompt.md").format(
            category=category,
            agency=info["agency"],
            worker_actions="\n".join(f"- {a}" for a in info["worker_actions"]),
            evidence="\n".join(f"- {e}" for e in info["evidence"]),
            deadline=info["deadline"] or "없음",
        )

        response = llm.invoke(prompt)
        token_usage = getattr(response, 'response_metadata', {}).get('token_usage', {})
        prompt_tokens = token_usage.get('prompt_tokens', 0)
        completion_tokens = token_usage.get('completion_tokens', 0)
        total_tokens = token_usage.get('total_tokens', 0)

        from engine.utils.execution_logger import get_logger
        logger = get_logger()
        if logger:
            logger.record_llm_usage(
                node_name="procedure_guide",
                model="gpt-5.4-nano",
                call_type="llm",
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                total_tokens=total_tokens,
            )

        return response.content


procedure_service = ProcedureService()
