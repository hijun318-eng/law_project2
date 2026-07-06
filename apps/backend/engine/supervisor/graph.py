"""
Supervisor Graph — 복합 질문을 여러 서브 에이전트에 분배하는 상위 그래프

역할:
  - supervisor_node: LLM으로 다음 실행할 서브 에이전트 결정
  - rag_router_node: 법률/판례 RAG 실행
  - calculator_node: 수당/퇴직금 계산 실행
  - news_node: 최신 뉴스 검색 실행
  - router_decision: 조건부 엣지 (supervisor 결정에 따라 라우팅)

흐름:
  supervisor → (rag_router | calculator | news) → supervisor → ... → END
"""
from typing import TypedDict, Optional

from langgraph.graph import StateGraph, END
from langchain_core.messages import HumanMessage, SystemMessage

from engine.config import llm
from engine.router_engine import router_engine
from engine.calculator_engine import CalculatorEngine
from engine.tools.news_search_tool import NewsSearchTool
from engine.utils.execution_logger import log_node

# ── 상수 ────────────────────────────────────────────────────
MAX_ITERATIONS = 3

# Supervisor가 선택할 수 있는 서브 에이전트
VALID_AGENTS = frozenset({"rag_router", "calculator", "news", "FINISH"})

NODE_LABELS = {
    "supervisor":  "🤖 Supervisor",
    "rag_router":  "⚖️ 법률 RAG",
    "calculator":  "🧮 수당 계산기",
    "news":        "📰 최신 뉴스",
}

SUPERVISOR_SYSTEM_PROMPT = """당신은 노동법률 AI 시스템의 Supervisor입니다. 사용자의 질문을 분석하여 적절한 전담 에이전트를 선택하세요.

## 전담 에이전트 목록

1. rag_router — 법률/판례 검색 및 법적 답변 (LangGraph RAG)
   - 사용자의 구체적인 상황에 대한 법적 판단, 판례 검색, 법령 해석이 필요할 때
   - 예: "해고당했는데 부당해고인가요?", "임금체불 관련 판례 알려줘",
          "야근수당 안 줘요", "직장 내 괴롭힘 신고 방법" (법적 판단+절차 모두 포함)

2. calculator — 수당/퇴직금/주휴수당/최저임금 계산 (LangGraph ReAct)
   - 금액, 숫자 계산이 필요할 때
   - 예: "퇴직금 계산해줘", "주휴수당 얼마야?", "최저임금 위반인가요?"

3. news — 최신 노동법 뉴스/판결/정책 검색
   - 최신 트렌드, 시사 정보, 최근 판결이 필요할 때
   - 예: "최근 중대재해법 판례", "올해 최저임금 뉴스"

## 의사 결정 규칙
- 복합 질문(여러 작업이 필요한 질문)은 순차적으로 여러 에이전트를 실행하세요.
- 예: "퇴직금 계산하고 관련 판례도 알려줘" → calculator 먼저 실행 → rag_router 추가
- 예: "퇴직금 계산하고 최근 뉴스도 찾아줘" → calculator → news
- 한 번 실행한 에이전트는 다시 선택하지 마세요.
- 충분한 정보가 수집되었으면 FINISH를 선택하세요.
- 최대 3회까지만 에이전트를 실행할 수 있습니다.

## 응답 형식
반드시 아래 중 하나만 응답하세요 (따옴표 없이, 부가 설명 없이):
rag_router
calculator
news
FINISH"""


# ── State ────────────────────────────────────────────────────

class SupervisorState(TypedDict):
    """Supervisor 그래프의 상태"""
    question: str                                # 사용자 원본 질문
    messages: list                               # 대화 메시지 이력
    next: str                                    # Supervisor가 결정한 다음 노드
    intermediate_results: dict                   # 각 에이전트 실행 결과 {"rag": ..., "calculator": ..., "news": ...}
    final_answer: str                            # 최종 통합 답변
    iteration: int                               # 현재까지 실행된 에이전트 수 (MAX_ITERATIONS 제한)
    error: str                                   # 에러 메시지
    rag_sources: list                            # RAG 소스 문서 정보 (frontend 표시용)
    rag_procedure: str


# ── Node 함수 ────────────────────────────────────────────────

