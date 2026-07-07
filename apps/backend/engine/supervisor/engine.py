"""
SupervisorEngine — RAGEngine과 동일한 stream_answer 인터페이스 제공

프론트엔드(qa.py)에서 engine.stream_answer(question)을 호출하면
SupervisorGraph가 복합 질문에 대해 여러 서브 에이전트를 순차 실행하고
그 결과를 스트리밍 형태로 전달합니다.
"""
import contextvars
import queue
import threading

from engine.utils.execution_logger import (
    init_logger, get_logger, clear_logger,
    set_progress_callback, clear_progress_callback,
)
from engine.supervisor.graph import (
    supervisor_graph,
    NODE_LABELS,
)
from engine.rag_engine import NODE_LABELS as RAG_NODE_LABELS

# rag_router 노드는 내부적으로 router_engine.run()을 동기 호출로 실행하는데,
# 그 안에서 도는 retrieve_precedent/retrieve_law/generate_answer 등도 @log_node가 적용되어 있어
# 아래 라벨을 함께 합쳐두면 supervisor 그래프 바깥의 하위 노드까지 동일한 방식으로 표시할 수 있다.
ALL_NODE_LABELS = {**NODE_LABELS, **RAG_NODE_LABELS}

_SENTINEL = object()


class SupervisorEngine:
    """
    Supervisor 기반 법률 분석 엔진

    RAGEngine과 동일한 .stream_answer() 시그니처를 제공하여
    프론트엔드 변경 없이 Supervisor로 교체 가능하게 함
    """

    def __init__(self):
        self.graph = supervisor_graph

    def _initial_state(self, question: str) -> dict:
        return {
            "question": question,
            "messages": [],
            "next": "supervisor",
            "intermediate_results": {},
            "final_answer": "",
            "iteration": 0,
            "error": "",
            "rag_sources": [],
            "rag_precedents": [],
            "rag_category": "",
            "rag_procedure": "",
            "rag_mode": "",
            "review_count": 0,
        }

    def stream_answer(self, question: str):
        """
        LangGraph의 .stream()은 supervisor 그래프의 최상위 노드(supervisor/rag_router/
        calculator/news/quality_review)가 끝날 때만 갱신을 내보낸다. 문제는 rag_router
        노드 하나가 내부적으로 router_engine.run()을 블로킹 호출해 판례검색→법령검색→
        답변생성을 수 초~수십 초에 걸쳐 순차 실행하는데, 이 구간은 supervisor 그래프 입장에서
        "노드 1개 실행 중"으로만 보여 진행상황이 그 사이엔 갱신되지 않는다는 점이다.

        이를 해결하기 위해 실제 그래프 실행은 백그라운드 스레드에서 .invoke()로 수행하고,
        (모든 노드 함수를 감싸는) @log_node 데코레이터가 노드 시작/종료마다 호출하는
        progress 콜백을 contextvars로 스레드에 전달해, 중첩된 하위 그래프의 노드까지
        포함한 모든 노드의 시작/종료를 큐를 통해 실시간으로 넘겨받는다.
        """
        logger_created = False
        if get_logger() is None:
            init_logger(question)
            logger_created = True

        state = self._initial_state(question)
        latest_state: dict = {}
        progress_queue: "queue.Queue" = queue.Queue()
        error_holder: dict = {}

        def on_progress(node_name, phase, log, elapsed):
            label = ALL_NODE_LABELS.get(node_name, node_name)
            progress_queue.put((node_name, phase, label, log, elapsed))

        def run_graph():
            set_progress_callback(on_progress)
            try:
                latest_state.update(self.graph.invoke(state))
            except Exception as e:
                error_holder["exc"] = e
            finally:
                clear_progress_callback()
                progress_queue.put(_SENTINEL)

        # contextvars(logger/progress callback 등)를 스레드로 그대로 전달하기 위해
        # 현재 컨텍스트를 복사해 스레드 안에서 실행한다.
        ctx = contextvars.copy_context()
        thread = threading.Thread(target=lambda: ctx.run(run_graph), daemon=True)
        thread.start()

        while True:
            item = progress_queue.get()
            if item is _SENTINEL:
                break
            node_name, phase, label, log, elapsed = item
            yield ("progress", node_name, phase, label, log, elapsed)

        thread.join()

        if "exc" in error_holder:
            raise error_holder["exc"]

        answer = self._build_final_answer(latest_state)
        sources = latest_state.get("rag_sources", [])
        precedents = latest_state.get("rag_precedents", [])
        category = latest_state.get("rag_category", "")
        procedure = latest_state.get("rag_procedure", "")
        mode = self._determine_route_mode(latest_state)

        logger = get_logger()
        if logger_created and logger:
            logger.finish(answer)
            logger.save()
            clear_logger()

        yield ("done", {
            "answer": answer,
            "procedure": procedure,
            "sources": sources,
            "precedents": precedents,
            "category": category,
            "mode": mode,
        })

    def answer(self, question: str) -> dict:
        logger_created = False
        if get_logger() is None:
            init_logger(question)
            logger_created = True

        result = self.graph.invoke(self._initial_state(question))
        answer_text = self._build_final_answer(result)
        sources = result.get("rag_sources", [])
        precedents = result.get("rag_precedents", [])
        category = result.get("rag_category", "")
        procedure = result.get("rag_procedure", "")
        mode = self._determine_route_mode(result)

        logger = get_logger()
        if logger_created and logger:
            logger.finish(answer_text)
            logger.save()
            clear_logger()

        return {
            "answer": answer_text,
            "procedure": procedure,
            "sources": sources,
            "precedents": precedents,
            "category": category,
            "mode": mode,
        }

    @staticmethod
    def _determine_route_mode(state: dict) -> str:
        """실행된 서브 에이전트를 바탕으로 ChatHistory.mode에 기록할 세부 모드를 결정.
        rag_router가 실행됐다면 router_engine이 판단한 세부 모드
        (case_based_answer/case_with_procedure/procedure_guidance)를 그대로 쓰고,
        계산기/뉴스만 단독 실행됐다면 그에 맞는 모드로 표시한다."""
        intermediate = state.get("intermediate_results", {})
        if intermediate.get("rag"):
            return state.get("rag_mode") or "case_based_answer"
        if intermediate.get("calculator"):
            return "allowance_calculator"
        if intermediate.get("news"):
            return "latest_news"
        return "supervisor"

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
