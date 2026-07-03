"""
근로기준법 질의회시집 전처리 스크립트
======================================
전략: 질의(question)만 page_content로 임베딩하고,
      회시(answer) 전체 + 모든 메타데이터는 metadata에 저장.
      → 사용자의 비정형 사례 설명이 질의와 직접 매칭되도록 설계.

출력: List[Document]  (LangChain Document 객체)
       - page_content : "질의: {question}"
       - metadata     : title, answer, chapter_num, chapter_name,
                         reference, ref_date, start_page, source,
                         title_keywords
"""

import json
import re
import fitz  # PyMuPDF
from pathlib import Path
from typing import Counter, Optional
from langchain_core.documents import Document


# ──────────────────────────────────────────────
# 1. 상수 정의
# ──────────────────────────────────────────────

PDF_PATH = Path("data\\질의회시집\\근로기준법 질의회시집(2018.4.~2023.6.).pdf")

# (시작 페이지, 챕터 번호, 챕터명)
CHAPTER_MAP = [
    (25,  1, "총칙"),
    (111, 2, "근로계약"),
    (199, 3, "임금"),
    (367, 4, "근로시간과 휴식"),
    (483, 6, "직장 내 괴롭힘의 금지"),
    (531, 8, "재해보상"),
    (539, 9, "취업규칙"),
    (616, 99, "END"),
]

# 행정해석 문서번호 패턴
REF_PATTERN = re.compile(
    r"\((?:근로기준정책과|근기|퇴직급여보장팀|임금근로시간과|고용차별개선과"
    r"|근로개선정책과|임금정책과|여성고용정책과|고용평등정책과|산재예방정책과)"
    r"[^\)]{0,50}\d{4}\.\d{1,2}\.\d{1,2}\.?\)"
)

# 홀수 페이지 헤더: '제N장 챕터명 / 쪽수'
ODD_HEADER  = re.compile(r"^제\d+장[^/\n]*/\s*\d+\n")
# 짝수 페이지 헤더: '쪽 / 근로기준법 질의회시집'
EVEN_HEADER = re.compile(r"^\d+\s*/\s*근로기준법\s*질의회시집\n")
# 챕터 구분 페이지 헤더
CHAPTER_DIV = re.compile(r"^제\d+장\n[가-힣\s]{1,20}\n")
# 소분류 헤더 (예: '1\n근로자\n')
SUBNUM_DIV  = re.compile(r"^\d+\n[가-힣\s]{2,30}\n")

# 질의가 끝나는 어미 패턴
QUESTION_ENDINGS = (
    "는지", "인지", "하는지", "있는지", "인가", "는가",
    "할지", "여부", "인지?", "는지?", "할까요", "나요",
)


# ──────────────────────────────────────────────
# 2. 유틸 함수
# ──────────────────────────────────────────────

def get_chapter(page_num: int) -> tuple[int, str]:
    """페이지 번호 → (챕터 번호, 챕터명)"""
    for i in range(len(CHAPTER_MAP) - 1):
        if CHAPTER_MAP[i][0] <= page_num < CHAPTER_MAP[i + 1][0]:
            return CHAPTER_MAP[i][1], CHAPTER_MAP[i][2]
    return CHAPTER_MAP[-2][1], CHAPTER_MAP[-2][2]


def strip_page_header(text: str) -> str:
    """페이지 상단 반복 헤더 제거"""
    text = ODD_HEADER.sub("", text, count=1)
    text = EVEN_HEADER.sub("", text, count=1)
    text = CHAPTER_DIV.sub("", text, count=1)
    text = SUBNUM_DIV.sub("", text, count=1)
    return text.strip()


def is_title_line(line: str) -> bool:
    """
    이 PDF에서 제목(소제목)은 PDF 내부적으로 \x01을 단어 구분자로 사용.
    일반 본문에는 \x01이 없으므로, \x01 포함 여부로 제목 라인을 식별.
    """
    return "\x01" in line and len(line.replace("\x01", " ").strip()) > 3


