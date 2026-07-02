"""
벡터DB 생성 스크립트 (1회 실행)

data/process/의 JSON 파일을 읽어 Chroma 벡터DB를 생성합니다.
실행: python -m engine.init_db
"""
import argparse
import sys
from engine.builders.law_builder import build_law_db
from engine.builders.precedent_builder import build_precedent_db
from engine.builders.qna_builder import build_qna_db


def main():
    parser = argparse.ArgumentParser(description="벡터DB 생성 스크립트")
    parser.add_argument(
        "--force",
        action="store_true",
        help="기존 벡터DB를 삭제하고 다시 생성합니다.",
    )
    parser.add_argument(
        "--db",
        choices=["law", "precedent", "qna", "all"],
        default="all",
        help="생성할 DB (기본값: all)",
    )
    args = parser.parse_args()

    dbs = {
        "law": ("법령", build_law_db),
        "precedent": ("판례", build_precedent_db),
        "qna": ("질의회시", build_qna_db),
    }

    if args.db == "all":
        targets = dbs.values()
    else:
        targets = [dbs[args.db]]

    for name, builder in targets:
        print(f"\n{'='*60}")
        print(f"{name} DB 생성 시작")
        print(f"{'='*60}")
        try:
            builder(force=args.force)
            print(f"{name} DB 생성 완료\n")
        except (FileNotFoundError, ValueError) as e:
            print(f"[ERROR] {name} DB 생성 실패: {e}", file=sys.stderr)

    print("\n모든 DB 생성 작업 완료.")


if __name__ == "__main__":
    main()
