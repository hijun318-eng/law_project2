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

llm = ChatOpenAI(
    model="gpt-5.4-nano",
    temperature=0
)

embedding = OpenAIEmbeddings(
    model="text-embedding-3-small"
)
