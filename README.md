# ⚖️ 노동OK

대한민국 노동법에 대한 질의응답, 상황별 권리 진단, 임금·퇴직금 계산, 최신 노동 뉴스 요약을 제공하는 **GraphRAG 기반 AI 어시스턴트**입니다. 법령·판례를 벡터 DB(ChromaDB)에 임베딩하고 LangGraph 기반 멀티스텝 추론(RAG)으로 근거 있는 법률 정보를 제공하며, Django 웹 애플리케이션으로 구현되어 Docker/AWS 환경에 배포됩니다.

> ⚠️ 본 서비스는 법률 자문이 아닌 참고 정보를 제공합니다. 구체적인 법적 조치가 필요한 경우 노무사·변호사 등 전문가와 상담하시기 바랍니다.

## 1. 👥 팀 구성

| 이름 | 정영석 | 최원빈 | 성주연 | 박준희 |
|:---:|:---:|:---:|:---:|:---:|
| **사진** | <img width="100" src="https://github.com/user-attachments/assets/794d5da9-3880-47f1-ba84-a19db9649b57" /> | <img width="100" src="https://github.com/user-attachments/assets/b605de84-6c64-4739-922c-904b1faf2094" /> | <img width="100" src="https://github.com/user-attachments/assets/ebb16dc3-d0f3-48ce-8757-f2cfbb870f4c" /> | <img width="100" src="https://github.com/user-attachments/assets/b7935738-09c5-4c48-828c-f1aa37bd99ea" /> |
| **역할** | 🧭 **PM** | ☁️ **DevOps Engineer** | 🎨 **Frontend Developer** | ⚙️ **Backend Developer** |
| **담당** | 전체 일정 관리, 요구사항 정의, 산출물 통합 조율 | Docker/Nginx 구성, AWS EC2·RDS·S3 배포, GitHub Actions CI/CD | Django Template·정적 UI 구현, 반응형 레이아웃, SSE 기반 상담 화면 인터랙션 | Django 서버·API 구현, LangGraph RAG/계산기/뉴스 엔진, 벡터DB(Chroma) 구성 및 검색 파이프라인 |

## 2. ✨ 주요 기능

| 기능 | 설명 |
|---|---|
| 💬 AI 법률 상담(QA) | 자연어 질문을 RouterEngine이 분류하여 판례·법령 검색 기반 답변(case_based_answer) 또는 절차 안내(procedure_guidance)를 제공 |
| 🧾 권리찾기 | 임금체불·부당해고·직장 내 괴롭힘 등 상황별 신고·구제 절차를 단계별로 안내 |
| 📋 증거자료 관리 | 상황별로 확보해야 할 증거자료 체크리스트(근로계약서, 급여명세서, 근태기록 등) 제공 |
| 🧮 계산기 | 퇴직금·연차수당·주휴수당 계산 및 최저임금 위반 여부 확인 (LangGraph ReAct 파이프라인, 법령 근거 함께 표시) |
| 📰 최신 뉴스 | 네이버 뉴스 API로 노동·고용 관련 기사를 수집하고 ReAct 루프로 요약 |
| 👤 마이페이지 | 상담 이력(QA/권리찾기/계산기) 조회, 계정 정보 확인 |
| 🛡️ 관리자 콘솔 | 대시보드, 사용자 관리, 피드백(만족도) 관리, 프롬프트 템플릿 관리(버전/롤백), 성능 모니터링 |

## 3. 🖥️ 주요 기능 화면

> 상세 UI 요소/이벤트 명세는 [`doc/화면_설계서.md`](doc/화면_설계서.md) 참고.

