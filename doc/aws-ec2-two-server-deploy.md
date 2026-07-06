# AWS EC2 2대 분리 배포 가이드

이 문서는 Django 백엔드와 GPU 기반 랭커를 서로 다른 EC2 인스턴스에 배포하는 방법을 정리한 문서입니다.

구조는 다음과 같습니다.

```text
[Backend EC2]
Django backend
vector_db / data 보유
RANKER_URL=http://Ranker-Private-IP:8001

        VPC 내부 통신

[Ranker GPU EC2]
Django ranker API
Dongjin-kr/ko-reranker
CUDA PyTorch
```

## 1. 인스턴스 구성

### Backend EC2

- 추천 타입: `t3.large`
- 최소 테스트용: `t3.medium`
- 역할:
  - 사용자 웹 화면 제공
  - Django API 실행
  - Chroma `vector_db` 검색
  - OpenAI API 호출
  - Ranker EC2로 rerank 요청 전송

### Ranker GPU EC2

- 추천 타입: `g4dn.2xlarge` 또는 `g5.2xlarge`
- 최소 테스트용: `g4dn.xlarge`
- 역할:
  - `Dongjin-kr/ko-reranker` CrossEncoder 모델 실행
  - `/rerank/` API 제공

메모리 문제가 있었던 경우에는 `g4dn.xlarge`보다 `g4dn.2xlarge` 이상을 권장합니다.

## 2. 보안 그룹

### Backend EC2 보안 그룹

허용 포트:

```text
22    SSH        내 IP만 허용
8000  Backend    내 IP 또는 로드밸런서에서 접근 허용
```

### Ranker GPU EC2 보안 그룹

허용 포트:

```text
22    SSH        내 IP만 허용
8001  Ranker     Backend EC2의 보안 그룹 또는 Private IP만 허용
```

중요: Ranker의 `8001` 포트는 외부 전체 공개하지 않는 것이 좋습니다.

## 3. Backend EC2 준비

프로젝트 루트에 아래 파일과 폴더가 있어야 합니다.

```text
.env
vector_db/
data/
```

`vector_db`는 실제 상담 시 Chroma가 읽는 벡터DB입니다.

`data/cache/sac`는 벡터DB를 재생성하거나 확인할 때 필요합니다. 이미 완성된 `vector_db`가 있으면 상담 실행 자체에는 `vector_db`가 더 직접적으로 중요합니다.

### Backend `.env` 예시

```env
OPENAI_API_KEY=...
NAVER_CLIENT_ID=...
NAVER_CLIENT_SECRET=...
DJANGO_SECRET_KEY=...
DEBUG=False
ALLOWED_HOSTS=BACKEND_PUBLIC_IP,localhost,127.0.0.1
RANKER_URL=http://RANKER_PRIVATE_IP:8001
```

`RANKER_PRIVATE_IP`에는 Ranker GPU EC2의 private IP를 넣습니다.

### Backend 실행

프로젝트 루트에서 실행합니다.

```bash
docker compose --env-file .env -f docker/docker-compose.backend.aws.yml up -d --build
docker compose --env-file .env -f docker/docker-compose.backend.aws.yml logs -f
```

접속 확인:

```text
http://BACKEND_PUBLIC_IP:8000
```

## 4. Ranker GPU EC2 준비

Ranker EC2는 GPU를 Docker 컨테이너에서 사용할 수 있어야 합니다.

가능하면 NVIDIA/CUDA가 준비된 AMI를 사용합니다. 직접 설치하는 경우에는 NVIDIA driver와 NVIDIA Container Toolkit 설치가 필요합니다.

Deep Learning AMI는 루트 디스크가 작고 `/opt/dlami/nvme`에 큰 임시 디스크가 붙어 있는 경우가 많습니다. 이 프로젝트의 ranker compose는 Hugging Face 모델 캐시를 아래 경로에 저장하도록 설정했습니다.

```text
/opt/dlami/nvme/huggingface
```

따라서 실행 전에 디렉터리를 만들어둡니다.

```bash
sudo mkdir -p /opt/dlami/nvme/huggingface
sudo chown -R ubuntu:ubuntu /opt/dlami/nvme/huggingface
```

GPU 확인:

```bash
nvidia-smi
```

Docker에서 GPU 확인:

```bash
docker run --rm --gpus all nvidia/cuda:12.4.1-base-ubuntu22.04 nvidia-smi
```

