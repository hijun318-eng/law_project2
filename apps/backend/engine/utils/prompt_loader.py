from pathlib import Path

PROMPT_DIR = Path(__file__).parent.parent / "prompts"

def load_prompt(filename: str) -> str:
    key = Path(filename).stem
    try:
        from backend.services.prompts import load_active_prompt
        return load_active_prompt(key, fallback_filename=filename)
    except Exception:
        pass

    path = PROMPT_DIR / filename
    with open(path, "r", encoding="utf-8") as f:
        return f.read()
