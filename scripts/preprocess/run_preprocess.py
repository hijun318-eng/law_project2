"""
전처리 통합 실행 스크립트

apps/backend/data/raw/의 원본 파일(PDF, MD)을 읽어
apps/backend/data/process/에 JSON으로 저장합니다.

실행 방법 (프로젝트 루트에서):
    python scripts/preprocess/run_preprocess.py

의존성:
    preprocess_qna.py → data/raw/pdf/*.pdf → data/process/qna/qna.json
    preprocess_case.py → data/raw/case/**/*.md → data/process/case/**/*.json
    preprocess_law.py → data/raw/law/*.pdf → data/process/law/**/*.json
"""
import sys
from pathlib import Path

# apps/backend/를 Python path에 추가하여 engine.* 모듈을 import 가능하게 함
_BACKEND_DIR = Path(__file__).resolve().parent.parent.parent / "apps" / "backend"
sys.path.insert(0, str(_BACKEND_DIR))

from preprocess_qna import run_qna
from preprocess_case import run_case
from preprocess_law import run_law
from preprocess_sac import run_sac


# apps/backend/ 기준 절대 경로
CONFIG = {
    "qna": {
        "input_dir": str(_BACKEND_DIR / "data" / "raw" / "pdf"),
        "output_dir": str(_BACKEND_DIR / "data" / "process" / "qna"),
    },
    "case": {
        "input_dir": str(_BACKEND_DIR / "data" / "raw" / "case"),
        "output_dir": str(_BACKEND_DIR / "data" / "process" / "case"),
    },
    "law": {
        "input_dir": str(_BACKEND_DIR / "data" / "raw" / "law"),
        "output_dir": str(_BACKEND_DIR / "data" / "process" / "law"),
    },
}


if __name__ == "__main__":
    # run_qna(**CONFIG["qna"])
    run_case(**CONFIG["case"])
    run_law(**CONFIG["law"])
    
    run_sac()
