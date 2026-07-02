import json
import shutil
from pathlib import Path

from langchain_core.documents import Document
from langchain_chroma import Chroma

from engine.config import embedding, BASE_DIR

DATA_ROOT = BASE_DIR / "data" / "process"


def build_law_db(force: bool = False) -> Chroma:

    law_root = DATA_ROOT / "law"

    if not law_root.exists():
        raise FileNotFoundError(
            f"폴더가 없습니다: {law_root.resolve()}"
        )

    json_files = sorted(
        law_root.rglob("*.json")
    )

    if not json_files:
        raise FileNotFoundError(
            f"{law_root} 안에 JSON 파일이 없습니다."
        )

    all_law_docs = []

    for json_file in json_files:

        print(f"로딩 중: {json_file.name}")

        with open(
            json_file,
            encoding="utf-8"
        ) as f:
            items = json.load(f)

        if isinstance(items, dict):
            items = [items]

        for item in items:

            meta = item.get("metadata", {})

            chapter_title = meta.get(
                "chapter_title",
                ""
            )

            article_title = meta.get(
                "article_title",
                ""
            )

            page_content = item.get(
                "page_content",
                ""
            )

            embedding_text = (
                f"{chapter_title}\n\n"
                f"{article_title}\n\n"
                f"{page_content}"
            )

            embedding_text = " ".join(
                embedding_text.split()
            )

            all_law_docs.append(
                Document(
                    page_content=embedding_text,
                    metadata=meta
                )
            )

    if not all_law_docs:
        raise ValueError(
            "로드된 법령 Document가 없습니다."
        )

    db_path = str(BASE_DIR / "vector_db" / "laws")

    if force:
        shutil.rmtree(
            db_path,
            ignore_errors=True
        )

    return Chroma.from_documents(
        documents=all_law_docs,
        embedding=embedding,
        persist_directory=db_path
    )