@log_node
def supervisor_node(state: SupervisorState) -> dict:
    """
    Supervisor LLM 노드 — 현재 상태를 분석하여 다음 실행할 에이전트 결정
    """
    intermediate = state.get("intermediate_results", {})
    iteration = state.get("iteration", 0)

    # 최대 반복 초과 시 강제 종료
    if iteration >= MAX_ITERATIONS:
        return {"next": "FINISH", "log": "최대 실행 횟수 도달"}

    # 이미 실행된 에이전트 정리
    already_done = [k for k in ("rag", "calculator", "news") if intermediate.get(k)]
    done_summary = ", ".join(already_done) if already_done else "없음"

    # 컨텍스트 구성
    intermediate_summary_lines = []
    if intermediate.get("rag"):
        intermediate_summary_lines.append("- rag_router: 법률 답변 생성 완료")
    if intermediate.get("calculator"):
        intermediate_summary_lines.append("- calculator: 계산 완료")
    if intermediate.get("news"):
        intermediate_summary_lines.append("- news: 뉴스 검색 완료")

    context = (
        f"\n[이전 실행 결과]\n"
        f"{chr(10).join(intermediate_summary_lines) if intermediate_summary_lines else '아직 실행된 에이전트 없음'}\n"
        f"[이미 실행 완료된 에이전트 (재선택 금지)]\n"
        f"{done_summary}\n\n"
        f"다음 실행할 에이전트:"
    )

    messages = [
        SystemMessage(content=SUPERVISOR_SYSTEM_PROMPT + context),
        HumanMessage(content=f"사용자 질문: {state['question']}"),
    ]

    resp = llm.invoke(messages)
    raw = resp.content.strip().lower().replace('"', "").replace("'", "").replace(".", "").strip()

    # 응답 파싱 — 포함된 키워드로 판단
    next_agent = "FINISH"  # 기본값

    if "rag" in raw or "법률" in raw:
        if "rag" not in already_done:
            next_agent = "rag_router"
    elif "calc" in raw or "계산" in raw:
        if "calculator" not in already_done:
            next_agent = "calculator"
    elif "news" in raw or "뉴스" in raw:
        if "news" not in already_done:
            next_agent = "news"

    # 중복 방지: 이미 실행된 에이전트는 FINISH 처리
    if next_agent != "FINISH":
        agent_key = {"rag_router": "rag", "calculator": "calculator", "news": "news"}.get(next_agent)
        if agent_key in already_done:
            next_agent = "FINISH"

    log_map = {
        "rag_router": "법률 정보 검색 및 답변 생성 필요",
        "calculator": "금액 계산 필요",
        "news": "최신 뉴스 검색 필요",
        "FINISH": "모든 정보 수집 완료",
    }

    return {"next": next_agent, "log": log_map.get(next_agent, "")}


@log_node
def rag_router_node(state: SupervisorState) -> dict:
    """RAG 엔진 실행 — 법률/판례 검색 및 답변 생성"""
    question = state["question"]

    # 이전에 계산 결과가 있으면 질문에 포함시켜 RAG가 활용하게 함
    calc_result = state.get("intermediate_results", {}).get("calculator", "")
    if calc_result:
        question = (
            f"[참고: 이전 계산 결과]\n"
            f"{calc_result}\n\n"
            f"[원본 질문]\n"
            f"{question}\n\n"
            f"위 계산 결과를 참고하여 법률 답변을 생성해주세요."
        )

    result = router_engine.run(question)
    return {
        "intermediate_results": {
            **state.get("intermediate_results", {}),
            "rag": result.content,
        },
        "rag_sources": [],
        "log": "법률 답변 생성 완료",
        "iteration": state.get("iteration", 0) + 1,
        "rag_procedure": "",
    }


@log_node
def calculator_node(state: SupervisorState) -> dict:
    """계산기 엔진 실행 — 수당/퇴직금 계산"""
    engine = CalculatorEngine()
    result = engine.calculate(state["question"])

    return {
        "intermediate_results": {
            **state.get("intermediate_results", {}),
            "calculator": result.get("answer", ""),
        },
        "log": "계산 완료",
        "iteration": state.get("iteration", 0) + 1,
    }


@log_node
def news_node(state: SupervisorState) -> dict:
    """뉴스 검색 실행 — 최신 노동법 뉴스/판결 검색"""
    tool = NewsSearchTool()
    res = tool.run(query=state["question"], display=5)

    if res.success and res.data.get("results"):
        items = res.data["results"]
        content = "📰 **관련 최신 뉴스 검색 결과입니다.**\n\n"
        for i, item in enumerate(items, 1):
            title = item.get("title", "제목 없음")
            link = item.get("link", "#")
            desc = item.get("description", "")
            content += f"**{i}. [{title}]({link})**\n> {desc}...\n\n"
    else:
        content = "⚠️ 관련 최신 뉴스를 찾을 수 없습니다."

    return {
        "intermediate_results": {
            **state.get("intermediate_results", {}),
            "news": content,
        },
        "log": "뉴스 검색 완료",
        "iteration": state.get("iteration", 0) + 1,
    }


def router_decision(state: SupervisorState) -> str:
    """
    조건부 엣지 — supervisor_node가 결정한 next 값을 기반으로 라우팅
    MAX_ITERATIONS 초과 시 강제 FINISH
    """
    if state.get("iteration", 0) >= MAX_ITERATIONS:
        return "FINISH"
    return state.get("next", "FINISH")


# ── 그래프 빌드 ──────────────────────────────────────────────

def _build_graph() -> StateGraph:
    builder = StateGraph(SupervisorState)

    # 노드 등록
    builder.add_node("supervisor",  supervisor_node)
    builder.add_node("rag_router",  rag_router_node)
    builder.add_node("calculator",  calculator_node)
    builder.add_node("news",        news_node)

    # 진입점
    builder.set_entry_point("supervisor")

    # 조건부 엣지 — supervisor가 결정한 대로 라우팅
    builder.add_conditional_edges(
        "supervisor",
        router_decision,
        {
            "rag_router": "rag_router",
            "calculator": "calculator",
            "news": "news",
            "FINISH": END,
        },
    )

    # 각 서브 에이전트 완료 후 supervisor로 복귀 (다음 결정)
    builder.add_edge("rag_router", "supervisor")
    builder.add_edge("calculator", "supervisor")
    builder.add_edge("news", "supervisor")

    return builder.compile()


supervisor_graph = _build_graph()
