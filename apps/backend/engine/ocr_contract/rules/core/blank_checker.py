import re

_BLANK_PATTERNS = [
    re.compile(r"^[년월일\s~부터까지\-\.]*$"),
    re.compile(r"^[\s시분~\-_부터까지,·]+$"),
    re.compile(r"^(원\s*){1,5}$"),
    re.compile(r"있을\s*\(\s*\)\s*없을\s*\(\s*\)"),
]

def is_blank(value) -> bool:
    if value is None:
        return True

    v = str(value).strip()
    if not v or v.lower() == "null":
        return True

    if any(p.search(v) for p in _BLANK_PATTERNS):
        return True

    return False
