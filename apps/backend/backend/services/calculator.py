from __future__ import annotations

import re
from dataclasses import asdict, dataclass

from engine.calculator import core as calc_core

MINIMUM_WAGE_2026 = calc_core.MINIMUM_WAGE_2026
MONTHLY_WEEKS = 4.345


@dataclass(frozen=True)
class CalcResult:
    title: str
    label: str
    amount: float
    tone: str
    lines: list[str]
    note: str = ""

    def to_dict(self) -> dict:
        data = asdict(self)
        data["amount_display"] = format_won(self.amount)
        return data


def format_won(value: float) -> str:
    return f"{round(value):,}원"


def calc_retirement(
    years: int, months: int, last_3_months_salary: float, paid_days: float = 92
) -> CalcResult:
    engine = calc_core.calc_retirement_pay(
        years, months, int(last_3_months_salary), int(paid_days),
    )
    total_days = engine["total_days"]
    if not engine["success"]:
        if engine.get("error") == "1년 미만":
            return CalcResult(
                title="퇴직금 계산",
                label="예상 퇴직금",
                amount=0,
                tone="amber",
                lines=[f"근속일수: 약 {total_days:,}일",
                       "퇴직금은 계속근로기간 1년 이상인 경우 발생합니다."],
                note="4주 평균 주 소정근로시간이 15시간 미만인 경우에도 제외될 수 있습니다.",
            )
        return CalcResult(
            title="퇴직금 계산",
            label="예상 퇴직금",
            amount=0,
            tone="amber",
            lines=[f"근속일수: 약 {total_days:,}일"],
        )
    avg_wage = engine["avg_wage"]
    severance = engine["severance"]
    return CalcResult(
        title="퇴직금 계산",
        label="예상 퇴직금",
        amount=severance,
        tone="blue",
        lines=[
            f"1일 평균임금: {format_won(avg_wage)}",
            f"근속일수: 약 {total_days:,}일",
            f"산식: {format_won(avg_wage)} × 30일 × ({total_days}일 ÷ 365일)",
        ],
    )


def calc_annual(
    years_worked: int, daily_wage: float, used_days: float = 0,
    remaining_days: float | None = None,
) -> CalcResult:
    engine = calc_core.calc_annual_leave_pay(
        years_worked, int(daily_wage), int(used_days),
    )
    total_days = engine["total_days"]
    remaining = (
        int(remaining_days)
        if remaining_days is not None
        else engine["remaining"]
    )
    amount = int(daily_wage) * remaining
    return CalcResult(
        title="연차수당 계산",
        label="예상 연차수당",
        amount=amount,
        tone="blue",
        lines=[
            engine["day_note"],
            f"1일 통상임금: {format_won(daily_wage)}",
            f"미사용 연차: {remaining:g}일",
            f"산식: {format_won(daily_wage)} × {remaining:g}일",
        ],
    )


def calc_weekly(hourly_wage: float, weekly_hours: float) -> CalcResult:
    engine = calc_core.calc_weekly_allowance(
        int(hourly_wage), int(weekly_hours),
    )
    if not engine["success"]:
        return CalcResult(
            title="주휴수당 계산",
            label="예상 주휴수당",
            amount=0,
            tone="amber",
            lines=[f"시급: {format_won(hourly_wage)}",
                   f"1주 소정근로시간: {int(weekly_hours):g}시간",
                   "주 15시간 미만 근로자는 주휴수당 지급 대상이 아닙니다."],
        )
    weekly = engine["weekly_allowance"]
    monthly = engine["monthly_allowance"]
    return CalcResult(
        title="주휴수당 계산",
        label="주 예상 주휴수당",
        amount=weekly,
        tone="blue",
        lines=[
            f"시급: {format_won(hourly_wage)}",
            f"1주 소정근로시간: {weekly_hours:g}시간",
            f"월 환산: 약 {format_won(monthly)}",
            f"산식: ({weekly_hours:g}시간 ÷ 40시간) × 8시간 × {format_won(hourly_wage)}",
        ],
        note="주휴수당은 소정근로일을 개근한 경우 지급됩니다.",
    )


def calc_minimum(
    hourly_wage: float, daily_hours: float, weekly_days: float,
    min_wage: float = MINIMUM_WAGE_2026,
) -> CalcResult:
    engine = calc_core.calc_minimum_wage_check(
        int(hourly_wage), int(daily_hours), int(weekly_days),
        int(min_wage),
    )
    passed = engine["success"]
    effective = engine["effective_hourly"]
    ratio = engine["ratio"]
    monthly_shortage = engine["monthly_shortage"]
    return CalcResult(
        title="최저임금 확인",
        label="최저임금 위반 아님" if passed else "최저임금 위반 의심",
        amount=effective if passed else monthly_shortage,
        tone="green" if passed else "red",
        lines=[
            f"실질 시급: {format_won(effective)}",
            f"기준 최저시급: {format_won(min_wage)} (2026년 기준)",
            f"근무시간: 하루 {int(daily_hours):g}시간 × 주 {int(weekly_days):g}일 = 주 {engine['weekly_hours']:g}시간",
            f"최저임금 대비: {ratio:.1f}%",
        ],
        note="" if passed else "임금명세서와 실제 근로시간을 함께 확인한 뒤 고용노동부 상담센터 1350에 문의해보세요.",
    )


