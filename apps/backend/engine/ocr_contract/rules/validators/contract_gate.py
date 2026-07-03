"""

업로드된 문서가 근로계약서인지 검증하는 2단 게이트.

[게이트 구조]
  GATE 1 — 키워드 휴리스틱 (비용 0, 빠름)
    "근로계약서", "임금", "소정근로시간" 등 필수 키워드 존재 여부 확인.
    명백한 비계약서(영수증, 이력서 등)를 여기서 차단.
    → 통과 시 GATE 2 진입

  GATE 2 — LLM 분류기 (정밀)
    OCR 텍스트를 LLM에게 전달해 근로계약서 여부를 판단.
    비정형 계약서, 영문 계약서, 레이아웃이 특이한 경우도 대응.
    → 통과 시 파이프라인 진행

[반환 구조]
  {
    "is_valid":   bool,          # True면 근로계약서로 판정
    "gate":       "keyword" | "llm" | None,   # 어느 게이트에서 판정됐는지
    "confidence": "high" | "low",
    "reason":     str,           # 판정 사유
  }
"""

from __future__ import annotations

import re
from typing import Optional


# ── GATE 1 기준값 ─────────────────────────────────────────────────────────────
# 근로계약서에 반드시 등장하는 핵심 키워드 그룹.
# 각 그룹에서 1개 이상 존재해야 해당 그룹 충족으로 판정.
# REQUIRED_GROUPS를 모두 충족해야 GATE 1 통과.
# 조항 변경과 무관하게 "계약서 형식 자체"를 판별하는 용도이므로 코드에 유지.
_KEYWORD_GROUPS: list[tuple[str, list[str]]] = [
    ("계약_유형",  ["근로계약", "고용계약", "labor contract", "employment contract"]),
    ("핵심_조항",  ["임금", "급여", "소정근로시간", "근로시간", "휴게", "휴일"]),
    ("당사자",     ["사용자", "근로자", "갑", "을", "employer", "employee"]),
]

# GATE 1 통과 기준: 전체 그룹 수 대비 충족해야 할 최소 그룹 수
_MIN_GROUP_MATCH = 2  # 3개 중 2개 이상

# 명백한 비계약서 키워드 — 이 중 하나라도 존재하면 즉시 거부
_REJECT_KEYWORDS: list[str] = [
    "영수증", "receipt", "invoice", "청구서", "이력서", "resume", "curriculum vitae",
    "진단서", "처방전", "주민등록", "여권", "passport",
]

# ── GATE 2 프롬프트 ───────────────────────────────────────────────────────────
_CLASSIFY_PROMPT = """\
아래 텍스트가 한국 근로기준법상 "근로계약서"인지 판단하세요.

[판단 기준]
- 근로계약서: 사용자와 근로자 사이의 근로 조건(임금, 근로시간, 업무 등)을 기재한 문서
- 근로계약서가 아닌 것: 영수증, 이력서, 진단서, 용역계약서, 위임계약서, 빈 양식, 관계없는 문서 등

[주의]
- 내용이 불완전하거나 일부 항목이 누락된 경우도 근로계약서로 판정할 수 있습니다.
- 확실하지 않으면 "uncertain"으로 표시하세요.

텍스트:
{ocr_text}

반드시 아래 JSON 형식으로만 응답하세요 (마크다운 없이 순수 JSON):
{{
  "is_labor_contract": true 또는 false 또는 "uncertain",
  "reason": "판단 근거 (1~2문장)"
}}
"""


# ══════════════════════════════════════════════════════════════════════════════
# 공개 인터페이스
# ══════════════════════════════════════════════════════════════════════════════

class NotAContractError(ValueError):
    """업로드된 문서가 근로계약서가 아닐 때 발생."""

    def __init__(self, reason: str, gate: Optional[str] = None):
        self.reason = reason
        self.gate   = gate
        super().__init__(reason)


def validate_contract_document(ocr_text: str) -> dict:
    """
    OCR 텍스트가 근로계약서인지 2단 게이트로 검증한다.

    근로계약서로 판정되면 결과 dict를 반환한다.
    근로계약서가 아니면 NotAContractError를 raise한다.

    Returns:
        {
            "is_valid":   True,
            "gate":       "keyword" | "llm",
            "confidence": "high" | "low",
            "reason":     str,
        }

    Raises:
        NotAContractError: 근로계약서가 아닌 경우
    """
    # GATE 1: 키워드 휴리스틱
    gate1 = _gate1_keyword(ocr_text)
    if gate1["verdict"] == "reject":
        raise NotAContractError(reason=gate1["reason"], gate="keyword")

    if gate1["verdict"] == "pass":
        return {
            "is_valid":   True,
            "gate":       "keyword",
            "confidence": "high",
            "reason":     gate1["reason"],
        }

    gate2 = _gate2_llm(ocr_text)
    if not gate2["is_valid"]:
        raise NotAContractError(reason=gate2["reason"], gate="llm")

    return {
        "is_valid":   True,
        "gate":       "llm",
        "confidence": "low" if gate2["uncertain"] else "high",
        "reason":     gate2["reason"],
    }


# ══════════════════════════════════════════════════════════════════════════════
# GATE 1: 키워드 휴리스틱
# ══════════════════════════════════════════════════════════════════════════════

def _gate1_keyword(text: str) -> dict:
    """
    Returns:
        {"verdict": "pass" | "reject" | "uncertain", "reason": str}
    """
    normalized = text.lower()

    for kw in _REJECT_KEYWORDS:
        if kw.lower() in normalized:
            return {
                "verdict": "reject",
                "reason":  f"근로계약서가 아닌 문서로 판단됩니다. (감지된 키워드: '{kw}')",
            }

    matched_groups: list[str] = []
    for group_name, keywords in _KEYWORD_GROUPS:
        if any(kw.lower() in normalized for kw in keywords):
            matched_groups.append(group_name)

    if len(matched_groups) >= _MIN_GROUP_MATCH:
        return {
            "verdict": "pass",
            "reason":  f"근로계약서 핵심 키워드 확인 (충족 그룹: {', '.join(matched_groups)})",
        }

    return {
        "verdict": "uncertain",
        "reason":  f"키워드 불충분 (충족 그룹: {len(matched_groups)}/{len(_KEYWORD_GROUPS)}) — LLM 검증으로 이행",
    }


# ══════════════════════════════════════════════════════════════════════════════
# GATE 2: LLM 분류기
# ══════════════════════════════════════════════════════════════════════════════

def _gate2_llm(ocr_text: str) -> dict:
    """
    Returns:
        {"is_valid": bool, "uncertain": bool, "reason": str}
    """
    import json, re as _re
    from pathlib import Path
    import sys

    project_root = Path(__file__).resolve().parent.parent.parent
    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))

    try:
        from engine.config import llm
        prompt  = _CLASSIFY_PROMPT.format(ocr_text=ocr_text[:3000])
        raw     = llm.invoke(prompt).content.strip()
        cleaned = _re.sub(r"```(?:json)?", "", raw).replace("```", "").strip()
        data    = json.loads(cleaned)
    except Exception as e:
        return {
            "is_valid":  True,
            "uncertain": True,
            "reason":    f"LLM 분류기 오류로 검증 생략: {e}",
        }

    verdict   = data.get("is_labor_contract")
    reason    = data.get("reason", "")
    uncertain = verdict == "uncertain"

    if verdict is True:
        return {"is_valid": True,  "uncertain": False, "reason": reason}
    if uncertain:
        return {"is_valid": True,  "uncertain": True,  "reason": f"[불확실] {reason}"}

    return {"is_valid": False, "uncertain": False, "reason": reason}
