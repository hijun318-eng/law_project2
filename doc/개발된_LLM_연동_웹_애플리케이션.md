# 노동OK — 개발된 LLM 연동 웹 어플리케이션

- 작성일: 2026-07-08
- 대상: 노동OK (GraphRAG 기반 노동법 상담 AI + Django 웹 애플리케이션)
- 목적: "개발된 LLM 연동 웹 애플리케이션" 평가기준 4개 항목의 구현 현황을 실제 코드 근거로 정리

## 한눈에 보기

| 평가 항목 | 평가 내용 | 충족 여부 |
|---|---|:---:|
| 1. 프론트엔드 구현 완성도 | HTML5/CSS3 반응형 마크업, ES6+ 문법, DOM/이벤트 처리 | ✅ 충족 |
| 2. 비동기 LLM 연동 구현 | Async/Await·Fetch API 외부 API 호출, 예외·로딩 처리 | ✅ 충족 |
| 3. Django 백엔드 구현 | MVT/ORM/FBV·CBV/폼 검증/인증·권한 처리 | ⚠️ 부분 충족 |
| 4. 배포·운영 구현 | AWS(EC2·RDS·S3)와 Docker 기반 배포 | ⚠️ 부분 충족 (RDS는 적용됨, 정적/미디어용 S3(django-storages)만 미도입 — vector_db 동기화용 S3는 구현됨) |

