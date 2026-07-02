"""
RAGEngine — LangGraph 기반 법률 분석 엔진

사용법:
    from engine.rag_engine import RAGEngine
    engine = RAGEngine()
    result = engine.answer("질문 내용")
    print(result["answer"])
    
    # 진행상황 스트리밍 (노드 단위):
    for node_name, label, detail in engine.stream_answer("질문 내용"):
        print(f"{label}: {detail}")
    
    # 토큰 스트리밍 (최종 답변 실시간 출력):
    for event in engine.stream_answer("질문 내용"):
        if event[0] == "token":
            print(event[2], end="", flush=True)
"""
import time
from engine.graph import graph
from engine.utils.execution_logger import init_logger, get_logger, clear_logger

NODE_LABELS = {
    "retrieve_precedent":        "🔍 판례 직접 검색",
    "retrieve_law":              "⚖️ 관련 법령 검색",
    "generate_answer":           "💡 최종 답변 생성",
    "procedure_guide":           "📋 절차 안내 생성",
}


class RAGEngine:
    """법률 RAG 엔진 (LangGraph 기반)"""

    def __init__(self):
        self.graph = graph

    def answer(self, question: str, top_k: int = 5) -> dict:
        """
        질문에 대한 법률 분석을 수행합니다.

        Returns:
            {"answer": str, "sources": list[dict]}
        """
        # 조건부 로거 초기화: 활성 로거가 없으면 새로 생성
        logger_created = False
        if get_logger() is None:
            init_logger(question)
            logger_created = True
        logger = get_logger()

        start = time.time()
        result = self.graph.invoke({"question": question})
        elapsed = time.time() - start

        if logger:
            logger.record_node("rag_engine_total", elapsed, "success")

        # 소스 문서 정보 추출
        sources = self._format_sources(result)

        try:
            return {
                "answer": result.get("final_answer", ""),
                "procedure": result.get("procedure_guide", ""),
                "sources": sources,
            }
        finally:
            # 이 메서드가 로거를 생성한 경우에만 finish/save/clear
            if logger_created and logger:
                answer_text = result.get("final_answer", "") if 'result' in locals() else ""
                logger.finish(answer_text)
                logger.save()
                clear_logger()

    def stream_answer(self, question: str, top_k: int = 5):
        """
        그래프 실행 과정을 실시간으로 스트리밍합니다.

        Phase 1 — 각 노드 완료 시마다 (node_name, label, detail) 튜플을 yield
        Phase 2 — 최종 답변을 토큰 단위로 yield (node_name="token", detail=토큰문자열)
        마지막 yield는 node_name="done"이며 detail에 최종 결과를 담습니다.

        Args:
            question: 사용자 질문
            top_k:   (향후 확장)

        Yields:
            (node_name: str, label: str, detail: str | dict)
        """
        # 조건부 로거 초기화
        logger_created = False
        if get_logger() is None:
            init_logger(question)
            logger_created = True
        logger = get_logger()

        result = {"question": question}  # graph.stream()은 초기 input을 포함하지 않음
        try:
            for event in self.graph.stream({"question": question}):
                for node_name, output in event.items():
                    result.update(output)
                    label = NODE_LABELS.get(node_name, node_name)
                    detail = self._format_stream_detail(node_name, output)
                    yield (node_name, label, detail)

            sources = self._format_sources(result)
            final_answer = result.get("final_answer", "")
            procedure = result.get("procedure_guide", "")

            # done yield 전에 로거 마무리 (stream_answer가 생성한 경우만)
            if logger_created and logger:
                logger.finish(final_answer)
                logger.save()
                clear_logger()

            yield "done", "✅ 분석 완료", {
                "answer": final_answer,
                "procedure": procedure,
                "sources": sources,
            }
        finally:
            # Safety net: generator가 done yield까지 도달하지 못하고 종료된 경우
            if logger_created and logger and not logger.end_time:
                answer_text = result.get("final_answer", "") if 'result' in locals() else ""
                logger.finish(answer_text)
                logger.save()
                clear_logger()

    def _format_stream_detail(self, node_name: str, output: dict):
        """스트리밍 중 각 노드 출력을 읽을 수 있는 형태로 변환"""
        """각 노드 출력을 사람이 읽을 수 있는 형태로 변환"""
        if node_name == "retrieve_precedent":
            docs = output.get("precedent_docs_direct", [])
            return f"판례 {len(docs)}건 검색됨"
 
        elif node_name == "retrieve_law":
            docs = output.get("law_docs", [])
            analysis = output.get("law_analysis", [])
            return f"법령 {len(docs)}개 검색됨 / 조항 {len(analysis)}개 추출"

        elif node_name == "generate_answer":
            answer = output.get("final_answer", "") or ""
            used = output.get("used_precedents", [])
            return f"답변 {len(answer)}자 생성 / 인용 판례 {len(used)}건"
 
        elif node_name == "procedure_guide":
            guide = output.get("procedure_guide", "") or ""
            return f"절차 안내 {len(guide)}자 생성"
 
        return ""

    def _format_sources(self, state: dict) -> list:
        """그래프 실행 결과 state에서 소스 문서 리스트를 추출"""
        sources = []

        for doc in state.get("law_docs", []):
            m = doc.metadata
            sources.append({
                "type": "law",
                "law_name": m.get("law_name", ""),
                "article_no": m.get("article_no", ""),
                "article_title": m.get("article_title", ""),
                "chapter_title": m.get("chapter_title", ""),
            })
 
        for doc in state.get("precedent_docs", []):
            m = doc.metadata
            sources.append({
                "type": "precedent",
                "case_no": (
                    m.get("source_file", "")
                    .replace(".md", "")
                    .replace(".json", "")
                ),
                "category": m.get("category", ""),
            })
 
        return sources
