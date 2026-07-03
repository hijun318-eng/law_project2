"""
LangGraph ReAct 계산기 그래프

create_react_agent를 사용하여 자연어 → 파라미터 추출 → 도구 호출 → 결과 반환

참고: 각 도구의 상세 파라미터 설명은 tool docstring에 정의되어 있으며,
create_react_agent가 자동으로 LLM에 전달합니다.
"""
from langgraph.prebuilt import create_react_agent
from engine.config import llm
from engine.calculator.tools import CALCULATOR_TOOLS
from engine.utils.prompt_loader import load_prompt

SYSTEM_PROMPT = load_prompt("calculator_prompt.md")

graph = create_react_agent(
    model=llm,
    tools=CALCULATOR_TOOLS,
    prompt=SYSTEM_PROMPT,
)
