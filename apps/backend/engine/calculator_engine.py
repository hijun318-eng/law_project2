"""
CalculatorEngine — LangGraph ReAct 기반 계산기 엔진

사용법:
    from engine.calculator_engine import CalculatorEngine
    engine = CalculatorEngine()
    result = engine.calculate("퇴직금 계산해줘, 3년 근무, 월 300만원")
    print(result["answer"])
"""
from typing import Optional
from langchain_core.messages import HumanMessage, AIMessage, BaseMessage
from engine.calculator.graph import graph


class CalculatorEngine:
    """계산기 ReAct 엔진 (LangGraph ReAct 기반)"""

    def __init__(self):
        self.graph = graph

    def calculate(
        self, query: str, conversation_history: Optional[list] = None
    ) -> dict:
        """
        자연어 질문에 대한 계산을 수행합니다.
        이전 대화 기록을 함께 전달하여 ReAct 에이전트가 이미 수집한 파라미터를
        재사용할 수 있도록 합니다.

        Args:
            query: 자연어 질문 (예: "퇴직금 계산해줘, 3년 근무, 월 300만원")
            conversation_history: 이전 대화 메시지 목록 (선택)
                [{"role": "user"/"assistant", "content": str}, ...]

        Returns:
            {"answer": str} — 계산 결과 문자열
        """
        # 이전 대화 기록을 LangChain 메시지로 변환
        messages: list[BaseMessage] = []
        if conversation_history:
            for msg in conversation_history:
                if msg["role"] == "user":
                    messages.append(HumanMessage(content=msg["content"]))
                elif msg["role"] == "assistant":
                    messages.append(AIMessage(content=msg["content"]))

        # 현재 질문 추가 (기록에 없는 경우에만)
        if not messages or not (
            isinstance(messages[-1], HumanMessage) and messages[-1].content == query
        ):
            messages.append(HumanMessage(content=query))

        result = self.graph.invoke({"messages": messages})

        # 마지막 AIMessage (tool_call 제외) 찾기 — isinstance 사용
        for msg in reversed(result["messages"]):
            if isinstance(msg, AIMessage) and not msg.tool_calls:
                content = msg.content
                if isinstance(content, str) and content.strip():
                    return {"answer": content}

        return {"answer": "죄송합니다. 계산 결과를 생성하지 못했습니다."}
