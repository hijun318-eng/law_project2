from engine.ocr_contract.config.constants import RULE_CHECKS
from engine.ocr_contract.rules.parsers.time_parser import parse_work_hours
from engine.ocr_contract.rules.parsers.break_parser import parse_break_minutes

def check_time(fields: dict):
    violations = []
    warnings = []

    work = parse_work_hours(fields.get("소정근로시간") or "")
    break_m = parse_break_minutes(fields.get("휴게시간") or "")

    if not work:
        return violations, warnings

    # max work hours
    if work > 12:
        violations.append({
            "type": "MAX_WORK_HOURS",
            "field": "소정근로시간",
            "detail": f"{work}h 초과",
            "law_ref": "근로기준법",
        })

    rule = RULE_CHECKS["휴게시간_8시간"]

    if work >= 8:
        required = 60
    elif work >= 4:
        required = 30
    else:
        required = 0

    if required:
        if break_m is None:
            violations.append({
                "type": "BREAK_MISSING",
                "field": "휴게시간",
            })
        elif break_m < required:
            violations.append({
                "type": "BREAK_VIOLATION",
                "field": "휴게시간",
            })

    return violations, warnings