### Ranker `.env` 예시

```env
DJANGO_SECRET_KEY=...
DEBUG=False
ALLOWED_HOSTS=RANKER_PRIVATE_IP,RANKER_PUBLIC_IP,localhost,127.0.0.1
RERANKER_BATCH_SIZE=4
RERANKER_MAX_DOCUMENTS=30
RERANKER_MAX_CHARS=1800
```

### Ranker 실행

프로젝트 루트에서 실행합니다.

```bash
docker compose -f docker/docker-compose.ranker-gpu.aws.yml up -d --build
docker compose -f docker/docker-compose.ranker-gpu.aws.yml logs -f
```

최초 실행 시 Hugging Face 모델 다운로드와 로딩 때문에 시간이 걸릴 수 있습니다.

### Ranker warmup

모델을 미리 한 번 로딩하기 위해 Ranker EC2에서 아래 요청을 실행합니다.

```bash
curl -X POST http://localhost:8001/rerank/ \
  -H "Content-Type: application/json" \
  -d '{"query":"부당해고","documents":["해고 정당성 관련 판례 요약"]}'
```

정상 응답 예시:

```json
{"scores":[0.1234],"count":1}
```

## 5. 메모리 문제 대응

Ranker는 CrossEncoder 모델을 사용하므로 worker 수와 batch size가 중요합니다.

현재 GPU ranker compose는 Gunicorn worker를 1개만 사용합니다. worker를 늘리면 모델이 worker마다 복제되어 RAM 또는 VRAM이 터질 수 있습니다.

기본값:

```env
RERANKER_BATCH_SIZE=4
RERANKER_MAX_DOCUMENTS=30
RERANKER_MAX_CHARS=1800
```

메모리 문제가 발생하면 먼저 아래처럼 낮춥니다.

```env
RERANKER_BATCH_SIZE=2
RERANKER_MAX_CHARS=1200
```

안정적으로 동작하면 이후 `RERANKER_BATCH_SIZE=8` 정도까지 올려볼 수 있습니다.

## 6. 배포 순서

권장 순서는 다음과 같습니다.

1. Ranker GPU EC2 생성
2. Ranker 보안 그룹에서 `8001`을 Backend EC2만 접근 가능하게 설정
3. Ranker EC2에 Docker, NVIDIA driver, NVIDIA Container Toolkit 준비
4. Ranker compose 실행
5. Ranker warmup 요청으로 `/rerank/` 정상 동작 확인
6. Backend EC2 생성
7. Backend EC2에 `.env`, `vector_db`, `data` 배치
8. Backend `.env`의 `RANKER_URL`을 Ranker private IP로 설정
9. Backend compose 실행
10. 브라우저에서 `http://BACKEND_PUBLIC_IP:8000` 접속 확인

## 7. 빠른 장애 확인

### Backend에서 Ranker 연결 확인

Backend EC2에서 실행:

```bash
curl -X POST http://RANKER_PRIVATE_IP:8001/rerank/ \
  -H "Content-Type: application/json" \
  -d '{"query":"임금체불","documents":["임금체불 관련 판례 요약"]}'
```

응답이 오지 않으면 보안 그룹, private IP, Ranker 컨테이너 상태를 확인합니다.

### Ranker 컨테이너 로그 확인

```bash
docker compose -f docker/docker-compose.ranker-gpu.aws.yml logs -f
```

### Backend 컨테이너 로그 확인

```bash
docker compose --env-file .env -f docker/docker-compose.backend.aws.yml logs -f
```

### OOM으로 죽는 경우

Ranker `.env`에서 먼저 아래 값을 낮춥니다.

```env
RERANKER_BATCH_SIZE=2
RERANKER_MAX_CHARS=1200
```

그 다음 재시작합니다.

```bash
docker compose -f docker/docker-compose.ranker-gpu.aws.yml down
docker compose -f docker/docker-compose.ranker-gpu.aws.yml up -d --build
```

### 모델 다운로드 중 디스크 부족이 나는 경우

아래처럼 루트 디스크가 거의 꽉 차 있고 `/opt/dlami/nvme`에 여유가 있다면 정상적인 상황입니다.

```bash
df -h / /opt/dlami/nvme
```

Docker build cache를 정리합니다.

```bash
docker builder prune -af
```

그 다음 ranker compose를 다시 실행합니다.
