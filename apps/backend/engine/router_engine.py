"""
engine/router_engine.py

홈 입력을 4개 모드 중 하나로 분류한 뒤, 해당 로직을 실행합니다.

모드
1) case_based_answer: 유사 법률/판례 추출 + 최종 답변 생성 (graph_answer)
2) procedure_guidance: 대응 절차 안내만 생성 (graph_procedure)
3) allowance_calculator: 수당 계산 (CalculatorEngine)
4) latest_news: 최신 노동법/판결 뉴스 검색 (NewsSearchTool / NewsEngine)
"""

from __future__ import annotations

from dataclasses import dataclass

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

    def route(self, question: str) -> str:
        if self._is_explicit_procedure_request(question):
            print(f"\n[라우터 판단 결과] '{ROUTE_PROCEDURE_GUIDANCE}' (rule)\n", flush=True)
            return ROUTE_PROCEDURE_GUIDANCE

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

    def run(self, question: str) -> RouterResult:
        mode = self.route(question)

        if mode == ROUTE_CASE_BASED_ANSWER:
            state = graph_answer.invoke({"question": question})
            return RouterResult(mode=mode, content=state.get("final_answer", ""))

        if mode == ROUTE_PROCEDURE_GUIDANCE:
            state = graph_procedure.invoke({"question": question})
            return RouterResult(mode=mode, content=state.get("procedure_guide", "skip"))

        if mode == ROUTE_ALLOWANCE_CALCULATOR:
            engine = CalculatorEngine()
            res = engine.calculate(question)
            return RouterResult(mode=mode, content=res.get("answer", ""))

        # 🌟 latest_news 로직 추가
        if mode == ROUTE_LATEST_NEWS:
            # 1. 만약 통합된 NewsEngine 객체(프론트엔드에서 사용 중인 객체)가 있다면 그것을 사용하도록 연결 가능.
            # 2. 여기서는 올려주신 NewsSearchTool을 직접 호출하여 답변을 구성합니다.
            from engine.tools.news_search_tool import NewsSearchTool
            tool = NewsSearchTool()
            res = tool.run(query=question, display=5)

            if not res.success or not res.data.get("results"):
                content = "⚠️ 관련 최신 뉴스를 찾을 수 없습니다. 다른 검색어를 입력해 보세요."
            else:
                items = res.data["results"]
                content = "📰 **관련 최신 뉴스 검색 결과입니다.**\n\n"
                for i, item in enumerate(items, 1):
                    # HTML 이스케이프 및 날짜 정리된 데이터 사용
                    title = item.get("title", "제목 없음")
                    link = item.get("link", "#")
                    desc = item.get("description", "")
                    content += f"**{i}. [{title}]({link})**\n> {desc}...\n\n"

            return RouterResult(mode=mode, content=content)

router_engine = LawRouterEngine()
