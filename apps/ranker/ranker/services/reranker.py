"""
CrossEncoder('Dongjin-kr/ko-reranker') 기반 리랭킹 서비스

Model: Dongjin-kr/ko-reranker (sentence-transformers CrossEncoder)
- 첫 로딩 시 5-15초 소요 (lazy loading)
- GPU 사용 가능 시 자동 활용
- scores는 0~1 사이 float 배열
"""
import logging
from typing import List

logger = logging.getLogger(__name__)

_model = None


def _get_model():
    global _model
    if _model is None:
        from sentence_transformers import CrossEncoder
        logger.info("Loading CrossEncoder model: Dongjin-kr/ko-reranker...")
        _model = CrossEncoder('Dongjin-kr/ko-reranker')
        logger.info("Model loaded successfully.")
    return _model


def rerank(query: str, documents: List[str]) -> List[float]:
    """
    query와 documents 쌍을 CrossEncoder로 리랭킹하여 scores 반환

    Args:
        query: 검색 질의
        documents: 리랭킹할 문서 문자열 리스트

    Returns:
        각 document에 대한 0~1 범위 점수 리스트
    """
    model = _get_model()
    pairs = [[query, doc] for doc in documents]
    scores = model.predict(pairs)
    return scores.tolist() if hasattr(scores, 'tolist') else list(scores)
