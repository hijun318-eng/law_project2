# Nginx + Backend Docker Compose 배포 가이드

이 문서는 Backend 앞단에 Nginx 컨테이너를 붙여 외부 HTTP 80 포트로 서비스하는 구조를 설명합니다.

## 구조

```text
사용자 브라우저
  ↓ http://SERVER_IP
AWS EC2 보안 그룹: 80 허용
  ↓
nginx container :80
  ↓ proxy_pass http://backend:8000
backend container :8000
  ↓
Django + Gunicorn
```

컨테이너는 2개입니다.

```text
Docker Compose
├─ nginx
└─ backend
```

## 변경된 파일

- `docker/docker-compose.backend.aws.yml`
  - `nginx` 서비스 추가
  - 외부 공개 포트는 `nginx`의 `80:80`
  - `backend`는 `ports` 대신 `expose: 8000`으로 Docker 내부 네트워크에만 노출
- `docker/nginx.conf`
  - `/` 요청을 `backend:8000`으로 프록시
  - `/static/`은 Nginx가 직접 응답
  - `/api/advice/`는 SSE 진행상황 스트리밍을 위해 buffering 비활성화
- `apps/backend/backend/settings.py`
  - Nginx 프록시 헤더 인식을 위한 설정 추가

## 서버 보안 그룹

권장 인바운드 규칙:

| 포트 | 대상 | 설명 |
|---:|---|---|
| 80 | 0.0.0.0/0 또는 필요한 접근 범위 | 사용자 HTTP 접속 |
| 22 | 내 IP | SSH 관리 접속 |

`8000`은 외부에 열 필요가 없습니다.

## .env 확인

서버 IP 또는 도메인을 `ALLOWED_HOSTS`에 넣어야 합니다.

```env
DEBUG=False
ALLOWED_HOSTS=SERVER_PUBLIC_IP,localhost,127.0.0.1
```

도메인과 HTTPS를 붙인 뒤 CSRF 문제가 생기면 아래처럼 추가합니다.

```env
CSRF_TRUSTED_ORIGINS=https://example.com
```

RunPod Ranker를 쓰는 경우:

```env
RANKER_MODE=runpod
RANKER_URL=https://api.runpod.ai/v2/<endpoint_id>/runsync
RUNPOD_API_KEY=<RunPod API Key>
RANKER_TIMEOUT_SECONDS=90
```

## 배포 명령

프로젝트 루트에서 실행합니다.

```bash
docker compose --env-file .env -f docker/docker-compose.backend.aws.yml down
docker compose --env-file .env -f docker/docker-compose.backend.aws.yml up -d --build
```

상태 확인:

```bash
docker compose -f docker/docker-compose.backend.aws.yml ps
docker compose -f docker/docker-compose.backend.aws.yml logs -f nginx
docker compose -f docker/docker-compose.backend.aws.yml logs -f backend
```

접속 확인:

```text
http://SERVER_PUBLIC_IP/
```

## 포트 충돌 확인

EC2 호스트에 Nginx나 Apache가 직접 설치되어 이미 80 포트를 쓰고 있으면 컨테이너 Nginx가 뜨지 않습니다.

```bash
sudo ss -ltnp | grep ':80'
```

이미 사용 중이면 호스트 Nginx/Apache를 중지하거나, Docker Compose 방식 대신 호스트 Nginx 방식으로 구조를 바꿔야 합니다.

