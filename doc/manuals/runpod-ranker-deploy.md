# RunPod Pod로 Ranker 이전 가이드

AWS GPU EC2(`g4dn.2xlarge`~`g5.2xlarge`)로 띄우던 ranker를 RunPod Pod로 옮기는 방법입니다.
기존 `docker/Dockerfile.ranker.gpu` + Django/gunicorn 구조를 그대로 재사용하고,
컨테이너가 도는 장소만 AWS에서 RunPod로 바뀝니다.

```text
[Backend EC2 (AWS, CPU)]              [RunPod Pod (GPU)]
Django backend                        Django ranker API
vector_db / data 보유                  Dongjin-kr/ko-reranker
RANKER_URL=https://<pod-id>-8001      CUDA PyTorch
   .proxy.runpod.net/rerank/
RANKER_API_KEY=<공유 비밀키>

        인터넷 경유 (같은 VPC 아님) + Authorization: Bearer 인증
```

AWS 내부망 통신과 다른 점: 지금까지는 backend↔ranker가 같은 VPC 내부망이라 인증 없이 호출했지만,
RunPod Pod는 퍼블릭 프록시 URL로 노출되므로 `Authorization: Bearer <RANKER_API_KEY>` 헤더로 요청을 검증합니다
(RunPod Serverless(runsync)와 동일한 인증 방식이며, `apps/ranker/ranker/views.py`,
`apps/backend/engine/nodes/retrieval.py`에 이미 반영됨).

## 1. 이미지 빌드 & 푸시

RunPod Pod는 Docker Hub(또는 다른 레지스트리)의 이미지를 pull해서 띄웁니다. 로컬/CI에서 빌드 후 푸시합니다.

```bash
docker build -f docker/Dockerfile.ranker.gpu -t <dockerhub-id>/law-ranker:latest ..
docker push <dockerhub-id>/law-ranker:latest
```

비공개 저장소를 쓰면 RunPod 콘솔에서 레지스트리 자격증명을 별도로 등록해야 합니다.

## 2. RunPod Pod 생성

RunPod 콘솔 → **Pods → Deploy** → **Custom Template**에서:

- **Container Image**: `<dockerhub-id>/law-ranker:latest`
- **GPU**: 워크로드가 작으므로(요청당 최대 30문서·1800자·batch 4) 저가형 GPU로 충분 — RTX A4000/A5000 등부터 시작해서 지연시간 보고 조정
- **Expose HTTP Ports**: `8001` 체크 (RunPod가 `https://<pod-id>-8001.proxy.runpod.net` 프록시 URL을 발급)
- **Container Disk**: 기본값으로 충분 (모델은 아래 Volume에 캐시)
- **Volume**: Network Volume을 만들어 `/root/.cache/huggingface`에 마운트 — 안 하면 Pod를 재시작할 때마다 `Dongjin-kr/ko-reranker` 모델을 다시 다운로드합니다.

### 환경 변수 (Pod 템플릿의 Environment Variables에 입력)

```env
DJANGO_SETTINGS_MODULE=ranker.settings
DJANGO_SECRET_KEY=<임의의 긴 문자열>
DEBUG=False
ALLOWED_HOSTS=*
RERANKER_DEVICE=cuda
RERANKER_BATCH_SIZE=4
RERANKER_MAX_DOCUMENTS=30
RERANKER_MAX_CHARS=1800
RANKER_API_KEY=<backend와 공유할 임의의 긴 문자열>
```

`ALLOWED_HOSTS=*`인 이유: RunPod 프록시가 매번 다른 호스트명으로 전달할 수 있어 고정 IP/도메인을 미리 알기 어렵습니다.
대신 `RANKER_API_KEY`로 요청을 검증하므로 인증 공백은 없습니다.

Pod의 CMD(gunicorn `--workers 1 --threads 1 --preload`)는 그대로 둡니다 — GPU 메모리에 모델이 워커마다 복제되는 걸 막기 위한 설정이라 RunPod에서도 동일하게 유효합니다.

## 3. 통신 확인

Pod가 `Running` 상태가 되면 콘솔에 프록시 URL이 표시됩니다.

```bash
curl -X POST https://<pod-id>-8001.proxy.runpod.net/rerank/ \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <RANKER_API_KEY와 동일한 값>" \
  -d '{"query":"부당해고","documents":["해고 정당성 관련 판례 요약"]}'
```

정상 응답:

```json
{"scores":[0.1234],"count":1}
```

`Authorization` 헤더를 빼거나 값이 틀리면 `{"error":"unauthorized"}` (401)이 반환되는지도 확인합니다.

## 4. Backend EC2 `.env` 수정

```env
RANKER_URL=https://<pod-id>-8001.proxy.runpod.net/rerank/
RANKER_API_KEY=<Pod에 설정한 값과 동일>
RANKER_TIMEOUT_SECONDS=60
```

크로스 클라우드 네트워크 홉이 추가되고 CPU 대비는 아니지만 AWS 내부망보다는 느리므로,
기존 `RANKER_TIMEOUT_SECONDS=30`보다 여유 있게 늘려두는 걸 권장합니다.

이후 backend 재배포:

```bash
docker compose --env-file .env -f docker/docker-compose.backend.aws.yml up -d --build
```

## 5. 기존 AWS GPU 인스턴스 정리

RunPod 쪽 동작을 며칠 검증한 뒤, 기존 `docker-compose.ranker-gpu.aws.yml`로 띄운 AWS GPU EC2 인스턴스를 종료합니다.
이게 이번 이전 작업의 실제 비용 절감 포인트입니다 (GPU EC2 24시간 과금 → RunPod Pod 사용량 기반 과금).

## 트러블슈팅

- **401 unauthorized**: backend `.env`의 `RANKER_API_KEY`와 RunPod Pod 환경변수의 `RANKER_API_KEY`가 다름
- **첫 요청이 유독 느림**: Pod가 재시작되면서 모델을 다시 로딩 중일 가능성 — Network Volume이 제대로 마운트됐는지, 매번 재다운로드하고 있지 않은지 Pod 로그 확인
- **타임아웃**: `RANKER_TIMEOUT_SECONDS`를 늘리거나, RunPod GPU 티어를 한 단계 올려서 추론 속도 확인
- **프록시 URL 접속 안 됨**: Pod 상태가 `Running`인지, 8001 포트가 "Expose HTTP Ports"에 체크됐는지 확인