| 화면 | 미리보기 | 설명 |
|---|---|---|
| 🏠 랜딩 (SC-1.1) | ![SC-1.1 랜딩](doc/screenshots/SC-1.1_landing.png) | 비로그인 사용자가 처음 진입하는 서비스 소개 화면. 서비스의 핵심 기능, 데이터 출처, 예시 상담 UI, 이용 방법, 회원가입 CTA를 제공한다. |
| 💬 AI 노동법 상담 (SC-3.1) | ![SC-3.1 AI 노동법 상담](doc/screenshots/SC-3.1_advice.png) | 로그인한 사용자가 노동법 관련 질문을 입력하고 AI 답변을 받는 핵심 상담 화면. 빠른 질문 버튼과 직접 입력을 모두 지원하며, 답변 하단에는 피드백(도움됐어요/아쉬워요)·법령 원문·저장 액션 버튼을 표시한다. |
| 🧮 수당 계산기 (SC-3.2) | ![SC-3.2 수당 계산기](doc/screenshots/SC-3.2_calculator.png) | 숫자 입력 또는 자연어 입력으로 퇴직금, 연차수당, 주휴수당을 계산하고 최저임금 위반 여부를 확인하는 화면. |
| 📰 최신 노동법 뉴스 (SC-3.3) | ![SC-3.3 최신 노동법 뉴스](doc/screenshots/SC-3.3_news.png) | 검색어와 카테고리를 통해 노동법 관련 최신 뉴스 목록과 AI 요약을 확인하는 화면. |
| 👤 마이페이지 (SC-3.4) | ![SC-3.4 마이페이지](doc/screenshots/SC-3.4_mypage.png) | 사용자의 상담 이력(QA/권리찾기/계산기)과 계정 정보를 탭으로 확인하는 개인 화면. |

## 4. 🛠️ 기술 스택

