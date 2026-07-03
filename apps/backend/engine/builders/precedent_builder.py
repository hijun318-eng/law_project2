import json
import shutil
from pathlib import Path

from langchain_core.documents import (
    Document
)

from langchain_chroma import Chroma

from engine.config import embedding, BASE_DIR

CACHE_ROOT = BASE_DIR / "data" / "cache" / "sac"


def build_precedent_db(
    force: bool = True
) -> Chroma:

    if not CACHE_ROOT.exists():

        raise FileNotFoundError(
            "먼저 preprocess_sac.py 실행 필요"
        )

    cache_files = sorted(
        CACHE_ROOT.rglob("*.json")
    )

    if not cache_files:

        raise ValueError(
            "SAC 캐시 없음"
        )

    all_docs = []

    seen_cases = set()

    for cache_file in cache_files:

        with open(
            cache_file,
            encoding="utf-8"
        ) as f:
            data = json.load(f)

        case_no = data["case_no"]

        if case_no in seen_cases:
            continue

        seen_cases.add(case_no)

        all_docs.append(
            Document(
                page_content=data["search"],
                metadata={
                    **data["metadata"],
                    "source_file":
                        f"{case_no}.json",
                    "llm_brief":
                        data["brief"]
                }
            )
        )

    db_path = str(BASE_DIR / "vector_db" / "precedents")

    if force:
        shutil.rmtree(
            db_path,
            ignore_errors=True
        )

    print(
        f"판례 {len(all_docs)}건 저장 중..."
    )

    return Chroma.from_documents(
        documents=all_docs,
        embedding=embedding,
        persist_directory=db_path
    )
