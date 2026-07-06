"""
engine/router_engine.py

홈 입력을 4개 모드 중 하나로 분류한 뒤, 해당 로직을 실행합니다.

모드
1) case_based_answer: 유사 법률/판례 추출 + 최종 답변 생성 (graph_answer)
2) procedure_guidance: 대응 절차 안내만 생성 (graph_procedure)
3) allowance_calculator: 수당 계산 (CalculatorEngine)
4) latest_news: 최신 노동법/판결 뉴스 검색 (NewsEngine)
"""

from __future__ import annotations

from dataclasses import dataclass, field

from engine.config import llm
from engine.calculator_engine import CalculatorEngine
from engine.graph import graph_answer, graph_procedure

from langchain_core.messages import HumanMessage, SystemMessage

ROUTE_CASE_BASED_ANSWER = "case_based_answer"
ROUTE_PROCEDURE_GUIDANCE = "procedure_guidance"
ROUTE_ALLOWANCE_CALCULATOR = "allowance_calculator"
# 🌟 최신 뉴스 검색 모드 추가
ROUTE_LATEST_NEWS = "latest_news"


SYSTEM_PROMPT = """
너는 노동법률 AI 라우터야. 
사용자의 질문을 분석하여 아래 4개의 노드 ID 중 가장 적합한 것 딱 1개만 반환해.

[노드 목록 및 판단 기준]
1. case_based_answer (최우선 방어)
   - 본인의 상황을 설명하며 "이게 불법인가요?", "비슷한 사례나 판례가 있나요?" 등 **법리적 해석이나 유사 사례 검토**가 필요한 경우.
   - 🚨 중요: "이런 상황인데 대응 절차 알려줘"처럼 **상황 판단과 절차를 동시에 묻는 질문**은 무조건 'case_based_answer'로 분류해. (사례 파악이 먼저 선행되어야 함)

2. procedure_guidance (순수 절차 문의)
   - 내 상황에 대한 해석이나 판례 검토는 필요 없고, **오직 행정/대응 절차, 서류, 방법**만을 묻는 경우.
   - 예시: "노동청 진정서 제출 방법 알려줘", "임금체불 신고 어디서 해?", "실업급여 신청 서류가 뭐야?"

3. allowance_calculator
   - 주휴수당, 연차수당, 해고예고수당, 퇴직금 등 구체적인 **금액 계산**을 요구하는 경우.

4. latest_news (최신 동향 및 뉴스 검색)
   - 노동법 개정, 최근 판결, 최저임금, 정책 등 **최신 뉴스나 사회적 이슈**를 묻는 경우.
   - 예시: "최근 중대재해처벌법 판례 찾아줘", "올해 최저임금 관련 뉴스 있어?", "요즘 직장내 괴롭힘 뉴스 알려줘"

[출력 규칙]
- 질문에 '절차', '방법'이라는 단어가 있더라도, 본인의 억울한 사연이나 구체적 정황을 설명하며 묻는다면 무조건 'case_based_answer'로 빼야 해.
- 부가적인 설명이나 마침표 없이, 오직 선택된 '노드 ID' 영문 텍스트 딱 하나만 출력해.
""".strip()


@dataclass
class RouterResult:
    mode: str
    content: str
    category: str = ""
    sources: list = field(default_factory=list)


class LawRouterEngine:
    def __init__(self):
        self._llm = llm

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
        print(f"\n[라우터 판단 결과] '{mode}'\n")

        if mode in {
            ROUTE_CASE_BASED_ANSWER,
            ROUTE_PROCEDURE_GUIDANCE,
            ROUTE_ALLOWANCE_CALCULATOR,
            ROUTE_LATEST_NEWS,  # 허용 목록에 추가
        }:
            return mode
        return ROUTE_CASE_BASED_ANSWER

    @staticmethod
    def _extract_category(state: dict) -> str:
        """GraphState에서 precedent_context_docs의 category를 추출합니다."""
        docs = state.get("precedent_context_docs", [])
        if not docs:
            return ""
        doc = docs[0]
        if not hasattr(doc, "metadata"):
            return ""
        return doc.metadata.get("category", "")

    @staticmethod
    def _extract_sources(state: dict) -> list:
        """GraphState에서 답변 생성에 참고한 법령 원문(law_analysis)을 추출합니다."""
        return state.get("law_analysis", [])

    def run(self, question: str, session_id: str | None = None) -> RouterResult:
        mode = self.route(question)

        # LangGraph 실행 모드(case_based_answer, procedure_guidance)에서만 logger 초기화
        langgraph_modes = (ROUTE_CASE_BASED_ANSWER, ROUTE_PROCEDURE_GUIDANCE)
        if mode in langgraph_modes:
            from engine.utils.execution_logger import init_logger
            init_logger(question, session_id=session_id)

        result = RouterResult(mode=mode, content="")  # fallback (예외 발생 시 finally에서 사용)
        try:
            if mode == ROUTE_CASE_BASED_ANSWER:
                state = graph_answer.invoke({"question": question})
                category = self._extract_category(state)
                sources = self._extract_sources(state)
                result = RouterResult(mode=mode, content=state.get("final_answer", ""), category=category, sources=sources)

            elif mode == ROUTE_PROCEDURE_GUIDANCE:
                state = graph_procedure.invoke({"question": question})
                category = self._extract_category(state)
                sources = self._extract_sources(state)
                result = RouterResult(mode=mode, content=state.get("procedure_guide", "skip"), category=category, sources=sources)

            elif mode == ROUTE_ALLOWANCE_CALCULATOR:
                engine = CalculatorEngine()
                res = engine.calculate(question)
                result = RouterResult(mode=mode, content=res.get("answer", ""))

            elif mode == ROUTE_LATEST_NEWS:
                from engine.news_engine import NewsEngine
                news_engine = NewsEngine(self._llm)
                res = news_engine.answer(question)
                result = RouterResult(mode=mode, content=res.get("answer", ""))

            return result
        finally:
            from engine.utils.execution_logger import get_logger, clear_logger
            logger = get_logger()
            if logger:
                answer = result.content
                logger.finish(answer)
                logger.save_db()
                logger.save()
                clear_logger()

router_engine = LawRouterEngine()
