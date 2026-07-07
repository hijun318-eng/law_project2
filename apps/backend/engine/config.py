"""
LLM 및 Embedding 설정
"""
import os
from pathlib import Path
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain_openai import OpenAIEmbeddings

# engine/config.py → engine/ → backend/ → apps/ → law_project2/ (root)
BASE_DIR = Path(__file__).resolve().parent.parent.parent.parent

load_dotenv(BASE_DIR / '.env')
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# LLM-004: 호출 타임아웃 + 지수 백오프 재시도.
# openai SDK가 max_retries만큼 429/5xx/커넥션 오류에 대해 자동으로 지수 백오프 재시도를 수행한다.
LLM_TIMEOUT_SECONDS = float(os.getenv("LLM_TIMEOUT_SECONDS", "30"))
LLM_MAX_RETRIES = int(os.getenv("LLM_MAX_RETRIES", "3"))

llm = ChatOpenAI(
    model="gpt-5.4-nano",
    temperature=0,
    timeout=LLM_TIMEOUT_SECONDS,
    max_retries=LLM_MAX_RETRIES,
)

embedding = OpenAIEmbeddings(
    model="text-embedding-3-small"
)
