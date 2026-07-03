"""
Chroma Vector DB 연결 (Lazy Loading)

사전에 init_db.py를 실행하여 벡터DB를 생성해야 합니다.
최초 접근 시에만 Chroma를 초기화하여 Django 기동 시간을 단축합니다.
"""
from langchain_chroma import Chroma
from engine.config import embedding, BASE_DIR


class _LazyChroma:
    """첫 메서드 호출/속성 접근 시에만 Chroma를 초기화하는 프록시"""

    def __init__(self, persist_directory: str):
        self._persist_directory = persist_directory
        self._db = None

    def _ensure(self):
        if self._db is None:
            self._db = Chroma(
                persist_directory=self._persist_directory,
                embedding_function=embedding,
            )
        return self._db

    def __getattr__(self, name):
        # _ensure() 호출 전에 _persist_directory, _db 등은
        # __init__에서 설정되므로 정상 동작
        return getattr(self._ensure(), name)


law_db = _LazyChroma(str(BASE_DIR / 'vector_db' / 'laws'))
precedent_db = _LazyChroma(str(BASE_DIR / 'vector_db' / 'precedents'))
qna_db = _LazyChroma(str(BASE_DIR / 'vector_db' / 'qna'))
