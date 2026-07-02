import json
import re

from engine.ocr_contract.config.constants import EXTRACT_PROMPT
from engine.config import llm


def extract_fields(ocr_text: str) -> dict:
    prompt = EXTRACT_PROMPT.format(ocr_text=ocr_text[:4000])
    raw = llm.invoke(prompt).content.strip()

    try:
        cleaned = re.sub(r"```(?:json)?", "", raw).replace("```", "")
        return json.loads(cleaned)
    except:
        return {
            "임금": None,
            "근무장소": None,
            "업무내용": None,
            "소정근로시간": None,
            "휴게시간": None,
            "휴일": None,
            "연차": None,
            "계약기간": None,
        }
