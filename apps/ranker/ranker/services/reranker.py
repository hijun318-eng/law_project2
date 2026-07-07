import logging
import os
from typing import List

logger = logging.getLogger(__name__)

MODEL_NAME = os.getenv("RERANKER_MODEL", "Dongjin-kr/ko-reranker")
MAX_DOCUMENTS = int(os.getenv("RERANKER_MAX_DOCUMENTS", "30"))
MAX_CHARS = int(os.getenv("RERANKER_MAX_CHARS", "1800"))
BATCH_SIZE = int(os.getenv("RERANKER_BATCH_SIZE", "4"))

_model = None


def _get_model():
    global _model
    if _model is None:
        import torch
        from sentence_transformers import CrossEncoder

        device = os.getenv("RERANKER_DEVICE")
        if not device:
            device = "cuda" if torch.cuda.is_available() else "cpu"

        logger.info("Loading CrossEncoder model %s on %s", MODEL_NAME, device)
        _model = CrossEncoder(MODEL_NAME, device=device)
        logger.info("CrossEncoder model loaded")
    return _model


def rerank(query: str, documents: List[str]) -> List[float]:
    model = _get_model()
    safe_documents = [(doc or "")[:MAX_CHARS] for doc in documents[:MAX_DOCUMENTS]]
    pairs = [[query, doc] for doc in safe_documents]

    scores = model.predict(pairs, batch_size=BATCH_SIZE)
    result = scores.tolist() if hasattr(scores, "tolist") else list(scores)

    if len(documents) > len(result):
        result.extend([0.0] * (len(documents) - len(result)))

    return result
