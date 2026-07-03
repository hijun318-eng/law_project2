"""
계산기 Tool 함수들 (LangChain @tool 데코레이터) + 순수 계산 함수
"""
from langchain_core.tools import tool
from engine.calculator.core import (
    calc_retirement_pay,
    calc_annual_leave_pay,
    calc_weekly_allowance,
    calc_minimum_wage_check,
)
from engine.constants import (
    MINIMUM_WAGE_2026,
    MINIMUM_WAGE_YEAR,
)

__all__ = [
    "calculate_retirement_pay",
    "calculate_annual_leave_pay",
    "calculate_weekly_allowance",
    "check_minimum_wage",

    "CALCULATOR_TOOLS",
]


# =====================================================================
# @tool 함수 (내부는 순수 계산 함수 호출 — core.py 참조)
# =====================================================================


@tool
def calculate_retirement_pay(
    years: float,
    months: int,
    last_3m_salary: int,
    paid_days: int = 92,
) -> str:
    """
    퇴직금을 계산합니다.

    Args:
        years:        근속 년수 (예: 3)
        months:       근속 개월 수 (0~11, 예: 6)
        last_3m_salary: 퇴직 전 3개월 동안의 총 임금 (원)
        paid_days:    퇴직 전 3개월 총 일수 (기본값: 92일)

    Returns:
        계산 결과 요약 문자열
    """
    result = calc_retirement_pay(years, months, last_3m_salary, paid_days)

    if not result["success"]:
        if "1년 미만" in str(result.get("error", "")):
            return (
                f"❌ 퇴직금 지급 대상이 아닙니다.\n"
                f"  • 근속일수: 약 {result['total_days']}일 (1년 미만)\n"
                f"  • 퇴직금은 1년 이상 근속한 근로자에게 지급됩니다.\n"
                f"  • 4주 평균 1주 소정근로시간이 15시간 미만인 경우도 제외됩니다."
            )
        return "❌ 임금 정보를 확인해주세요."

    return (
        f"💰 예상 퇴직금: **{result['severance']:,}원**\n\n"
        f"**계산 상세**\n"
        f"  • 1일 평균임금: {result['avg_wage']:,.0f}원 (= {result['last_3m_salary']:,}원 ÷ {result['paid_days']}일)\n"
        f"  • 근속일수: 약 {result['total_days']}일 ({result['years']}년 {result['months']}개월)\n"
        f"  • 산식: {result['avg_wage']:,.0f}원 × 30일 × ({result['total_days']}일 ÷ 365일)\n"
        f"  • = {result['severance']:,}원\n\n"
        f"**📋 유의사항**\n"
        f"  • 실제 금액은 회사 규정과 개인 상황에 따라 다를 수 있습니다.\n"
        f"  • 퇴직금은 확정급여형(DB) 기준으로 계산되었습니다."
    )


@tool
def calculate_annual_leave_pay(
    years_worked: int,
    daily_wage: int,
    used_days: int = 0,
) -> str:
    """
    연차수당을 계산합니다. 사용하지 않은 연차휴가에 대한 수당을 계산합니다.

    Args:
        years_worked: 근속 연수 (예: 2)
        daily_wage:   1일 통상임금 (원, 예: 80000)
        used_days:    이미 사용한 연차 일수 (기본값: 0)

    Returns:
        계산 결과 요약 문자열
    """
    result = calc_annual_leave_pay(years_worked, daily_wage, used_days)
    return (
        f"💰 예상 연차수당: **{result['amount']:,}원**\n\n"
        f"**계산 상세**\n"
        f"  • {result['day_note']}\n"
        f"  • 1일 통상임금: {result['daily_wage']:,}원\n"
        f"  • 발생 연차: {result['total_days']}일\n"
        f"  • 사용 연차: {result['used_days']}일\n"
        f"  • 미사용 연차: {result['remaining']}일\n"
        f"  • 산식: {result['daily_wage']:,}원 × {result['remaining']}일 = {result['amount']:,}원\n\n"
        f"**📋 유의사항**\n"
        f"  • 연차수당은 회계연도 기준으로 정산됩니다.\n"
        f"  • 1년 미만 근로자의 경우 월 1일씩 발생하며 최대 11일입니다."
    )