def clean_title(line: str) -> str:
    """제목 라인 정규화"""
    return re.sub(r"\s+", " ", line.replace("\x01", " ")).strip()


def extract_title_keywords(title: str) -> str:
    """
    제목에서 핵심 키워드 추출 (불용어 제거).
    메타데이터 필터링 및 검색 보조에 활용.
    """
    stopwords = {"여부", "관련", "경우", "대한", "에서", "있는", "하는", "으로", "에"}
    words = title.split()
    keywords = [w for w in words if w not in stopwords and len(w) > 1]
    return " ".join(keywords)


def split_question_answer(block_lines: list[str]) -> tuple[str, str]:
    """
    제목 라인 이후의 텍스트를 질의 / 회시로 분리.

    분리 기준:
    1. 질의 어미 (는지, 인지, 여부 등)로 끝나는 줄이 나오면 → 질의 종료
    2. 줄 길이가 85자 초과하고 질의 어미 없음 → 회시 시작 신호
    3. 공백 라인 후 질의가 1줄 이상 쌓였으면 → 회시 전환
    4. 최대 6줄까지만 질의로 허용
    """
    q_lines: list[str] = []
    a_lines: list[str] = []
    in_q = True
    q_count = 0

    for line in block_lines:
        s = line.strip()

        # 빈 라인 처리
        if not s:
            if in_q and q_count > 0:
                in_q = False
            if not in_q:
                a_lines.append(line)
            continue

        if in_q:
            ends_question = any(s.endswith(e) for e in QUESTION_ENDINGS)
            is_long_line  = len(s) > 85

            q_lines.append(s)
            q_count += 1

            if ends_question:
                in_q = False  # 자연스러운 질의 종료
            elif is_long_line and not ends_question and q_count >= 1:
                # 너무 긴 줄 → 회시 본문으로 이동
                a_lines.append(q_lines.pop())
                in_q = False
            elif q_count >= 6:
                in_q = False
        else:
            a_lines.append(line)

    question = " ".join(q_lines).strip()
    answer   = "\n".join(a_lines).strip()
    return question, answer


# ──────────────────────────────────────────────
# 3. PDF 파싱 메인 로직
# ──────────────────────────────────────────────

def parse_pdf(pdf_path: Path) -> list[dict]:
    """
    PDF에서 질의회시 항목을 파싱하여 딕셔너리 리스트 반환.

    각 딕셔너리:
        title          : 항목 제목 (예: "사회복무요원의 근로자성 여부")
        question       : 질의 본문
        answer         : 회시 본문 (전체)
        chapter_num    : 챕터 번호 (int)
        chapter_name   : 챕터명
        reference      : 행정해석 문서번호 (예: "근로기준정책과-1384, 2021.5.11.")
        ref_date       : 발령일 (YYYY-MM-DD)
        start_page     : PDF 시작 페이지 번호
        source         : 출처 문서명
        title_keywords : 제목 핵심 키워드
    """
    doc = fitz.open(str(pdf_path))
    
    # ① 페이지 텍스트 수집 (콘텐츠 시작 페이지부터)
    pages_text: dict[int, str] = {}
    for i in range(24, min(len(doc), 615)):
        text = doc[i].get_text("text").strip()
        if text:
            pages_text[i + 1] = text  # 1-indexed

    # ② 페이지를 항목 단위로 그룹핑
    #    제목 라인(\x01 포함)이 페이지 첫 줄에 나타나면 새 항목 시작
    entries: list[tuple[int, str]] = []
    current_pages: list[str] = []
    current_start: Optional[int] = None

    for pg in sorted(pages_text.keys()):
        cleaned = strip_page_header(pages_text[pg])
        lines   = cleaned.split("\n")

        if lines and is_title_line(lines[0]):
            # 이전 항목 저장
            if current_pages and current_start:
                entries.append((current_start, "\n".join(current_pages)))
            current_pages = [cleaned]
            current_start = pg
        else:
            if current_start:
                current_pages.append(cleaned)

    if current_pages and current_start:
        entries.append((current_start, "\n".join(current_pages)))

    # ③ 항목별 세부 파싱
    parsed: list[dict] = []

    for start_pg, block in entries:
        lines = block.split("\n")

        # 제목 라인 탐색
        title_idx = next(
            (i for i, l in enumerate(lines) if is_title_line(l)), None
        )
        if title_idx is None:
            continue

        title      = clean_title(lines[title_idx])
        body_lines = lines[title_idx + 1:]

        # 행정해석 번호 추출 (마지막 = 최종 회시 번호)
        refs    = REF_PATTERN.findall(block)
        ref_str = refs[-1] if refs else ""

        # 발령일 파싱
        date_m  = re.search(r"(\d{4})\.(\d{1,2})\.(\d{1,2})", ref_str)
        ref_date = (
            f"{date_m.group(1)}-{date_m.group(2).zfill(2)}-{date_m.group(3).zfill(2)}"
            if date_m else ""
        )

        question, answer = split_question_answer(body_lines)
        ch_num, ch_name  = get_chapter(start_pg)

        parsed.append({
            "title"         : title,
            "question"      : question,
            "answer"        : answer,
            "chapter_num"   : ch_num,
            "chapter_name"  : ch_name,
            "reference"     : ref_str,
            "ref_date"      : ref_date,
            "start_page"    : start_pg,
            "source"        : "근로기준법 질의회시집 2018.4~2023.6",
            "title_keywords": extract_title_keywords(title),
        })

    doc.close()
    return parsed


