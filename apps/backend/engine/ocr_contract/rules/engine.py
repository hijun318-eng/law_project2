from engine.ocr_contract.rules.validators.required import check_required
from engine.ocr_contract.rules.validators.wage import check_wage
from engine.ocr_contract.rules.validators.time import check_time


def run_rule_engine(fields: dict) -> dict:

    missing = check_required(fields)

    wage_v, wage_w = check_wage(fields)
    time_v, time_w = check_time(fields)

    violations = wage_v + time_v
    warnings = wage_w + time_w

    return {
        "is_valid": len(missing) == 0 and len(violations) == 0,
        "missing": missing,
        "violations": violations,
        "warnings": warnings,
        "summary": _build_summary(missing, violations, warnings),
    }


def _build_summary(missing, violations, warnings):
    if not missing and not violations:
        return "✅ 위반 사항 없음"

    parts = []
    if missing:
        parts.append(f"누락 {len(missing)}")
    if violations:
        parts.append(f"위반 {len(violations)}")

    return "❌ " + ", ".join(parts)