> 3, 4번 항목의 미비점은 각 섹션 하단 "미구현/차이" 박스와 문서 맨 끝 [보완 제언](#보완-제언)에 정리했습니다. RDS는 적용 완료, S3는 vector_db 동기화 용도로 이미 구현되어 있으며(정적/미디어용은 미도입), 현재 진행 상황은 4번 섹션과 [보완 제언](#보완-제언)에 정리했습니다.

---

## 1. 프론트엔드 구현 완성도

**결론: HTML5 시맨틱 마크업, CSS 반응형, ES6+ 문법, DOM 이벤트 처리를 모두 갖춤**

### HTML5 / 반응형 CSS

| 구현 내용 | 근거 |
|---|---|
| 반응형 뷰포트, ES 모듈 로딩 | `templates/labor/base.html:1-19` |
| 시맨틱 태그(header/nav/main/section/footer) | `templates/labor/landing.html` |
| 미디어쿼리 2단계 (900px / 480px) | `static/labor/css/app.css:502, 523` |
| 모바일 브레이크포인트 (768px) | `static/labor/css/landing2.css:209` |
| Grid 레이아웃 (`.feature-grid`) | `static/labor/css/app.css:117-123` |
| Flexbox 레이아웃 (`.landing-header`) | `static/labor/css/app.css:65-72` |

### ES6+ 문법 / DOM·이벤트 처리

| 구현 내용 | 근거 |
|---|---|
| 화살표 함수 + `const`, 모듈 export | `static/labor/js/utils.js:6-12` |
| ES 모듈 import/오케스트레이션 | `static/labor/js/app-main.js:1-5` |
| async/await + fetch | `static/labor/js/app-main.js:36, 72-73` |
| 스프레드 문법 | `static/labor/js/admin-dashboard.js:7` |
| 구조분해 할당 파라미터 | `static/labor/js/advice.js:80-106` |
| 이벤트 위임 (`closest()`) | `static/labor/js/advice.js:184-222` |
| 실시간 클라이언트 검증 | `static/labor/js/calculator.js:10-53` |

---

## 2. 비동기 LLM 연동 구현

**결론: fetch 스트리밍, 진행상황 UI, 에러 처리, 백엔드 SSE·LLM 호출까지 전 구간 구현됨**

### 프론트엔드 (fetch / 로딩 / 에러)

| 구현 내용 | 근거 |
|---|---|
| SSE 스트림을 직접 파싱하는 fetch 리더 | `static/labor/js/advice.js:80-105` `streamAdvice()` |
| 로딩 스피너 + 진행률 텍스트 | `static/labor/js/advice.js:65-67` |
| 경과시간 타이머 | `static/labor/js/advice.js:151-155` |
| LangGraph 노드별 진행상황 문구 변환 | `static/labor/js/advice.js:71-75` |
| 실패 시 사용자 노출 에러 메시지 | `static/labor/js/advice.js:167-171` |
| try/catch 에러 처리 | `static/labor/js/app-main.js:71-83` |

### 백엔드 (SSE / LLM 호출)

| 구현 내용 | 근거 |
|---|---|
| `StreamingHttpResponse` 기반 SSE 응답 | `backend/views.py:375-444` `advice_api()` |
| 진행상황 이벤트 제너레이터 | `backend/views.py:397-419` `event_stream()` |
| 백그라운드 스레드 + Queue로 실시간 진행상황 전달 | `engine/supervisor/engine.py:58-133` |
| OpenAI LLM 호출 (타임아웃·재시도 설정) | `engine/config.py:7, 21-26` |
| 임베딩 API 연동 | `engine/config.py:28-30` |
| OpenAI 예외 → 사용자 메시지 변환 | `engine/utils/llm_errors.py:2` |
| nginx에서 SSE 버퍼링 차단 설정 | `docker/nginx.conf:19-28` |

---

## 3. Django 백엔드 구현

**결론: MVT/ORM/인증·인가는 탄탄하나, CBV와 Django Form 클래스는 미사용 (아래 "미구현" 참고)**

### MVT 패턴

| 구성요소 | 근거 |
|---|---|
| Model | `chat/models.py:5-73` (`ChatHistory`, `PromptTemplate` 등), `monitoring/models.py:4-43` |
| View | `backend/views.py` 전체 |
| Template | `templates/labor/*.html` |
| 화면-URL-View-Template 매핑 설계서 | `doc/screen_design.md` (SC-1.1~SC-4.5, 실제 구현 기준) |

> **설계 문서와 실제 구현의 차이**: `doc/Django MVT 설계.md`(초기안)는 `home`/`accounts`/`chat`/`calculator`/`news`/`dashboard`로 앱을 분리하는 구조를 제안했지만, 실제로는 `apps/backend/backend` 단일 앱에 `/app/?page=...`, `/admin-console/?tab=...` 같은 쿼리 파라미터 라우팅으로 통합됨. 최신 실제 구조는 `doc/screen_design.md` 기준.

### ORM

| 구현 내용 | 근거 |
|---|---|
| 필터/정렬/카운트 쿼리셋 | `backend/views.py:230-232` |
| 집계 쿼리셋 (`Count`, `TruncDay` 등) | `backend/services/dashboard.py:29-35` |
| `update_or_create` | `backend/views.py:333-339` |
| 마이그레이션 | `chat/migrations/0001~0004`, `monitoring/migrations/0001` |

### FBV / CBV, 폼 검증, 인증·인가

| 항목 | 현황 | 근거 |
|---|---|---|
| FBV | ✅ 전체 뷰가 함수 기반 | `backend/views.py:60-444` 전반 |
| CBV | ❌ 미사용 | 레포 전체에서 `View`/`ListView` 서브클래스 없음 |
| Django Form/ModelForm | ❌ 미사용, 수동 검증으로 대체 | `backend/views.py:146-154` `register_view()` |
| 로그인/세션/잠금 | ✅ | `backend/views.py:91-136`, 5회 실패 시 10분 잠금 |
| 관리자 전용 접근 제어 | ✅ | `backend/views.py:251-252` |
| IDOR 방지(본인 데이터만 조회) | ✅ | `backend/views.py:520-523` |
| 세션 만료(60분) | ✅ | `backend/settings.py:130-132` |
| 마이크로서비스 간 Bearer 토큰 인증 | ✅ | `ranker/ranker/views.py:28-32` |

---

## 4. 배포·운영 구현

**결론: Docker + Nginx + EC2 2대 분리 배포 + CI는 구성됨. RDS는 적용 완료, S3는 벡터 DB 동기화 용도로 구현됨 (정적/미디어용 S3는 미도입 — 아래 "미구현" 참고)**

### Docker / Nginx

| 구현 내용 | 근거 |
|---|---|
| 백엔드 이미지 | `docker/Dockerfile.backend` |
| GPU 랭커 이미지 (CUDA PyTorch) | `docker/Dockerfile.ranker.gpu` |
| 로컬 개발용 compose (backend+ranker) | `docker/docker-compose.yml` |
| AWS 배포용 compose (nginx+backend) | `docker/docker-compose.backend.aws.yml` |
| GPU 랭커 전용 compose | `docker/docker-compose.ranker-gpu.aws.yml` |
| nginx 리버스 프록시 설정 | `docker/nginx.conf`, `doc/nginx-backend-deploy.md` |

nginx 도입으로 `backend` 컨테이너는 `expose: 8000`(내부망 전용)만 사용하고, 외부에는 nginx의 80 포트만 노출됨 — 공격 표면 축소. 호스트 Nginx/Apache와의 포트 충돌 대응 절차까지 문서화됨.

### AWS EC2 2대 분리 배포

| 서버 | 인스턴스 타입 | 역할 | 보안그룹 |
|---|---|---|---|
| Backend EC2 | `t3.large` (최소 `t3.medium`) | 웹 서빙, Django API, Chroma 검색, OpenAI 호출 | 22(내 IP), 80(nginx) |
| Ranker GPU EC2 | `g4dn.2xlarge`/`g5.2xlarge` (최소 `g4dn.xlarge`) | 랭커 모델 서빙(`/rerank/`) | 22(내 IP), 8001(Backend만 허용) |

두 서버는 VPC 내부 Private IP로 통신(`RANKER_URL=http://RANKER_PRIVATE_IP:8001/rerank/`). GPU 랭커는 Gunicorn worker를 1개로 고정해 모델이 worker마다 복제되어 VRAM이 초과되는 것을 방지(`docker/Dockerfile.ranker.gpu`). 배포 문서(`doc/aws-ec2-two-server-deploy.md`)에 10단계 배포 순서와 워밍업/OOM/디스크 부족 트러블슈팅 절차가 포함되어 있어 재현 가능한 형태로 정상 동작을 검증할 수 있음.

### GPU 비용 최적화: RunPod 이전

상시 과금되는 GPU EC2 대신 사용량 기반 과금인 RunPod Pod로 랭커만 이전하는 경로도 마련됨(`doc/runpod-ranker-deploy.md`). AWS 내부망과 달리 퍼블릭 프록시로 노출되므로 `Authorization: Bearer <RANKER_API_KEY>` 인증을 추가 구현:
- `apps/ranker/ranker/views.py:28-32` (토큰 검증)
- `apps/backend/engine/nodes/retrieval.py:16-24` (토큰 첨부 호출)

### AWS RDS(PostgreSQL) 적용

DB 계층은 `DATABASE_URL` 환경변수 유무로 SQLite/RDS를 전환하도록 코드에 구현되어 있으며, 배포 환경은 RDS 인스턴스 생성 후 EC2 `.env`에 `DATABASE_URL`을 채우는 방식으로 적용 완료됨:

| 구현 내용 | 근거 |
|---|---|
| `DATABASE_URL` 기반 DB 분기 (`dj_database_url.parse`) | `backend/settings.py:91-107` |
| PostgreSQL 드라이버 | `requirements.txt:18` (`psycopg[binary]`) |
| 커넥션 풀링(`DB_CONN_MAX_AGE`), SSL 강제(`DB_SSL_REQUIRE`) | `backend/settings.py:97-98` |
| RDS 생성값·전환 절차·백업/복원·롤백 가이드 | `doc/rds-postgres-migration.md` |

> `DATABASE_URL`이 비어 있으면 기존처럼 SQLite로 동작 — 로컬 개발 환경은 SQLite 그대로 두고, 배포 환경(EC2)만 RDS를 사용하도록 분리 적용됨.

### AWS S3 스토리지 — Chroma vector_db 동기화
**배포 시 Chroma 벡터 DB를 S3와 동기화**하는 형태로 S3를 사용:

| 구현 내용 | 근거 |
|---|---|
| GitHub Actions 배포 스텝에서 `aws s3 sync`로 `vector_db/` 복원 | `.github/workflows/deploy-ec2.yml:28-41` |
| S3 URI를 시크릿으로 주입 (`VECTOR_DB_S3_URI`), 미설정 시 스킵 | 위 워크플로 조건문 (`if [ -n "${{ secrets.VECTOR_DB_S3_URI }}" ]`) |
| EC2에 AWS CLI 미설치 시 자동 설치 후 `aws s3 sync ... --delete` 실행 | 위 워크플로 |

> Chroma `vector_db`는 대용량 임베딩 인덱스라 Git/이미지에 포함하지 않고, 배포 때마다 S3에서 최신본을 내려받는 방식으로 운영. `doc/rds-postgres-migration.md`에서도 "Chroma vector_db는 RDS 대상이 아니며 별도 벡터 저장소/백업으로 다룬다"고 명시한 부분이 이 S3 동기화로 실현됨.
>
> 원래 `deploy` 브랜치(커밋 `03870d9` "Sync vector DB from S3 during deploy")에만 있던 구현을 `main`의 `deploy-ec2.yml`에도 반영함.

### 환경변수 / CI

| 구현 내용 | 근거 |
|---|---|
| 환경변수 기반 설정 (`python-decouple`) | `backend/settings.py:1-41` |
| `.env` 로드 (`python-dotenv`) | `engine/config.py:6, 13-14` |
| 시크릿 템플릿화 | `.env.example` |
| GitHub Actions CI (test + JS 구문검사) | `.github/workflows/ci.yml` |

---

## 미구현 / 설계 차이 정리

| 평가기준 요구사항 | 현황 |
|---|---|
| CBV | 미사용 — 전체 FBV로만 구현 |
| Django Form/ModelForm | 미사용 — 뷰 함수 내 수동 검증(`if not name or not email...`)으로 대체 |
| RDS | 적용 완료 — `settings.py:91-107`에서 `DATABASE_URL` 유무로 SQLite/PostgreSQL(RDS) 분기, 배포 환경(EC2)은 `DATABASE_URL`을 RDS 엔드포인트로 설정해 사용 중, 로컬 개발 환경은 미설정 시 SQLite로 자동 대체 |
| S3 | vector_db 동기화 용도로 구현 완료 — `main`의 `.github/workflows/deploy-ec2.yml`에서 배포 시 `aws s3 sync`로 Chroma `vector_db/` 복원. 정적/미디어 파일용 `django-storages`/`boto3`는 미도입 |

## 보완 제언

1. **CBV 추가** — 관리자 대시보드류 뷰 1~2개를 `View`/`TemplateView`로 리팩터링
2. **Django Form 도입** — `register_view()`의 수동 검증을 `RegisterForm(forms.Form)` + `clean_*`로 전환
3. **RDS 적용 완료** — 코드(`DATABASE_URL` 분기) 및 배포 환경 적용까지 완료. 절차/롤백 가이드는 `doc/rds-postgres-migration.md` 참고
4. **정적/미디어 파일 S3화 (선택, 미도입)** — 필요 시 `django-storages`+`boto3` 추가, `STORAGES` 설정 및 버킷/IAM 구성으로 확장 가능