# ──────────────────────────────────────────────
# 4. LangChain Document 변환
# ──────────────────────────────────────────────

def to_langchain_documents(parsed: list[dict]) -> list[Document]:
    """
    파싱 결과 → LangChain Document 변환.

    page_content = "질의: {question}"   ← 임베딩 대상
    metadata     = 나머지 모든 필드     ← 검색 후 꺼내 쓰는 회시/메타 정보
    """
    docs: list[Document] = []

    for item in parsed:
        # 질의가 비어있으면 제목으로 대체 (폴백)
        question_text = item["question"] if item["question"] else item["title"]

        page_content = f"질의: {question_text}"

        metadata = {
            "title"         : item["title"],
            "answer"        : item["answer"],          # 회시 전문
            "chapter_num"   : item["chapter_num"],
            "chapter_name"  : item["chapter_name"],
            "reference"     : item["reference"],
            "ref_date"      : item["ref_date"],
            "start_page"    : item["start_page"],
            "source"        : item["source"],
            "title_keywords": item["title_keywords"],
        }

        docs.append(Document(page_content=page_content, metadata=metadata))

    return docs


# ──────────────────────────────────────────────
# 5. 메인 실행
# ──────────────────────────────────────────────

def load_qna_documents(pdf_path: Path = PDF_PATH) -> list[Document]:
    """
    외부에서 import하여 사용하는 진입점.

    Usage:
        from preprocess_qna import load_qna_documents
        docs = load_qna_documents(Path("근로기준법_질의회시집_2018_4__2023_6__.pdf"))
    """
    parsed = parse_pdf(pdf_path)
    return to_langchain_documents(parsed)



# ============================================================
# QnA 실행
# ============================================================
def run_qna(input_dir: str, output_dir: str):
    from pathlib import Path
    import json
    from collections import Counter

    pdf_dir = Path(input_dir)
    pdf_files = sorted(pdf_dir.glob("*.pdf"))

    all_docs = []

    for pdf_path in pdf_files:
        parsed = parse_pdf(pdf_path)
        docs = to_langchain_documents(parsed)

        for d in docs:
            d.metadata["source_file"] = pdf_path.name

        all_docs.extend(docs)

    print(f"총 문서 수: {len(all_docs)}")

    # 저장
    out_path = Path(output_dir) / "qna.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)

    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(
            [{"page_content": d.page_content, "metadata": d.metadata} for d in all_docs],
            f,
            ensure_ascii=False,
            indent=2
        )

    print(f"QnA 저장 완료: {out_path}")
