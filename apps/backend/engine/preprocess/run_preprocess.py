"""
전처리 통합 실행 스크립트

data/raw/의 원본 파일(PDF, MD)을 읽어 data/process/에 JSON으로 저장합니다.

실행 방법 (프로젝트 루트에서):
    python -m engine.preprocess.run_preprocess

의존성:
    preprocess_qna.py → data/raw/pdf/*.pdf → data/process/qna/qna.json
    preprocess_case.py → data/raw/case/**/*.md → data/process/case/**/*.json
    preprocess_law.py → data/raw/law/*.pdf → data/process/law/**/*.json
"""
from engine.preprocess.preprocess_qna import run_qna
from engine.preprocess.preprocess_case import run_case
from engine.preprocess.preprocess_law import run_law
from engine.preprocess.preprocess_sac import run_sac


# 프로젝트 루트 기준 경로
CONFIG = {
    "qna": {
        "input_dir": "data/raw/pdf",
        "output_dir": "data/process/qna",
    },
    "case": {
        "input_dir": "data/raw/case",
        "output_dir": "data/process/case",
    },
    "law": {
        "input_dir": "data/raw/law",
        "output_dir": "data/process/law",
    },
}


if __name__ == "__main__":
    # run_qna(**CONFIG["qna"])
    run_case(**CONFIG["case"])
    run_law(**CONFIG["law"])
    
    run_sac()