| 구분 | 스택 |
|---|---|
| **Backend** | ![Python](https://img.shields.io/badge/Python-3776AB?style=flat-square&logo=python&logoColor=white) ![Django](https://img.shields.io/badge/Django-092E20?style=flat-square&logo=django&logoColor=white) ![LangChain](https://img.shields.io/badge/LangChain-1C3C3C?style=flat-square&logo=langchain&logoColor=white) ![LangGraph](https://img.shields.io/badge/LangGraph-1C3C3C?style=flat-square) ![OpenAI](https://img.shields.io/badge/OpenAI-412991?style=flat-square&logo=openai&logoColor=white) |
| **Vector DB / Reranker** | ![ChromaDB](https://img.shields.io/badge/ChromaDB-FF6F00?style=flat-square) ![ko--reranker](https://img.shields.io/badge/ko--reranker-FF6F00?style=flat-square) |
| **Database** | ![SQLite](https://img.shields.io/badge/SQLite-003B57?style=flat-square&logo=sqlite&logoColor=white) ![PostgreSQL](https://img.shields.io/badge/PostgreSQL-4169E1?style=flat-square&logo=postgresql&logoColor=white) |
| **Frontend** | ![HTML5](https://img.shields.io/badge/HTML5-E34F26?style=flat-square&logo=html5&logoColor=white) ![CSS3](https://img.shields.io/badge/CSS3-1572B6?style=flat-square&logo=css3&logoColor=white) ![JavaScript](https://img.shields.io/badge/JavaScript-F7DF1E?style=flat-square&logo=javascript&logoColor=black) |
| **Infra / DevOps** | ![Docker](https://img.shields.io/badge/Docker-2496ED?style=flat-square&logo=docker&logoColor=white) ![Nginx](https://img.shields.io/badge/Nginx-009639?style=flat-square&logo=nginx&logoColor=white) ![Gunicorn](https://img.shields.io/badge/Gunicorn-499848?style=flat-square&logo=gunicorn&logoColor=white) ![AWS EC2](https://img.shields.io/badge/AWS%20EC2-FF9900?style=flat-square&logo=amazonec2&logoColor=white) ![AWS S3](https://img.shields.io/badge/AWS%20S3-569A31?style=flat-square&logo=amazons3&logoColor=white) ![AWS RDS](https://img.shields.io/badge/AWS%20RDS-527FFF?style=flat-square&logo=amazonrds&logoColor=white) ![GitHub Actions](https://img.shields.io/badge/GitHub%20Actions-2088FF?style=flat-square&logo=githubactions&logoColor=white) |

## 5. 📂 프로젝트 구조

```
law_project2/
├── apps/
│   ├── backend/                # 메인 Django 앱 (사용자 서비스 + 관리자 콘솔)
│   │   ├── backend/            # 프로젝트 설정, urls, views, forms
│   │   ├── chat/                # 상담 이력, 프롬프트 템플릿 모델
│   │   ├── monitoring/          # 성능/비용 모니터링 모델
│   │   ├── engine/              # LangGraph 기반 RAG/계산기/뉴스 엔진
│   │   │   ├── builders/        # 법령/판례/질의회시 벡터DB 빌더
│   │   │   ├── retrievers/      # 판례 검색 + 리랭킹
│   │   │   ├── nodes/           # RAG 그래프 노드 (검색/생성)
│   │   │   ├── supervisor/      # 복합 질문용 멀티에이전트 컨트롤러
│   │   │   ├── calculator/      # 임금/퇴직금 계산 ReAct 파이프라인
│   │   │   ├── news/            # 네이버 뉴스 수집·요약
│   │   │   ├── ocr_contract/    # 근로계약서 OCR 파이프라인
│   │   │   └── prompts/         # 프롬프트 템플릿(*.md, 관리자 화면에서 편집)
│   │   ├── static/ · templates/ # 정적 자원, HTML 템플릿
│   │   └── requirements.txt
│   └── ranker/                  # 판례 리랭킹 전용 Django 서비스 (GPU)
├── scripts/preprocess/           # 원본(PDF/MD) → JSON 전처리 스크립트
├── docker/                       # Dockerfile, docker-compose(local/AWS), nginx 설정
├── doc/                          # 요구사항 정의서, 시스템 구성도, 화면 설계서, 배포 매뉴얼 등
└── .github/workflows/            # CI, EC2 배포 워크플로
```

## 6. 🚀 시작하기

### 6.1 사전 요구사항

- Python 3.12+ (`docker/Dockerfile.backend` 기준 `python:3.12-slim`, CI는 3.13 사용)
- Docker / Docker Compose (선택, 컨테이너 실행 시)
- OpenAI API Key, 네이버 뉴스 API Key(Client ID/Secret)

### 6.2 환경변수 설정

```bash
cp .env.example .env
# .env에 OPENAI_API_KEY, NAVER_CLIENT_ID/SECRET 등 채우기
```

### 6.3 벡터 DB 생성 (최초 1회)

```bash
# 프로젝트 루트에서 의존성 설치 + 전처리 (data/raw/ → data/process/)
pip install -r apps/backend/requirements.txt
python scripts/preprocess/run_preprocess.py

# apps/backend에서 벡터DB 생성 (data/process/ → Chroma vector_db/)
(cd apps/backend && python -m engine.init_db)
```

### 6.4 로컬 실행

**직접 실행**

```bash
cd apps/backend
python manage.py migrate
python manage.py runserver
```

**Docker Compose** (backend + ranker)

```bash
cd docker
docker compose up --build
```

## 7. ☁️ 배포

- AWS EC2 2대(Backend / Ranker GPU) 분리 배포, Nginx → Gunicorn → Django(WSGI) 구조
- GitHub Actions로 Docker 이미지 빌드·배포 및 S3에서 벡터DB 동기화 자동화
- 상세 절차: [`doc/manuals/aws-ec2-two-server-deploy.md`](doc/manuals/aws-ec2-two-server-deploy.md), [`doc/manuals/github-actions-ec2-deploy.md`](doc/manuals/github-actions-ec2-deploy.md), [`doc/manuals/rds-postgres-migration.md`](doc/manuals/rds-postgres-migration.md), [`doc/manuals/runpod-ranker-deploy.md`](doc/manuals/runpod-ranker-deploy.md)

## 8. 📚 문서

| 문서 | 내용 |
|---|---|
| [`doc/요구사항_정의서.md`](doc/요구사항_정의서.md) | 기능/비기능 요구사항, 유스케이스, 추적성 매트릭스 |
| [`doc/시스템_구성도.md`](doc/시스템_구성도.md) | 전체 데이터 흐름, 배포 아키텍처, 클라우드/컨테이너 구성, 보안 |
| [`doc/화면_설계서.md`](doc/화면_설계서.md) | 화면별 와이어프레임 및 URL/View/Template 매핑 |
| [`doc/테스트_계획_및_결과_보고서.md`](doc/테스트_계획_및_결과_보고서.md) | 테스트 케이스 및 결과 |
| [`doc/개발된_LLM_연동_웹_애플리케이션.md`](doc/개발된_LLM_연동_웹_애플리케이션.md) | 기술 구현 현황 정리 |
| [`doc/manuals/`](doc/manuals/) | Django MVT 설계안, AWS/RDS/RunPod 배포 매뉴얼 |
