import json

def parse_action(text: str) -> dict | None:
    if "Action:" not in text:
        return None

    try:
        part = text.split("Action:", 1)[1]

        start = part.find("{")
        if start == -1:
            return None

        depth = 0
        end = -1

        for i, ch in enumerate(part[start:], start):
            if ch == "{":
                depth += 1
            elif ch == "}":
                depth -= 1

                if depth == 0:
                    end = i
                    break

        if end == -1:
            return None

        raw = part[start:end + 1]

        return json.loads(raw)

    except Exception:
        return None
