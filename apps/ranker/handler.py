"""RunPod Serverless 진입점. HTTP 서버 대신 RunPod 작업 큐에서 job을 받아 처리한다."""
import runpod

from ranker.services.reranker import rerank


def handler(event):
    job_input = event.get("input") or {}
    query = (job_input.get("query") or "").strip()
    documents = job_input.get("documents") or []

    if not query:
        return {"error": "query is required"}
    if not isinstance(documents, list) or len(documents) == 0:
        return {"error": "documents list is required"}

    scores = rerank(query, documents)
    return {"results": [{"index": i, "score": score} for i, score in enumerate(scores)]}


runpod.serverless.start({"handler": handler})
