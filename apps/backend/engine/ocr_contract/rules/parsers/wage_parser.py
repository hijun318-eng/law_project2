import re

def parse_hourly_wage(text: str):
    if not text:
        return None

    cleaned = text.replace(",", "").replace(" ", "")
    m = re.search(r"시급(\d+)원?", cleaned)
    return int(m.group(1)) if m else None


def parse_monthly_wage(text: str):
    if not text:
        return None

    cleaned = text.replace(",", "").replace(" ", "")

    m = re.search(r"월급?(\d+)원?", cleaned)
    if m:
        return int(m.group(1))

    m = re.search(r"기본급(\d+)원?", cleaned)
    return int(m.group(1)) if m else None
