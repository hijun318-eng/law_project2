"""
판례 MD 전처리 모듈
판례 .md 파일 → JSON 변환
"""

import json
import traceback
from pathlib import Path


def _normalize_category_name(folder_name: str) -> str:
    if "." in folder_name:
        return folder_name.split(".", 1)[1].strip()
    return folder_name.strip()


def process_all_mds(
    input_dir: str = "./data",
    output_dir: str = "./data/process",
) -> None:
    """
    판례 .md 파일 → JSON 변환.
    data/**/*.md → data/process/**/*.json
    process 폴더 내 파일은 건너뜀.
    """
    input_path = Path(input_dir)
    output_path = Path(output_dir)

    md_files = [
        p for p in input_path.rglob("*.md")
        if "process" not in p.parts
    ]

    print(f"총 {len(md_files)}개 MD 발견")

    for md_file in md_files:
        print(f"처리 중: {md_file.name}")
        try:
            content = md_file.read_text(encoding="utf-8")
            category = _normalize_category_name(md_file.parent.name)
            output_file = (
                output_path
                / md_file.relative_to(input_path).parent
                / f"{md_file.stem}.json"
            )
            output_file.parent.mkdir(parents=True, exist_ok=True)

            with open(output_file, "w", encoding="utf-8") as f:
                json.dump(
                    [
                        {
                            "page_content": content,
                            "metadata": {
                                "source_file": md_file.name,
                                "category": category,
                            },
                        }
                    ],
                    f,
                    ensure_ascii=False,
                    indent=2,
                )
            print(f"  → 저장 완료 ({output_file})")

        except Exception as e:
            print(f"  ⚠ 오류 ({md_file.name}): {e}")
            traceback.print_exc()

    print("MD 전처리 완료")



# ============================================================
# Case 실행
# ============================================================

def run_case(input_dir: str, output_dir: str):
    process_all_mds(input_dir=input_dir, output_dir=output_dir)