@tool
def calculate_weekly_allowance(
    hourly_wage: int,
    weekly_hours: int,
) -> str:
    """
    주휴수당을 계산합니다. 1주 소정근로시간 15시간 이상인 근로자의 주휴수당을 계산합니다.

    Args:
        hourly_wage:  시급 (원, 예: 10000)
        weekly_hours: 1주 소정근로시간 (예: 40)

    Returns:
        계산 결과 요약 문자열
    """
    result = calc_weekly_allowance(hourly_wage, weekly_hours)

    if not result["success"]:
        return (
            "⚠️ **주휴수당 지급 대상이 아닙니다.**\n\n"
            f"  • 1주 소정근로시간: {result['weekly_hours']}시간\n"
            f"  • 주 15시간 미만 근로자는 주휴수당 지급 대상에서 제외됩니다.\n\n"
            f"**📋 주휴수당 조건**\n"
            f"  • 1주 소정근로시간이 15시간 이상일 것\n"
            f"  • 소정근로일을 개근할 것\n"
            f"  • 근로계약서상 정해진 근로일수를 충족할 것"
        )

    return (
        f"💰 **주휴수당: 주 {result['weekly_allowance']:,}원**\n\n"
        f"**계산 상세**\n"
        f"  • 시급: {result['hourly_wage']:,}원\n"
        f"  • 1주 소정근로시간: {result['weekly_hours']}시간\n"
        f"  • 산식: ({result['weekly_hours']}시간 ÷ 40시간) × 8시간 × {result['hourly_wage']:,}원\n"
        f"  • 주 환산: {result['weekly_allowance']:,}원\n"
        f"  • 월 환산 (4.345주 기준): 약 {result['monthly_allowance']:,}원\n\n"
        f"**📋 유의사항**\n"
        f"  • 주휴수당은 소정근로일을 개근해야 지급됩니다.\n"
        f"  • 주 15시간 미만 근로자는 지급 대상이 아닙니다.\n"
        f"  • 월 환산액은 4.345주 기준으로 계산된 참고치입니다."
    )


@tool
def check_minimum_wage(
    hourly_wage: int,
    daily_hours: int,
    weekly_days: int,
    min_wage_per_hour: int = MINIMUM_WAGE_2026,
) -> str:
    """
    최저임금 위반 여부를 확인합니다. 2026년 기준 최저시급 10,320원을 기본값으로 판단하며, 직접 최저시급을 지정할 수도 있습니다.

    - 2026년 법정 최저시급: 10,320원 (고용노동부 고시 제2025-47호)
    - 필요 시 min_wage_per_hour 파라미터로 다른 금액을 지정할 수 있습니다.

    Args:
        hourly_wage: 내 시급 (원, 예: 10000)
        daily_hours: 1일 근무시간 (예: 8)
        weekly_days: 주간 근무일수 (예: 5)
        min_wage_per_hour: 비교할 최저시급 (원, 기본값 10320 = 2026년 기준)

    Returns:
        계산 결과 요약 문자열
    """
    result = calc_minimum_wage_check(
        hourly_wage, daily_hours, weekly_days, min_wage_per_hour
    )

    if result["success"]:
        return (
            f"✅ **최저임금 위반 아님**\n\n"
            f"**확인 결과**\n"
            f"  • 내 시급: {result['hourly_wage']:,}원\n"
            f"  • 1일 근무: {result['daily_hours']}시간 × 주 {result['weekly_days']}일 = 주 {result['weekly_hours']}시간\n"
            f"  • 실질 시급 (주휴 포함): {result['effective_hourly']:,.0f}원\n"
            f"  • {MINIMUM_WAGE_YEAR}년 최저시급: {result['current_min_wage']:,}원\n"
            f"  • 최저임금 대비: {result['ratio']:.1f}%\n\n"
            f"✅ 최저시급 {result['current_min_wage']:,}원 이상으로 적법합니다."
        )
    else:
        return (
            f"❌ **최저임금 위반 의심**\n\n"
            f"**확인 결과**\n"
            f"  • 내 시급: {result['hourly_wage']:,}원\n"
            f"  • 1일 근무: {result['daily_hours']}시간 × 주 {result['weekly_days']}일 = 주 {result['weekly_hours']}시간\n"
            f"  • 실질 시급 (주휴 포함): {result['effective_hourly']:,.0f}원\n"
            f"  • {MINIMUM_WAGE_YEAR}년 최저시급: {result['current_min_wage']:,}원\n"
            f"  • 최저임금 대비: {result['ratio']:.1f}%\n"
            f"  • 예상 월 손해액: 약 {result['monthly_shortage']:,}원\n\n"
            f"**📞 고용노동부 상담센터 1350으로 신고하세요.**\n"
            f"  • 최저임금 위반 시 사업주는 3년 이하의 징역 또는 3천만원 이하의 벌금에 처해질 수 있습니다."
        )


CALCULATOR_TOOLS = [
    calculate_retirement_pay,
    calculate_annual_leave_pay,
    calculate_weekly_allowance,
    check_minimum_wage,
]
