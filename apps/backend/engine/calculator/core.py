"""
순수 계산 함수 — 의존성 없음
"""
from engine.constants import (
    MINIMUM_WAGE_2026,
    MINIMUM_WAGE_YEAR,
    WEEKLY_HOURLY_THRESHOLD,
    STANDARD_WEEKLY_HOURS,
    WEEKLY_ALLOWANCE_HOURS,
    MONTHLY_WEEKS,
    MIN_DAYS_FOR_SEVERANCE,
    SEVERANCE_DAYS_MULTIPLIER,
)


def calc_retirement_pay(
    years: float, months: int, last_3m_salary: int, paid_days: int = 92
) -> dict:
    """
    퇴직금 순수 계산 함수. 포매팅 없이 dict 반환.

    Returns: {
        "success": bool,
        "severance": int (원),  # 성공 시
        "total_days": int,
        "avg_wage": float,
        "years": float, "months": int, "last_3m_salary": int, "paid_days": int,
        "error": str | None  # 실패 시
    }
    """
    months = min(max(0, months), 11)  # 경계값 검증
    total_days = int(years * 365 + months * 30.5)
    avg_wage = last_3m_salary / paid_days if paid_days > 0 else 0
    if total_days < MIN_DAYS_FOR_SEVERANCE:
        return {
            "success": False,
            "error": "1년 미만",
            "total_days": total_days,
            "avg_wage": avg_wage,
            "severance": 0,
            "years": years,
            "months": months,
            "last_3m_salary": last_3m_salary,
            "paid_days": paid_days,
        }
    if avg_wage <= 0:
        return {
            "success": False,
            "error": "임금 정보 없음",
            "total_days": total_days,
            "avg_wage": 0,
            "severance": 0,
            "years": years,
            "months": months,
            "last_3m_salary": last_3m_salary,
            "paid_days": paid_days,
        }
    severance = avg_wage * SEVERANCE_DAYS_MULTIPLIER * (
        total_days / MIN_DAYS_FOR_SEVERANCE
    )
    return {
        "success": True,
        "severance": round(severance),
        "total_days": total_days,
        "avg_wage": avg_wage,
        "years": years,
        "months": months,
        "last_3m_salary": last_3m_salary,
        "paid_days": paid_days,
        "error": None,
    }


def calc_annual_leave_pay(
    years_worked: int, daily_wage: int, used_days: int = 0
) -> dict:
    """
    연차수당 순수 계산 함수.

    Returns: {
        "success": bool,
        "amount": int, "total_days": int, "remaining": int,
        "day_note": str, "daily_wage": int, "used_days": int
    }
    """
    if years_worked < 1:
        total_days = years_worked * 11
        day_note = "1년 미만 근로자: 월 1일 발생 (최대 11일)"
    else:
        total_days = min(15 + (years_worked - 1), 25)
        day_note = f"{years_worked}년차: 연 {total_days}일 발생 (최대 25일)"
    remaining = max(0, total_days - used_days)
    amount = daily_wage * remaining
    return {
        "success": True,
        "amount": amount,
        "total_days": total_days,
        "remaining": remaining,
        "day_note": day_note,
        "daily_wage": daily_wage,
        "used_days": used_days,
    }


def calc_weekly_allowance(hourly_wage: int, weekly_hours: int) -> dict:
    """
    주휴수당 순수 계산 함수.

    Returns: {
        "success": bool,
        "weekly_allowance": int, "monthly_allowance": int,
        "hourly_wage": int, "weekly_hours": int,
        "error": str | None
    }
    """
    if weekly_hours < WEEKLY_HOURLY_THRESHOLD:
        return {
            "success": False,
            "error": "15시간 미만",
            "weekly_hours": weekly_hours,
            "weekly_allowance": 0,
            "monthly_allowance": 0,
            "hourly_wage": hourly_wage,
        }
    weekly_allowance = (
        (weekly_hours / STANDARD_WEEKLY_HOURS)
        * WEEKLY_ALLOWANCE_HOURS
        * hourly_wage
    )
    monthly_allowance = weekly_allowance * MONTHLY_WEEKS
    return {
        "success": True,
        "weekly_allowance": round(weekly_allowance),
        "monthly_allowance": round(monthly_allowance),
        "hourly_wage": hourly_wage,
        "weekly_hours": weekly_hours,
        "error": None,
    }


def calc_minimum_wage_check(
    hourly_wage: int,
    daily_hours: int,
    weekly_days: int,
    min_wage_per_hour: int = MINIMUM_WAGE_2026,
) -> dict:
    """
    최저임금 위반 여부 순수 계산 함수.

    Returns: {
        "success": bool (True=위반아님),
        "effective_hourly": float, "current_min_wage": int, "ratio": float,
        "monthly_shortage": int, "weekly_hours": int,
        "hourly_wage": int, "daily_hours": int, "weekly_days": int
    }
    """
    current_min_wage = min_wage_per_hour if min_wage_per_hour > 0 else MINIMUM_WAGE_2026
    weekly_hours_val = daily_hours * weekly_days
    if weekly_hours_val >= WEEKLY_HOURLY_THRESHOLD:
        effective_hours = (
            weekly_hours_val
            + (weekly_hours_val / STANDARD_WEEKLY_HOURS) * WEEKLY_ALLOWANCE_HOURS
        )
    else:
        effective_hours = weekly_hours_val
    effective_hourly = (
        (hourly_wage * weekly_hours_val) / effective_hours
        if effective_hours > 0
        else 0
    )
    ratio = (effective_hourly / current_min_wage) * 100
    passed = effective_hourly >= current_min_wage
    # shortage 계산 단순화 (weekly_hours 중복 제거)
    shortage_per_week = (
        (current_min_wage - effective_hourly) * weekly_hours_val if not passed else 0
    )
    monthly_shortage = round(shortage_per_week * MONTHLY_WEEKS)
    return {
        "success": passed,
        "effective_hourly": effective_hourly,
        "current_min_wage": current_min_wage,
        "ratio": ratio,
        "monthly_shortage": monthly_shortage,
        "weekly_hours": weekly_hours_val,
        "hourly_wage": hourly_wage,
        "daily_hours": daily_hours,
        "weekly_days": weekly_days,
    }
