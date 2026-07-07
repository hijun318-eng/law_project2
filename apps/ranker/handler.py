"""
RunPod Serverless 워커 진입점.

기존 Django `rerank_view`(ranker/views.py)와 동일한 입출력 스펙을
runpod SDK의 handler(job) 패턴으로 감싼 것. 실제 rerank 로직은
ranker/services/reranker.py를 그대로 재사용한다 (Django에 의존하지 않음).
"""
import runpod

from ranker.services.reranker import rerank


def handler(job):
    """
    RunPod job 형식:
        {"input": {"query": "검색어", "documents": ["문서1", "문서2", ...]}}

    반환 형식 (기존 /rerank/ 뷰와 동일):
        {"scores": [0.95, 0.23, ...], "count": 2}
        {"error": "message"}
    """
    job_input = job.get("input", {}) or {}
    query = (job_input.get("query") or "").strip()
    documents = job_input.get("documents", [])

    if not query:
        return {"error": "query is required"}
    if not isinstance(documents, list) or len(documents) == 0:
        return {"error": "documents list is required"}

    try:
        scores = rerank(query, documents)
        return {"scores": scores, "count": len(scores)}
    except Exception as e:
        return {"error": str(e)}


runpod.serverless.start({"handler": handler})
