"""
법령 PDF 전처리 모듈
조문(조) 단위 파싱 → Document 분리
ChromaDB 저장에 최적화된 flat 메타데이터 구조
"""

import json
import re
import traceback
from pathlib import Path
from typing import Optional

import fitz
from langchain_core.documents import Document


# ============================================================
# 정규식
# ============================================================

# 법령명 추출: "근로기준법", "개인정보 보호법" 등
# - 줄 전체가 법령명인 경우 (짧고, '법'으로 끝나거나 포함)
RE_LAW_NAME = re.compile(
    r"^[가-힣\s]{2,30}(?:법|규정|령|규칙|지침)$"
)

# 약칭 추출
RE_ABBR = re.compile(r"약칭[:\s：]+([^\s\)\]]{2,20})")

# 개정·신설·삭제 이력 태그 제거
# 1) 정상 닫힌 태그: <개정 2021. 1. 5.>, <개 정 2024. 10. 22.>
# 2) PDF 줄바꿈으로 잘린 미닫힌 태그: "<개정 2010. 6. 4." → 줄 끝까지 제거
RE_REVISION = re.compile(
    r"<\s*(?:개\s*정|신\s*설|삭\s*제|전문\s*개정)[^>]*>?"
)
# 대괄호 법령 메타 태그 제거
# [본조신설 2024. 10. 22.], [시행일: 2027. 1. 1.], [전문개정 ...], [제목개정 ...] 등
# → 대괄호 안에 주요 키워드가 포함된 것은 모두 제거
RE_BRACKET_TAG = re.compile(
    r"\[(?:[^\]]*(?:시행일|전문개정|전문|본조신설|제목개정|일부개정|타법개정)[^\]]*)\]"
)

# 페이지 말미 잔류 조문 번호 제거
# "근로기준법 [시행일: ...] 제43조의6" 형태로 page_content 끝에 붙는 경우
# → 법령명 + (선택적 대괄호) + 조문번호 패턴
RE_TRAILING_ARTICLE = re.compile(
    r"\s*[가-힣\s]+법\s*(?:\[[^\]]*\])?\s*제\d+조(?:의\d+)?\s*$"
)

# 장/절
RE_CHAPTER = re.compile(r"^(제\d+장)\s+(.+)")
RE_SECTION = re.compile(r"^(제\d+절)\s+(.+)")

# 부칙
RE_ADDENDA = re.compile(r"^부칙\s*(?:<.+?>)?")

# 조문 헤더: "제23조(해고 등의 제한)" 또는 "제23조 (해고 등의 제한)"
RE_ARTICLE = re.compile(
    r"^(제\d+조(?:의\d+)?)\s*\(([^)]*)\)"
)

# 항 번호: ①②③ ... ⑳ 또는 ㉑ 이상 유니코드 원문자
RE_PARAGRAPH = re.compile(
    r"^([①②③④⑤⑥⑦⑧⑨⑩⑪⑫⑬⑭⑮⑯⑰⑱⑲⑳"
    r"㉑㉒㉓㉔㉕㉖㉗㉘㉙㉚㉛㉜㉝㉞㉟])\s*(.*)"
)

# 노이즈 라인 제거
RE_NOISE = re.compile(
    r"^(법제처|국가법령정보센터|www\.law\.go\.kr"
    r"|\d{1,3}$"
    r"|\[시행\s+\d{4}"
    r"|고용노동부|과학기술정보통신부|보건복지부"
    r"|환경부|국토교통부|법무부|행정안전부|기획재정부"
    r"|산업통상자원부|교육부|문화체육관광부)"
)


# ============================================================
# PDF 텍스트 추출
# ============================================================

def _pdf_to_text(pdf_path: str) -> str:
    try:
        doc = fitz.open(pdf_path)
        pages = []
        for page in doc:
            text = page.get_text("text")
            if text:
                pages.append(text)
        doc.close()
        return "\x0c".join(pages)
    except Exception as e:
        raise RuntimeError(f"PDF 읽기 실패 ({pdf_path}): {e}")


def _split_pages(raw: str) -> list[tuple[int, str]]:
    return [
        (i + 1, page)
        for i, page in enumerate(raw.split("\x0c"))
        if page.strip()
    ]


# ============================================================
# 노이즈 제거
# ============================================================