def calculate_form(
    calc_type: str, salary: float = 0, months: float = 0, hours: float = 40,
) -> CalcResult:
    if calc_type == "annual":
        return calc_annual(int(months // 12), salary / 30 if salary else 0)
    if calc_type == "weekly":
        hourly = salary / (hours * MONTHLY_WEEKS) if salary and hours else 0
        return calc_weekly(hourly, hours)
    if calc_type == "minimum":
        daily_hours = min(8, max(1, round(hours / 5)))
        hourly = salary / (hours * MONTHLY_WEEKS) if salary and hours else MINIMUM_WAGE_2026
        return calc_minimum(hourly, daily_hours, 5)
    return calc_retirement(int(months // 12), int(months % 12), salary * 3)


def calculate_natural(text: str) -> tuple[str, CalcResult | None]:
    calc_type = _detect_type(text)
    tokens = _money_tokens(text)
    if not calc_type:
        return "계산 유형을 찾지 못했습니다. 퇴직금, 연차수당, 주휴수당, 최저임금 중 하나를 포함해 입력해주세요.", None

    if calc_type == "severance":
        period = _service_period(text)
        monthly_salary = _first_money_near(tokens, text, r"월|월급|급여|임금") \
                         or (tokens[0]["value"] if tokens else 0)
        if not period or not monthly_salary:
            return "퇴직금 계산에는 근무기간과 임금 정보가 필요합니다. 예: 퇴직금 계산해줘, 3년 근무, 월 300만원", None
        result = calc_retirement(period["years"], period["months"], monthly_salary * 3)
        return f"{result.label}은 {format_won(result.amount)}입니다.", result

    if calc_type == "annual":
        period = _service_period(text)
        years = int(period["total_months"] // 12) if period else _first_number(text, [r"(\d+(?:\.\d+)?)\s*년차"])
        remaining = _first_number(text, [r"미사용\s*(\d+(?:\.\d+)?)\s*일", r"남은\s*연차\s*(\d+(?:\.\d+)?)\s*일"])
        used = _first_number(text, [r"사용\s*(\d+(?:\.\d+)?)\s*일", r"(\d+(?:\.\d+)?)\s*일\s*사용"]) or 0
        daily_wage = _first_money_near(tokens, text, r"일|하루|통상") or (tokens[0]["value"] if tokens else 0)
        if years is None or not daily_wage:
            return "연차수당 계산에는 근속연수와 1일 통상임금이 필요합니다. 예: 연차수당, 2년 근무, 1일 통상임금 8만원, 3일 사용", None
        result = calc_annual(int(years), daily_wage, used, remaining)
        return f"{result.label}은 {format_won(result.amount)}입니다.", result

    if calc_type == "weekly":
        hourly_wage = _first_money_near(tokens, text, r"시급|시간급") or (tokens[0]["value"] if tokens else 0)
        weekly_hours = _first_number(text, [r"주\s*(?:소정)?(?:근로)?\s*(\d+(?:\.\d+)?)\s*시간", r"(\d+(?:\.\d+)?)\s*시간\s*/\s*주"])
        if not hourly_wage or weekly_hours is None:
            return "주휴수당 계산에는 시급과 주 소정근로시간이 필요합니다. 예: 시급 11000원, 주 20시간 주휴수당", None
        result = calc_weekly(hourly_wage, weekly_hours)
        return f"{result.label}은 {format_won(result.amount)}입니다.", result

    hourly_wage = _first_money_near(tokens, text, r"시급|시간급") or (tokens[0]["value"] if tokens else 0)
    daily_hours = _first_number(text, [r"(?:하루|1일|일)\s*(\d+(?:\.\d+)?)\s*시간", r"(\d+(?:\.\d+)?)\s*시간씩"])
    weekly_days = _first_number(text, [r"주\s*(\d+(?:\.\d+)?)\s*일"])
    if not hourly_wage or daily_hours is None or weekly_days is None:
        return "최저임금 확인에는 시급, 하루 근무시간, 주 근무일수가 필요합니다. 예: 최저임금 확인, 시급 9500원, 하루 8시간, 주 5일", None
    result = calc_minimum(hourly_wage, daily_hours, weekly_days)
    detail = f"예상 월 손해 {format_won(result.amount)}" if result.tone == "red" else f"실질 시급 {format_won(result.amount)}"
    return f"{result.label}: {detail}", result


def _detect_type(text: str) -> str | None:
    if re.search(r"최저|최저임금|최저시급", text):
        return "minimum"
    if "주휴" in text:
        return "weekly"
    if "연차" in text:
        return "annual"
    if "퇴직" in text:
        return "severance"
    if re.search(r"시급|시간급", text) and re.search(r"주\s*\d+", text):
        return "weekly"
    return None


def _money_tokens(text: str) -> list[dict]:
    tokens = []
    for match in re.finditer(r"(\d+(?:\.\d+)?)\s*(억|천만|백만|만원|만|원)", text.replace(",", "")):
        number = float(match.group(1))
        unit = match.group(2)
        multiplier = {"억": 100000000, "천만": 10000000, "백만": 1000000, "만원": 10000, "만": 10000, "원": 1}[unit]
        tokens.append({"value": round(number * multiplier), "index": match.start(), "raw": match.group(0)})
    return tokens


def _first_number(text: str, patterns: list[str]) -> float | None:
    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            return float(match.group(1))
    return None


def _service_period(text: str) -> dict | None:
    years = _first_number(text, [r"(\d+(?:\.\d+)?)\s*년"]) or 0
    months = _first_number(text, [r"(\d+(?:\.\d+)?)\s*개월"]) or 0
    if not years and not months:
        return None
    total_months = round((years * 12) + months)
    return {"years": total_months // 12, "months": total_months % 12, "total_months": total_months}


def _first_money_near(tokens: list[dict], text: str, pattern: str) -> float | None:
    for token in tokens:
        start = max(0, token["index"] - 12)
        end = token["index"] + 12
        if re.search(pattern, text[start:end]):
            return token["value"]
    return None
