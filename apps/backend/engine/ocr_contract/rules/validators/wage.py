from engine.ocr_contract.config.constants import RULE_CHECKS, MIN_HOURLY_WAGE
from engine.ocr_contract.rules.parsers.wage_parser import (
    parse_hourly_wage,
    parse_monthly_wage,
)

def check_wage(fields: dict):
    violations = []
    warnings = []

    wage_text = fields.get("임금") or ""

    hourly = parse_hourly_wage(wage_text)
    monthly = parse_monthly_wage(wage_text)

    rule = RULE_CHECKS["최저임금"]

    if hourly:
        if hourly < rule["min_hourly_wage"]:
            violations.append({
                "type": "최저임금 위반",
                "field": "임금",
                "detail": f"기재된 시급 {hourly:,}원이 법정 최저시급 {MIN_HOURLY_WAGE:,}원보다 낮습니다.",
                "law_ref": rule["law_ref"],
            })

    elif monthly:
        hourly_est = int(monthly / 209)
        if hourly_est < MIN_HOURLY_WAGE:
            violations.append({
                "type": "최저임금 위반",
                "field": "임금",
                "detail": (
                    f"월급 {monthly:,}원을 월 209시간 기준으로 환산한 시급 "
                    f"{hourly_est:,}원이 법정 최저시급 {MIN_HOURLY_WAGE:,}원보다 낮습니다."
                ),
                "law_ref": rule["law_ref"],
            })

    elif wage_text.strip():
        warnings.append({
            "type": "임금 정보 확인 필요",
            "field": "임금",
            "detail": (
                f"'{wage_text}'에서 시급 또는 월급 금액을 추출할 수 없어 "
                "최저임금 검사를 수행하지 못했습니다."
            ),
        })

    return violations, warnings
