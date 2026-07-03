import re

def parse_work_hours(text: str):
    if not text:
        return None

    m = re.search(r"(\d{1,2}):(\d{2})\s*[~\-]\s*(\d{1,2}):(\d{2})", text)
    if m:
        sh, sm, eh, em = map(int, m.groups())
        return (eh * 60 + em - sh * 60 - sm) / 60

    return None
