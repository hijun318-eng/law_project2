"""
engine/router_engine.py

법률 RAG 하위 질문을 3개 모드 중 하나로 분류한 뒤, 해당 로직을 실행합니다.
(수당 계산/최신 뉴스는 Supervisor가 별도의 전담 노드로 직접 처리하므로
 이 라우터의 책임 범위가 아닙니다.)

모드
1) case_based_answer: 유사 법률/판례 추출 + 최종 답변 생성 (graph_answer)
2) case_with_procedure: 사례 판단 + 대응 절차 안내 (graph)
3) procedure_guidance: 대응 절차 안내만 생성 (graph_procedure)
"""

from __future__ import annotations

from dataclasses import dataclass, field

from engine.config import llm
from engine.graph import graph, graph_answer, graph_procedure
from engine.utils.sources import format_sources

from langchain_core.messages import HumanMessage, SystemMessage

ROUTE_CASE_BASED_ANSWER = "case_based_answer"
ROUTE_CASE_WITH_PROCEDURE = "case_with_procedure"
ROUTE_PROCEDURE_GUIDANCE = "procedure_guidance"

VALID_ROUTES = {ROUTE_CASE_BASED_ANSWER, ROUTE_CASE_WITH_PROCEDURE, ROUTE_PROCEDURE_GUIDANCE}


SYSTEM_PROMPT = """
너는 노동법률 AI 라우터야.
사용자의 질문을 분석하여 아래 3개의 노드 ID 중 가장 적합한 것 딱 1개만 반환해.

[노드 목록 및 판단 기준]
1. case_based_answer
   - 본인의 상황을 설명하며 "이게 불법인가요?", "비슷한 사례나 판례가 있나요?" 등 **법리적 해석이나 유사 사례 검토**만 필요한 경우 (절차 문의는 없음).

2. case_with_procedure
   - 본인의 상황을 설명하면서 동시에 "대응 절차", "신고 방법", "어떻게 대응해야 하나요" 등 **사례 판단과 절차 안내가 함께** 필요한 경우.
   - 예시: "부당해고 당한 것 같은데 대응 절차 알려줘", "임금체불인데 신고 방법도 알려줘"

3. procedure_guidance (순수 절차 문의)
   - 본인 상황에 대한 해석이나 판례 검토는 필요 없고, **오직 행정/대응 절차, 서류, 방법**만을 묻는 경우.
   - 예시: "노동청 진정서 제출 방법 알려줘", "임금체불 신고 어디서 해?", "실업급여 신청 서류가 뭐야?"

[출력 규칙]
- 부가적인 설명이나 마침표 없이, 오직 선택된 '노드 ID' 영문 텍스트 딱 하나만 출력해.
""".strip()


@dataclass
class RouterResult:
    mode: str
    content: str
    sources: list = field(default_factory=list)
    procedure: str = ""


class LawRouterEngine:
    def __init__(self):
        self._llm = llm

    @staticmethod
    def _is_explicit_procedure_request(question: str) -> bool:
        q = question.replace(" ", "").lower()
        procedure_keywords = (
            "대응절차",
            "대처절차",
            "진행절차",
            "구제절차",
            "절차알려",
            "절차를알려",
            "절차가뭐",
            "신고방법",
            "신청방법",
            "제출방법",
            "접수방법",
            "어디에신고",
            "어디다신고",
            "어디로신고",
            "구제신청",
            "진정서",
            "필요서류",
            "준비서류",
        )
        return any(keyword in q for keyword in procedure_keywords)

    @staticmethod
    def _has_case_context(question: str) -> bool:
        q = question.replace(" ", "").lower()
        case_keywords = (
            "사례",
            "상황",
            "내경우",
            "제경우",
            "이런경우",
            "이런상황",
            "회사에서",
            "사장이",
            "대표가",
            "상사가",
            "갑자기",
            "통보",
            "해고",
            "못받",
            "안줍",
            "안주",
            "일했는데",
            "했는데",
            "당했",
            "라고했",
            "라고합니다",
            "부당",
            "불법",
            "가능한가",
            "맞나요",
        )
        return any(keyword in q for keyword in case_keywords)

    def route(self, question: str) -> str:
        resp = self._llm.invoke(
            [
                SystemMessage(content=SYSTEM_PROMPT),
                HumanMessage(content=f"사용자 질문: {question}"),
            ]
        )
        mode_raw = getattr(resp, "content", "")
        if isinstance(mode_raw, str):
            mode = (mode_raw or "").strip().lower()
        else:
            mode = str(mode_raw).strip().lower()

        # 디버깅 로그
        print(f"\n[라우터 판단 결과] '{mode}' (llm)\n")

        if mode in VALID_ROUTES:
            return mode

        # LLM 응답이 유효한 노드 ID가 아닐 때만 키워드 규칙으로 폴백
        if self._is_explicit_procedure_request(question):
            if self._has_case_context(question):
                print(f"\n[라우터 판단 결과] '{ROUTE_CASE_WITH_PROCEDURE}' (fallback rule)\n", flush=True)
                return ROUTE_CASE_WITH_PROCEDURE
            print(f"\n[라우터 판단 결과] '{ROUTE_PROCEDURE_GUIDANCE}' (fallback rule)\n", flush=True)
            return ROUTE_PROCEDURE_GUIDANCE

        print(f"\n[라우터 판단 결과] '{ROUTE_CASE_BASED_ANSWER}' (fallback default)\n", flush=True)
        return ROUTE_CASE_BASED_ANSWER

    def run(self, question: str) -> RouterResult:
        mode = self.route(question)

        if mode == ROUTE_CASE_BASED_ANSWER:
            state = graph_answer.invoke({"question": question})
            return RouterResult(
                mode=mode,
                content=state.get("final_answer", ""),
                sources=format_sources(state),
            )

        if mode == ROUTE_CASE_WITH_PROCEDURE:
            state = graph.invoke({"question": question})
            answer = state.get("final_answer", "")
            procedure = state.get("procedure_guide", "")
            if procedure and procedure != "skip":
                answer = f"{answer}\n\n---\n\n## 대응 절차\n\n{procedure}"
            return RouterResult(
                mode=mode,
                content=answer,
                sources=format_sources(state),
                procedure=procedure,
            )

        # ROUTE_PROCEDURE_GUIDANCE
        state = graph_procedure.invoke({"question": question, "skip_rerank": True})
        return RouterResult(
            mode=mode,
            content=state.get("procedure_guide", "skip"),
            sources=format_sources(state),
            procedure=state.get("procedure_guide", ""),
        )


router_engine = LawRouterEngine()
