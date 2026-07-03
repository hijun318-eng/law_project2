"""
판례 SAC 전처리

data/process/case/*.json
    ↓
search / brief 생성
    ↓
data/cache/sac/*.json
"""

import argparse
import json
import sys
from pathlib import Path

# scripts/preprocess/에서 직접 실행할 때 apps/backend/를 Python path에 추가
_THIS_DIR = Path(__file__).resolve().parent
_BACKEND_DIR = _THIS_DIR.parent.parent / "apps" / "backend"
if _BACKEND_DIR.exists() and str(_BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(_BACKEND_DIR))

from engine.services.precedent_summary_service import (
    summary_service
)
from engine.config import BASE_DIR

SOURCE_ROOT = BASE_DIR / "data" / "process" / "case"
CACHE_ROOT = BASE_DIR / "data" / "cache" / "sac"


def run_sac(force: bool = False):

    if not SOURCE_ROOT.exists():
        raise FileNotFoundError(
            f"폴더가 없습니다: {SOURCE_ROOT.resolve()}"
        )

    CACHE_ROOT.mkdir(
        parents=True,
        exist_ok=True
    )

    files = sorted(
        SOURCE_ROOT.rglob("*.json")
    )

    print(f"\n총 {len(files)}개 판례 발견\n")

    success = 0
    skipped = 0
    failed = 0

    for idx, json_file in enumerate(files, 1):

        case_no = json_file.stem

        cache_file = (
            CACHE_ROOT /
            f"{case_no}.json"
        )

        if cache_file.exists() and not force:

            print(
                f"[{idx}/{len(files)}] SKIP {case_no}"
            )

            skipped += 1
            continue

        print(
            f"[{idx}/{len(files)}] SAC 생성: {case_no}"
        )

        try:

            with open(
                json_file,
                encoding="utf-8"
            ) as f:
                items = json.load(f)

            if isinstance(items, dict):
                items = [items]

            # 판례 전체 내용 결합
            content = "\n\n".join(
                item.get(
                    "page_content",
                    ""
                )
                for item in items
            )

            if not content.strip():

                print(
                    f"  → 내용 없음"
                )

                failed += 1
                continue

            metadata = (
                items[0].get(
                    "metadata",
                    {}
                )
                if items
                else {}
            )
            
            category = metadata.get(
                "category",
                ""
            )
            search_text, brief_text = (
                summary_service.make_dual_summary(
                    content,
                    category
                )
            )

            save_data = {
                "case_no": case_no,
                "metadata": metadata,
                "search": search_text,
                "brief": brief_text
            }

            with open(
                cache_file,
                "w",
                encoding="utf-8"
            ) as f:

                json.dump(
                    save_data,
                    f,
                    ensure_ascii=False,
                    indent=2
                )

            success += 1

        except Exception as e:

            print(
                f"  [ERROR] {case_no}: {e}"
            )

            failed += 1

    print("\n" + "=" * 60)
    print(f"성공 : {success}")
    print(f"스킵 : {skipped}")
    print(f"실패 : {failed}")
    print(f"저장 위치 : {CACHE_ROOT.resolve()}")
    print("=" * 60)


if __name__ == "__main__":

    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--force",
        action="store_true",
        help="기존 SAC 캐시 재생성"
    )

    args = parser.parse_args()

    run_sac(
        force=args.force
    )
