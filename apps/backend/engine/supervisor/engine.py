"""
SupervisorEngine — RAGEngine과 동일한 stream_answer 인터페이스 제공

프론트엔드(qa.py)에서 engine.stream_answer(question)을 호출하면
SupervisorGraph가 복합 질문에 대해 여러 서브 에이전트를 순차 실행하고
그 결과를 스트리밍 형태로 전달합니다.
"""
from engine.utils.execution_logger import init_logger, get_logger, clear_logger
from engine.supervisor.graph import (
    supervisor_graph,
    NODE_LABELS,
)


class SupervisorEngine:
    """
    Supervisor 기반 법률 분석 엔진

    RAGEngine과 동일한 .stream_answer() 시그니처를 제공하여
    프론트엔드 변경 없이 Supervisor로 교체 가능하게 함
    """

    def __init__(self):
        self.graph = supervisor_graph

    def stream_answer(self, question: str):
        logger_created = False
        if get_logger() is None:
            init_logger(question)
            logger_created = True

        state = {
            "question": question,
            "messages": [],
            "next": "supervisor",
            "intermediate_results": {},
            "final_answer": "",
            "iteration": 0,
            "error": "",
            "rag_sources": [],
            "rag_procedure": "",
        }

        latest_state = dict(state)

        for event in self.graph.stream(state):
            for node_name, output in event.items():
                log = output.get("log", "")
                if log:
                    label = NODE_LABELS.get(node_name, node_name)
                    yield (node_name, label, log)
                latest_state.update(output)

        answer = self._build_final_answer(latest_state)
        sources = latest_state.get("rag_sources", [])
        procedure = latest_state.get("rag_procedure", "")

        logger = get_logger()
        if logger_created and logger:
            logger.finish(answer)
            logger.save()
            clear_logger()

        yield ("done", "✅ 분석 완료", {
            "answer": answer,
            "procedure": procedure,
            "sources": sources,
        })

    def answer(self, question: str) -> dict:
        logger_created = False
        if get_logger() is None:
            init_logger(question)
            logger_created = True

        result = self.graph.invoke({
            "question": question,
            "messages": [],
            "next": "supervisor",
            "intermediate_results": {},
            "final_answer": "",
            "iteration": 0,
            "error": "",
            "rag_sources": [],
            "rag_procedure": "",
        })
        answer_text = self._build_final_answer(result)
        sources = result.get("rag_sources", [])
        procedure = result.get("rag_procedure", "")

        logger = get_logger()
        if logger_created and logger:
            logger.finish(answer_text)
            logger.save()
            clear_logger()

        return {"answer": answer_text, "procedure": procedure, "sources": sources, "mode": "supervisor"}

    @staticmethod
    def _build_final_answer(state: dict) -> str:
        """각 에이전트 결과를 하나의 최종 답변으로 통합"""
        intermediate = state.get("intermediate_results", {})
        rag = intermediate.get("rag", "")
        calc = intermediate.get("calculator", "")
        news = intermediate.get("news", "")

        # RAG 답변이 메인 — 계산 결과가 포함되어 있음
        if rag:
            answer = rag
            # 뉴스 결과가 RAG 답변에 포함되지 않은 것으로 보이면 추가
            if news and ("최신 뉴스" not in rag[:200] if len(rag) > 200 else True):
                answer += f"\n\n---\n\n{news}"
            return answer

        # RAG 없이 계산만
        if calc:
            answer = f"🧮 **계산 결과**\n\n{calc}"
            if news:
                answer += f"\n\n---\n\n{news}"
            return answer

        # 뉴스만
        if news:
            return news

        return "질문을 분석할 수 없습니다. 다시 입력해주세요."
