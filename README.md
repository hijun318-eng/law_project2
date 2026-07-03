# 노동OK - AI 기반 노동법 상담 서비스

GraphRAG 기반 노동법 상담 AI + Django 웹 애플리케이션

## 프로젝트 구조

```
law_project2/
├── apps/
│   ├── backend/       (A) Django 웹 서버 (port 8000)
│   │   ├── backend/   메인 Django 앱 (views, urls, settings)
│   │   ├── engine/    RAG 엔진 (ChromaDB, LangGraph, Router)
│   │   └── manage.py
│   └── ranker/        (B) 문서 랭킹 마이크로서비스 (port 8001)
│       ├── ranker/    Django 앱 (rerank API)
│       └── manage.py
├── .env               API 키, DB 설정
└── README.md
```

## 사전 준비

### 1. Python 패키지 설치

```bash
cd apps/backend
pip install -r requirements.txt

cd ../ranker
pip install -r requirements.txt
```

### 2. 환경 변수 설정

`.env` 파일을 프로젝트 루트에 생성:

```env
OPENAI_API_KEY=sk-...
NAVER_CLIENT_ID=...
NAVER_CLIENT_SECRET=...
DJANGO_SECRET_KEY=...
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1
RANKER_URL=http://localhost:8001
```

### 3. 벡터 DB 생성 (최초 1회)

RAG 엔진이 사용할 법령/판례/질의회시 ChromaDB를 생성합니다.

```bash
cd apps/backend
python -m engine.init_db          # 전체 DB 생성
python -m engine.init_db --force  # 기존 DB 삭제 후 재생성
python -m engine.init_db --db law # 특정 DB만 생성 (law|precedent|qna)
```

---

## 프로젝트 기동

두 프로젝트를 **동시에** 실행해야 합니다.

### A. Backend (Django 웹 서버) — port 8000

```bash
cd apps/backend
python manage.py runserver 0.0.0.0:8000
```

- 메인 웹 서버 (랜딩 페이지, 로그인, 대시보드, 법률 상담 API)
- 접속: http://localhost:8000

### B. Ranker (문서 랭킹 마이크로서비스) — port 8001

```bash
cd apps/ranker
python manage.py runserver 0.0.0.0:8001
```

- 문서 재순위화(re-ranking) API 제공
- Backend의 RAG 엔진이 랭킹이 필요할 때 호출

### 확인

| 서비스 | URL | 예상 응답 |
|--------|-----|-----------|
| Backend | http://localhost:8000/ | 노동OK 랜딩 페이지 |
| Ranker  | http://localhost:8001/rerank/ | 405 Method Not Allowed (POST 필요) |

---

## API 엔드포인트

| 경로 | 메서드 | 설명 |
|------|--------|------|
| `/` | GET | 랜딩 페이지 |
| `/login/` | GET/POST | 로그인 |
| `/register/` | GET/POST | 회원가입 |
| `/logout/` | GET | 로그아웃 |
| `/app/` | GET | 사용자 앱 (로그인 필요) |
| `/admin-console/` | GET | 관리자 대시보드 (admin 계정 필요) |
| `/api/advice/` | POST | 법률 상담 질문 |
| `/api/calculate/` | POST | 수당 계산 (form/chat 모드) |
| `/api/news/` | GET | 최신 노동법 뉴스 |
| `/api/prompts/` | POST | 프롬프트 관리 |

---

## 테스트 계정

| 계정 | 이메일 | 비밀번호 | 권한 |
|------|--------|----------|------|
| 관리자 | admin@example.com | 11111111 | admin |
| 사용자 | user@example.com | 11111111 | user |

---

## 주요 기술 스택

| 구성 | 기술 |
|------|------|
| Backend | Django 6.0, Python 3.13 |
| Vector DB | ChromaDB (langchain-chroma) |
| LLM | OpenAI GPT + Embedding |
| RAG | LangGraph (7-node StateGraph) |
| Re-ranker | ranker 마이크로서비스 |
| News | Naver News API |
| Frontend | Django Templates + CSS |
