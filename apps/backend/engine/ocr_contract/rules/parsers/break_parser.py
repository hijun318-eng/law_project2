import re

def parse_break_minutes(text: str):
    if not text:
        return None

    m = re.search(r"(\d{1,2}):(\d{2})\s*[~\-]\s*(\d{1,2}):(\d{2})", text)
    if m:
        sh, sm, eh, em = map(int, m.groups())
        return eh * 60 + em - sh * 60 - sm

    m = re.search(r"(\d+)\s*시간", text)
    if m:
        return int(m.group(1)) * 60

    m = re.search(r"(\d+)\s*분", text)
    if m:
        return int(m.group(1))

    return None