def _clean_line(line: str) -> Optional[str]:
    s = line.strip()

    if not s:
        return None

    if re.match(r"^\d{1,3}$", s):
        return None

    if RE_NOISE.match(s):
        return None

    # ======================================================
    # 1) 가장 먼저: 개정/신설/삭제 "문자열 패턴" 제거
    # ======================================================
    s = re.sub(r"개\s*정\s*\d{0,4}.*?\d{4}\.\s*\d{1,2}\.\s*\d{1,2}\.?", "", s)
    s = re.sub(r"개\s*정\s*\d{0,4}", "", s)

    # ======================================================
    # 2) 꺾쇠 태그 계열 전부 제거
    # ======================================================
    s = re.sub(r"<[^>]*>", "", s)   # 완전 태그 제거
    s = re.sub(r"<\s*[^>]*", "", s) # 열린 꺾쇠 잔여 제거
    s = re.sub(r"[^<]*\s*>", "", s) # 닫힌 꺾쇠 잔여 제거

    # ======================================================
    # 3) 날짜 단독 잔여 제거
    # ======================================================
    s = re.sub(r"\d{4}\.\s*\d{1,2}\.\s*\d{1,2}\.?", "", s)

    # ======================================================
    # 4) 기존 브라켓/노이즈 제거 유지
    # ======================================================
    s = RE_BRACKET_TAG.sub("", s)
    s = RE_TRAILING_ARTICLE.sub("", s).strip()

    # 남은 대괄호 메타 태그 제거
    s = re.sub(r"\[(?:전문|시행일:?\s*|본조신설|제목개정|일부개정|타법개정)[^\]]*\]", "", s)

    # PDF 깨짐으로 남은 시행일 꼬리 제거
    s = re.sub(r"\[시행일:?\s*\]", "", s)

    # [전문] 단독 잔재 제거
    s = re.sub(r"\[전문\]", "", s)

    # 페이지 하단에 붙는 '제101조' 같은 꼬리 제거
    s = re.sub(r"\s*제\d+조(?:의\d+)?\s*$", "", s).strip()

    # ======================================================
    # 5) 조문번호 단독 제거
    # ======================================================
    s = re.sub(r"^제\d+조(?:의\d+)?\s*$", "", s).strip()

    # ======================================================
    # 6) 최종 정리
    # ======================================================
    s = re.sub(r"\s*,\s*,", ",", s)
    s = re.sub(r"^\s*,\s*", "", s)
    s = re.sub(r"[\s,]+$", "", s).strip()

    if not s:
        return None

    return s

# ============================================================
# 법령명 추출 (개선)
# ============================================================

def _extract_law_name(raw: str, pdf_stem: str) -> str:
    """
    우선순위:
    1. 약칭 (약칭: OOO법)
    2. 첫 15줄에서 RE_LAW_NAME 패턴에 맞는 줄
    3. 파일명(stem)
    """
    # 1. 약칭
    abbr_m = RE_ABBR.search(raw[:600])
    if abbr_m:
        return abbr_m.group(1).strip()

    # 2. 첫 15줄에서 법령명 패턴
    for line in raw.split("\n")[:20]:
        s = line.strip()
        # 노이즈 제거 후 확인
        if not s or RE_NOISE.match(s):
            continue
        if RE_LAW_NAME.match(s):
            return s

    # 3. 파일명에서 법령명 추출 (괄호, 날짜, 법률번호 제거)
    # 첫 번째 괄호 이전까지만 사용
    cleaned = pdf_stem.split("(")[0].strip()
    # 중복 공백 제거
    cleaned = re.sub(r"\s+", " ", cleaned)
    return cleaned if cleaned else pdf_stem

# ============================================================
# 조문 단위 파싱
# ============================================================

def _split_articles(pages: list[tuple[int, str]]) -> list[dict]:
    """
    반환 형식:
    {
        "article_no": "제23조",
        "article_title": "해고 등의 제한",
        "chapter_no": "제2장",
        "chapter_title": "근로계약",
        "section_no": "제1절",      # 없으면 ""
        "section_title": "...",     # 없으면 ""
        "content_lines": ["조문 전체 텍스트 라인들..."]
    }
    """
    articles: list[dict] = []
    current: Optional[dict] = None

    cur_chapter_no = ""
    cur_chapter_title = ""
    cur_section_no = ""
    cur_section_title = ""

    for _page_num, text in pages:
        for raw_line in text.split("\n"):
            line = _clean_line(raw_line)
            if not line:
                continue

            # 장
            chapter_m = RE_CHAPTER.match(line)
            if chapter_m:
                cur_chapter_no = chapter_m.group(1)
                cur_chapter_title = chapter_m.group(2).strip()
                cur_section_no = ""
                cur_section_title = ""
                continue

            # 절
            section_m = RE_SECTION.match(line)
            if section_m:
                cur_section_no = section_m.group(1)
                cur_section_title = section_m.group(2).strip()
                continue

            # 부칙
            if RE_ADDENDA.match(line):
                if current:
                    articles.append(current)
                current = {
                    "article_no": "부칙",
                    "article_title": line,
                    "chapter_no": "",
                    "chapter_title": "",
                    "section_no": "",
                    "section_title": "",
                    "content_lines": [line],
                }
                continue

            # 조문
            article_m = RE_ARTICLE.match(line)
            if article_m:
                if current:
                    articles.append(current)
                article_no = article_m.group(1)
                article_title = (
                    article_m.group(2).strip()
                    if article_m.group(2)
                    else ""
                )
                current = {
                    "article_no": article_no,
                    "article_title": article_title,
                    "chapter_no": cur_chapter_no,
                    "chapter_title": cur_chapter_title,
                    "section_no": cur_section_no,
                    "section_title": cur_section_title,
                    "content_lines": [],  # 헤더 라인 제외, 본문만 누적
                }
                # 헤더 뒤에 본문이 같은 줄에 이어지는 경우 처리
                # 예: "제1조(목적) 이 법은 ..."
                after_header = line[article_m.end():].strip()
                if after_header:
                    current["content_lines"].append(after_header)
                continue

            # 조문 내용 누적
            if current is not None:
                prev = current["content_lines"]
                if prev and prev[-1].endswith("-"):
                    prev[-1] = prev[-1][:-1] + line
                else:
                    prev.append(line)

    if current:
        articles.append(current)

    return articles


