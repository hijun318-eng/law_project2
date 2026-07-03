"""
Chroma Vector DB 연결

사전에 init_db.py를 실행하여 벡터DB를 생성해야 합니다.
"""
from langchain_chroma import Chroma
from engine.config import embedding, BASE_DIR

law_db = Chroma(
    persist_directory=str(BASE_DIR / 'vector_db' / 'laws'),
    embedding_function=embedding
)

precedent_db = Chroma(
    persist_directory=str(BASE_DIR / 'vector_db' / 'precedents'),
    embedding_function=embedding
)

qna_db = Chroma(
    persist_directory=str(BASE_DIR / 'vector_db' / 'qna'),
    embedding_function=embedding
)
