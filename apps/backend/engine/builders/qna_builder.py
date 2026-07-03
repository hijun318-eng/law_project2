import json
import shutil
from pathlib import Path

from langchain_core.documents import Document
from langchain_chroma import Chroma

from engine.config import embedding, BASE_DIR

DATA_ROOT = BASE_DIR / "data" / "process"


def build_qna_db(
    force: bool = False
) -> Chroma:

    qna_json = (
        DATA_ROOT
        / "qna"
        / "qna.json"
    )

    if not qna_json.exists():
        raise FileNotFoundError(
            f"파일이 없습니다: {qna_json.resolve()}"
        )

    with open(
        qna_json,
        encoding="utf-8"
    ) as f:
        items = json.load(f)

    if isinstance(items, dict):
        items = [items]

    qna_docs = []

    for item in items:

        qna_docs.append(
            Document(
                page_content=item[
                    "page_content"
                ],
                metadata=item.get(
                    "metadata",
                    {}
                )
            )
        )

    if not qna_docs:
        raise ValueError(
            "로드된 질의회시 Document가 없습니다."
        )

    db_path = str(BASE_DIR / "vector_db" / "qna")

    if force:
        shutil.rmtree(
            db_path,
            ignore_errors=True
        )

    return Chroma.from_documents(
        documents=qna_docs,
        embedding=embedding,
        persist_directory=db_path
    )