# ============================================================
# 항 텍스트 최종 정리
# ============================================================

def _join_and_clean(text: str) -> str:
    """
    항 라인들을 합친 뒤 최종 노이즈 제거.
    - 페이지 말미에 붙은 조문 번호 제거
      예: "...따라야 한다. 근로기준법 [시행일: 2027. 1. 1.] 제43조의6"
    - 남은 trailing 쉼표·공백 정리
    """
    s = text.strip()
    # 페이지 경계 잔류 조문 번호 (법령명 + 조문번호 패턴)
    s = RE_TRAILING_ARTICLE.sub("", s).strip()
    # 남은 trailing 쉼표 정리
    s = re.sub(r"[\s,]+$", "", s).strip()
    return s


# ============================================================
# PDF 1개 → Document 리스트
# ============================================================

def parse_law_pdf(
    pdf_path: str,
    law_name: Optional[str] = None,
) -> list[Document]:
    """
    법령 PDF 1개 → 조(article) 단위 Document 리스트.

    메타데이터 구조 (ChromaDB 친화적 flat 구조):
    {
        "law_name":      "근로기준법",
        "chapter_no":    "제2장",
        "chapter_title": "근로계약",
        "section_no":    "제1절",      # 없으면 필드 자체 제외
        "section_title": "...",        # 없으면 필드 자체 제외
        "article_no":    "제23조",
        "article_title": "해고 등의 제한",
    }
    page_content: 조문 전체 본문 텍스트 (헤더·개정 이력 제외, 항 번호 포함)
    """
    raw = _pdf_to_text(pdf_path)
    if not raw.strip():
        raise RuntimeError(f"텍스트 추출 실패: {pdf_path}")

    resolved_law_name = law_name or _extract_law_name(raw, Path(pdf_path).stem)

    pages = _split_pages(raw)
    articles = _split_articles(pages)

    docs: list[Document] = []

    for art in articles:
        content = _join_and_clean(" ".join(art["content_lines"]))
        if not content:
            continue

        if art["article_no"] != "부칙":
            article_header = art["article_no"]
            if art["article_title"]:
                article_header += f"({art['article_title']})"
            content = _join_and_clean(f"{article_header} {content}")

        metadata: dict = {
            "law_name":      resolved_law_name,
            "chapter_no":    art["chapter_no"],
            "chapter_title": art["chapter_title"],
            "article_no":    art["article_no"],
            "article_title": art["article_title"],
        }

        # 절 정보는 있을 때만 포함
        if art["section_no"]:
            metadata["section_no"] = art["section_no"]
            metadata["section_title"] = art["section_title"]

        docs.append(
            Document(
                page_content=content,
                metadata=metadata,
            )
        )

    return docs


# ============================================================
# 폴더 전체 PDF → JSON
# ============================================================

def process_all_pdfs(
    input_dir: str = "./data",
    output_dir: str = "./data/process",
) -> None:
    """
    data/**/*.pdf → data/process/**/*.json
    process 폴더 내 파일은 건너뜀.
    """
    input_path = Path(input_dir)
    output_path = Path(output_dir)

    pdf_files = [
        p for p in input_path.rglob("*.pdf")
        if "process" not in p.parts
    ]

    print(f"총 {len(pdf_files)}개 PDF 발견")

    for pdf_file in pdf_files:
        print(f"\n처리 중: {pdf_file.name}")
        try:
            file_law_name = re.sub(
                r"\s+",
                " ",
                pdf_file.stem.split("(")[0].strip()
            )

            docs = parse_law_pdf(
                str(pdf_file),
                law_name=file_law_name
            )
            output_file = (
                output_path
                / pdf_file.relative_to(input_path).parent
                / f"{pdf_file.stem}.json"
            )
            output_file.parent.mkdir(parents=True, exist_ok=True)

            with open(output_file, "w", encoding="utf-8") as f:
                json.dump(
                    [
                        {
                            "page_content": d.page_content,
                            "metadata": d.metadata,
                        }
                        for d in docs
                    ],
                    f,
                    ensure_ascii=False,
                    indent=2,
                )

            print(f"  → Document {len(docs)}개 저장 ({output_file})")

        except Exception as e:
            print(f"  ⚠ 오류 ({pdf_file.name}): {type(e).__name__}: {e}")
            traceback.print_exc()

    print("\nPDF 전처리 완료")


# ============================================================
# Law 실행
# ============================================================

def run_law(input_dir: str, output_dir: str):
    process_all_pdfs(input_dir=input_dir, output_dir=output_dir)
