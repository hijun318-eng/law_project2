from __future__ import annotations

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
    """
    LLM 기반 자연어 계산 처리.
    LangGraph ReAct 에이전트(gpt-5.4-nano)가 자연어에서 파라미터를 추출하고
    engine/calculator/core.py의 순수 계산 함수를 도구로 호출하여 결과를 반환합니다.
    """
    try:
        from engine.calculator_engine import CalculatorEngine
        engine = CalculatorEngine()
        result = engine.calculate(text)
        return result.get("answer", "죄송합니다. 결과를 생성하지 못했습니다."), None
    except Exception as e:
        return f"죄송합니다. 계산 중 오류가 발생했습니다: {e}", None
