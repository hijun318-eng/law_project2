"""
engine/ocr_contract/pipeline.py
"""

from __future__ import annotations

from engine.ocr_contract.ocr.ocr_engine import run_ocr
from engine.ocr_contract.llm.extractor import extract_fields
from engine.ocr_contract.rules.engine import run_rule_engine
from engine.ocr_contract.rules.validators.contract_gate import (
    validate_contract_document,
    NotAContractError,
)


def analyze_contract(image_path: str, debug: bool = False) -> dict:
    # STEP 1. OCR
    ocr_text = run_ocr(image_path)
    if debug:
        print(f"\n{'='*60}\nOCR 원문\n{'='*60}\n{ocr_text}")

    # STEP 2. 근로계약서 여부 검증 (2단 게이트)
    # 통과 실패 시 NotAContractError raise → 호출부에서 처리
    gate_result = validate_contract_document(ocr_text)

    # STEP 3. LLM 구조화 추출
    fields = extract_fields(ocr_text)

    # STEP 4. Rule Engine
    validation = run_rule_engine(fields)

    return {
        "ocr_text":   ocr_text,
        "gate":       gate_result,
        "fields":     fields,
        "validation": validation,
        "summary":    validation["summary"],
    }


def print_result(result: dict) -> None:
    SEP = "=" * 60
    v   = result["validation"]

    gate = result.get("gate", {})
    conf_icon = "🟢" if gate.get("confidence") == "high" else "🟡"
    print(f"\n{SEP}")
    print(f"📄 문서 검증  [{gate.get('gate', '?').upper()} 게이트]  {conf_icon} {gate.get('confidence', '').upper()}")
    print(f"   {gate.get('reason', '')}")

    print(f"\n{SEP}\n📋 추출된 계약 정보\n{SEP}")
    for field, value in result["fields"].items():
        icon = "✅" if value and str(value).strip() not in ("null", "") else "❌"
        print(f"  {icon} {field}: {value or '미기재'}")

    print(f"\n{SEP}\n🔍 필수기재사항 누락\n{SEP}")
    if v["missing"]:
        for field, law_ref in v["missing"].items():
            print(f"  ❌ {field}  ({law_ref})")
    else:
        print("  ✅ 모든 필수기재사항 기재됨")

    print(f"\n{SEP}\n⚖️  법정기준 위반\n{SEP}")
    if v["violations"]:
        for item in v["violations"]:
            print(f"  ❌ [{item['type']}] {item['field']}")
            print(f"      내용: {item['detail']}")
            print(f"      근거: {item['law_ref']}")
    else:
        print("  ✅ 위반 없음")

    if v["warnings"]:
        print(f"\n{SEP}\n⚠️  수동 확인 필요\n{SEP}")
        for w in v["warnings"]:
            print(f"  ⚠️  [{w['type']}] {w['field']}")
            print(f"      {w['detail']}")

    print(f"\n{SEP}\n📝 요약\n{SEP}")
    print(f"  {result['summary']}\n{SEP}\n")
