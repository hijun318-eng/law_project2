# Terraform으로 AWS 배포

`doc/aws-ec2-two-server-deploy.md` (Backend + Ranker 모두 EC2),
`doc/runpod-ranker-deploy.md` (Backend는 EC2, Ranker는 RunPod Pod), 그리고
RunPod Serverless Endpoint 세 가지 배포 방식을 `ranker_deployment` 변수 하나로
전환할 수 있게 구성한 코드입니다.

```
ranker_deployment = "ec2"               # Backend EC2 + Ranker GPU EC2 (같은 VPC 내부망)
ranker_deployment = "runpod"             # Backend EC2 + Ranker RunPod Pod (인터넷 경유, Bearer 인증)
ranker_deployment = "runpod_serverless"  # Backend EC2 + Ranker RunPod Serverless Endpoint (사용량 기반 과금, 콜드스타트 있음)
```

## 이 코드가 자동화하는 것 / 하지 않는 것

공통 자동화:
- VPC, 서브넷, 인터넷 게이트웨이, 라우팅
- Backend 보안 그룹, EC2 인스턴스, Docker 설치 + git clone + `deploy_backend.sh` 생성
- **AWS RDS PostgreSQL** (`enable_rds`, 기본 활성화) — `doc/rds-postgres-migration.md`의 SQLite→RDS 전환을 그대로 프로비저닝. Backend EC2 보안그룹에서만 5432 허용, `publicly_accessible=false`, 비밀번호는 안 채우면 자동 생성(`random_password`)
- **vector_db S3 백업 버킷 + Backend EC2 IAM 인스턴스 프로필** (`enable_vector_db_s3_backup`, 기본 활성화) — `.github/workflows/deploy-ec2-terraform.yml`이 배포 시마다 `aws s3 sync`로 이 버킷에서 Chroma `vector_db`를 복원하는데, 그 명령이 EC2 내부에서 실행되므로 EC2가 S3를 읽을 수 있는 IAM 역할을 자동으로 붙여줌
- **Backend 앱 배포까지 자동** (`auto_deploy_backend`, 기본 활성화) — `terraform apply`가 Backend EC2에 SSH로 접속해 로컬 `.env`(개인 시크릿)에 `RANKER_URL`/`RANKER_API_KEY`/`RANKER_BACKEND`/`RANKER_MODEL`/`DATABASE_URL`(Terraform이 계산한 값)을 병합하고, `vector_db/`·`data/`와 함께 업로드한 뒤 `deploy_backend.sh`까지 실행함 (`terraform/backend_deploy.tf`). 자세한 내용은 아래 [Backend 앱 배포 자동화](#backend-앱-배포-자동화-auto_deploy_backend) 참고

`ranker_deployment = "ec2"`일 때 추가 자동화:
- Ranker 보안 그룹 (8001은 Backend SG에서만 허용)
- Ranker GPU EC2 인스턴스 (AWS Deep Learning AMI 자동 조회)
- Docker 설치 + git clone + `deploy_ranker.sh` 생성

`ranker_deployment = "runpod"`일 때 추가 자동화:
- RunPod Network Volume (Hugging Face 모델 캐시 영속화)
- RunPod Pod 생성 (이미지, GPU 타입, 포트, 환경변수까지 Terraform이 관리)

`ranker_deployment = "runpod_serverless"`일 때 추가 자동화:
- RunPod Network Volume (선택, 커뮤니티 provider로 생성)
- **Template + Endpoint 생성/추적/삭제** — 공식 `runpod/runpod` provider(alias: `runpod_official`)의 `runpod_template`/`runpod_endpoint` **네이티브 리소스**로 관리. `terraform apply`/`destroy`가 둘 다 온전히 생명주기를 추적한다 (Template도 destroy 시 같이 삭제됨).

`runpod_serverless_worker` 값에 따라 이미지 자체도 다르게 관리됩니다:
- `"infinity"` (**기본값**) — RunPod 공식 워커 [`runpod-workers/worker-infinity-embedding`](https://github.com/runpod-workers/worker-infinity-embedding)를 그대로 pull. **이미지 빌드/푸시가 전혀 필요 없고**, `reranker_model` 변수만 바꾸면 다른 HF reranker 모델로 즉시 전환됩니다.
  - RunPod 공식 vLLM 워커(`runpod/worker-v1-vllm`)는 안 씁니다 — 소스코드([handler.py](https://github.com/runpod-workers/worker-vllm/blob/main/src/handler.py))를 직접 확인해보니 `engine.generate()`만 호출하는 텍스트 생성 전용 구조라 `Dongjin-kr/ko-reranker`같은 CrossEncoder(시퀀스 분류) 모델을 지원하지 않습니다.
- `"custom"` — 기존처럼 `docker/Dockerfile.ranker.serverless`로 직접 빌드한 이미지 사용

⚠️ **공식 provider(`runpod_official`)의 알려진 제약** (스키마 확인 결과):
- `runpod_endpoint`에 `gpu_type_ids`가 없음 — GPU **모델**을 지정할 방법이 없고 `gpu_count`(개수)만 지정 가능. 어떤 GPU가 배정될지는 RunPod가 결정.
- `runpod_endpoint`에 `scaler_type`/`scaler_value`가 없음 — 오토스케일링 전략을 Terraform으로 설정 불가 (RunPod 플랫폼 기본값을 따름).
- `runpod_pod`(Pod 모드, `ranker_deployment = "runpod"`)는 여전히 커뮤니티 provider를 씁니다 — 공식 provider의 Pod 리소스는 `gpu_type_id`/`machine_id`가 스키마엔 있지만 실제 API 요청에 반영되지 않는 오픈 버그([#51](https://github.com/runpod/terraform-provider-runpod/issues/51))가 있어 GPU 지정이 안 되기 때문.

항상 수동으로 해야 하는 것:
- 로컬 `.env` 파일 자체 준비 (`OPENAI_API_KEY`, `NAVER_CLIENT_ID`/`SECRET`, `DJANGO_SECRET_KEY` 등 — `auto_deploy_backend`는 이 파일을 베이스로 병합만 하지, 개인 시크릿까지 대신 만들어주지는 않음)
- (`ec2` 모드) Ranker `.env` 업로드 + `deploy_ranker.sh` 실행 (Ranker는 `auto_deploy_backend` 자동화 대상이 아님, Backend만 해당)
- (`runpod` 모드) `docker/Dockerfile.ranker.gpu` 이미지를 미리 build & push (RunPod는 레지스트리 이미지를 pull하는 구조라 Terraform이 대신할 수 없음)
- (`runpod_serverless` + `runpod_serverless_worker="custom"`) `docker/Dockerfile.ranker.serverless` 이미지를 build & push (`"infinity"`면 이 단계 자체가 없음)
- `auto_deploy_backend=false`로 끈 경우: Backend `.env`/`vector_db/`/`data/` scp + `deploy_backend.sh` 실행 (예전 방식)

## 사전 준비

1. AWS CLI 자격증명 설정 (`aws configure`)
2. Terraform >= 1.5 설치
3. 로컬 SSH 키페어 (`~/.ssh/id_rsa.pub` 등)
4. 본인 공인 IP 확인 (`curl ifconfig.me`) → `ssh_allowed_cidr`에 사용
5. **ec2 모드**: GPU 인스턴스(`g4dn.2xlarge` 등) vCPU 할당량 확인
6. **runpod 모드**:
   - RunPod API 키 발급 (https://www.runpod.io/console/user/settings)
   - `docker build -f docker/Dockerfile.ranker.gpu -t <registry>/law-ranker:latest .. && docker push <registry>/law-ranker:latest` 로 이미지 미리 준비 (`doc/runpod-ranker-deploy.md` 1번 항목과 동일)
7. **runpod_serverless 모드 (`runpod_serverless_worker = "infinity"`, 기본값 — 이미지 빌드 불필요)**:
   - RunPod API 키 발급 (`runpod_api_key` — Template/Endpoint를 관리하는 `runpod_official` provider와 커뮤니티 `runpod` provider가 공통으로 사용)
   - `terraform.tfvars`의 `reranker_model`에 원하는 HF reranker 모델 지정 (기본값 `Dongjin-kr/ko-reranker`)
   - Backend `.env`의 `RANKER_BACKEND`/`RANKER_MODEL`은 `auto_deploy_backend=true`(기본값)면 Terraform이 자동으로 주입하므로 직접 안 건드려도 됨

   **runpod_serverless_worker = "custom"으로 바꾸는 경우** (직접 빌드한 이미지 사용):
   - `docker build -f docker/Dockerfile.ranker.serverless -t <registry>/law-ranker-serverless:latest .. && docker push <registry>/law-ranker-serverless:latest`
   - `terraform.tfvars`의 `runpod_serverless_image`에 위에서 push한 이미지 지정
8. **`auto_deploy_backend`(기본값 true)를 쓰는 경우**:
   - `terraform.tfvars`의 `ssh_private_key_path`가 `ssh_public_key_path`와 짝이 맞는 개인키를 가리켜야 함
   - 로컬 저장소 루트에 `.env`(개인 시크릿), `vector_db/`, `data/`가 미리 준비되어 있어야 함 (`terraform apply`가 이 경로들을 그대로 읽어서 업로드함)

## 사용 순서

```bash
cd terraform
cp terraform.tfvars.example terraform.tfvars
# terraform.tfvars 편집:
#  - ssh_allowed_cidr, ssh_public_key_path (공통)
#  - ranker_deployment = "ec2" 또는 "runpod"
#  - 선택한 모드에 맞는 변수들 채우기

terraform init
terraform plan
terraform apply
```

`apply` 완료 후:

```bash
terraform output
```

## 앱 배포 (apply 이후)

`auto_deploy_backend=true`(기본값)면 **Backend 쪽은 `terraform apply`가 끝나는 시점에 이미 배포 완료 상태**입니다 (.env 병합 + vector_db/data 업로드 + `deploy_backend.sh` 실행까지 자동). 아래는 모드별로 **Ranker 쪽만** 남은 수동 작업 + 동작 확인 방법입니다.

### A. ranker_deployment = "ec2"

```bash
# Ranker: .env 업로드 + GPU 확인 + 배포 (Ranker는 자동화 대상 아님)
scp -i <프라이빗키> ../.env ubuntu@$(terraform output -raw ranker_public_ip):/opt/law_project2/
ssh -i <프라이빗키> ubuntu@$(terraform output -raw ranker_public_ip)
nvidia-smi
/opt/law_project2/deploy_ranker.sh
```

### B. ranker_deployment = "runpod"

Pod는 `terraform apply` 시점에 이미 생성/실행되어 있습니다 (env 변수도 Terraform이 주입 완료). Backend `.env`의 `RANKER_URL`/`RANKER_API_KEY`도 자동 반영됩니다.

```bash
# Pod 상태 및 접속 URL 확인
terraform output ranker_runpod_proxy_url
terraform output ranker_runpod_pod_id

# 동작 확인 (RANKER_API_KEY는 terraform.tfvars의 ranker_api_key와 동일한 값)
curl -X POST "$(terraform output -raw ranker_runpod_proxy_url)" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <ranker_api_key 값>" \
  -d '{"query":"부당해고","documents":["해고 정당성 관련 판례 요약"]}'
```

### C. ranker_deployment = "runpod_serverless"

`terraform apply` 한 번으로 Template과 Endpoint가 모두 생성/연결되고, Backend `.env`의 `RANKER_URL`/`RANKER_API_KEY`/`RANKER_BACKEND`/`RANKER_MODEL`도 자동 반영됩니다.

**`runpod_serverless_worker = "infinity"` (기본값)인 경우:**

```bash
terraform output ranker_runpod_serverless_url
terraform output ranker_runpod_serverless_endpoint_id

# 동작 확인 (Authorization은 커스텀 비밀키가 아니라 RunPod 계정 API 키!)
# 요청 필드가 query/docs (documents 아님), model에 reranker_model과 같은 값 필요
curl -X POST "$(terraform output -raw ranker_runpod_serverless_url)" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <runpod_api_key 값>" \
  -d '{"input": {"model":"Dongjin-kr/ko-reranker","query":"부당해고","docs":["해고 정당성 관련 판례 요약"],"return_docs":false}}'
# 정상 응답 예: {"id":"...","status":"COMPLETED","output":{"scores":[0.87]}}
```

**`runpod_serverless_worker = "custom"`인 경우:**

```bash
terraform output ranker_runpod_serverless_url

curl -X POST "$(terraform output -raw ranker_runpod_serverless_url)" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <runpod_api_key 값>" \
  -d '{"input": {"query":"부당해고","documents":["해고 정당성 관련 판례 요약"]}}'
# 정상 응답 예: {"output":{"results":[{"index":0,"score":0.87}]}}
```

⚠️ `worker-infinity-embedding`의 실제 응답 JSON 구조(`output.scores`)는 공식 README 예시를 근거로 추정한 것이라, 처음 붙일 때 위 curl로 한 번 직접 확인해보는 걸 권장합니다.

첫 요청은 워커가 콜드 스타트(모델 로딩)하느라 느릴 수 있습니다 (`runpod_serverless_workers_min > 0`으로 두면 상시 워커를 유지해 콜드스타트를 없앨 수 있지만 그만큼 계속 과금됩니다).

## Backend 앱 배포 자동화 (`auto_deploy_backend`)

`terraform apply` 흐름 안에서 `null_resource.backend_app_deploy`(`terraform/backend_deploy.tf`)가 Backend EC2에 SSH로 접속해 순서대로 진행합니다:

1. user_data(cloud-init)가 끝날 때까지 대기 (`.bootstrap_complete` 마커 파일 생성 확인)
2. 로컬 `../.env`를 베이스로, `RANKER_URL`/`RANKER_API_KEY`/`RANKER_BACKEND`/`RANKER_MODEL`/`DATABASE_URL` 등 **이번 apply로 새로 생성된 인프라 값**만 Terraform이 계산해 덮어쓴 `.env`를 로컬에 생성 (`terraform/.generated-backend.env`, gitignore 대상)
3. 그 `.env` + `vector_db/` + `data/`를 인스턴스로 업로드
4. `deploy_backend.sh` 실행

**전제조건**
- `ssh_private_key_path`가 `ssh_public_key_path`와 짝이 맞는 개인키를 가리켜야 함
- 저장소 루트에 `.env`, `vector_db/`, `data/`가 미리 준비되어 있어야 함

**다시 배포하고 싶을 때** (로컬 `.env`/`vector_db`를 바꾼 뒤): 이 리소스는 인스턴스가 재생성될 때만 재실행되므로, 강제로 다시 돌리려면
```bash
terraform apply -replace=null_resource.backend_app_deploy[0]
```

**끄고 싶으면** `auto_deploy_backend = false`로 두고, 아래처럼 수동으로 진행하세요 (`<app_dir>`은 변수 값 그대로 — 기본값 `/opt/law_project2`, 이 프로젝트는 GitHub Actions와 경로를 맞추려고 `/home/ubuntu/law_project2`로 재정의해둠):

```bash
# .env에는 RANKER_URL/RANKER_API_KEY/RANKER_BACKEND/RANKER_MODEL/DATABASE_URL을
# 모드에 맞게 직접 반영해야 함 (위 A/B/C 섹션의 terraform output 값 참고)
scp -i <프라이빗키> -r ../.env ../vector_db ../data ubuntu@$(terraform output -raw backend_public_ip):<app_dir>/
ssh -i <프라이빗키> ubuntu@$(terraform output -raw backend_public_ip) '<app_dir>/deploy_backend.sh'
```

⚠️ `file`/`remote-exec` provisioner는 HashiCorp가 "최후의 수단"으로만 권장하는 기능이라, SSH 연결이 불안정하거나 `vector_db`/`data`가 매우 크면 `terraform apply`가 오래 걸리거나 타임아웃될 수 있습니다. 이 경우 `auto_deploy_backend = false`로 끄고 수동 진행하세요.

### 접속 확인 (공통)

nginx가 80 포트로 서빙하므로 포트 번호 없이 접속합니다 (backend 컨테이너의 8000은 호스트에 노출되지 않음).

```
http://<backend_public_ip>
```

## AWS RDS / vector_db S3 백업 (기본 활성화)

`enable_rds`, `enable_vector_db_s3_backup` 둘 다 기본값 `true`라 `terraform apply`만으로 함께 생성됩니다.

```bash
# RDS 접속 정보 확인
terraform output rds_endpoint
terraform output -raw rds_master_password
terraform output -raw database_url   # Backend .env의 DATABASE_URL에 그대로 사용

# S3 버킷 확인
terraform output vector_db_s3_bucket_name
terraform output vector_db_s3_uri     # GitHub Actions TF_VECTOR_DB_S3_URI secret에 그대로 사용
```

- Backend `.env`에 `DATABASE_URL=<terraform output -raw database_url 값>` 반영 후 `deploy_backend.sh` 재실행 (컨테이너 시작 시 `migrate --noinput`이 자동 실행되어 RDS에 테이블이 생성됨).
- **S3 최초 업로드는 자동입니다.** `vector_db_s3_auto_upload=true`(기본값)면 버킷이 생성되는 그 `terraform apply` 실행 시, `terraform apply`를 돌리는 바로 그 머신에서 로컬 `vector_db/` → S3로 `aws s3 sync`가 자동 실행됩니다 (`.github/workflows/deploy-ec2-terraform.yml`은 반대 방향인 S3→EC2만 하므로, 최초 시드는 이렇게 채워야 함). 이 머신에 `aws cli` + S3 쓰기 권한이 있는 자격증명이 있어야 하고, `vector_db/`가 없으면 건너뛰고 경고만 남깁니다.
  - 버킷이 이미 있는 상태에서 로컬 `vector_db/`를 바꾼 뒤 다시 올리고 싶다면 (평소엔 재실행 안 됨):
    ```bash
    terraform apply -replace=null_resource.vector_db_initial_upload[0]
    ```
  - 자동 업로드를 아예 원치 않으면 `vector_db_s3_auto_upload = false`로 끄고 직접 `aws s3 sync vector_db/ "$(terraform output -raw vector_db_s3_uri)/"` 실행
- 이 Terraform으로 만든 Backend EC2는 **기존 운영 서버(52.79.204.190)와는 완전히 별개**이므로, GitHub Actions도 전용 브랜치(`deploy-terraform`) + 전용 워크플로우 `.github/workflows/deploy-ec2-terraform.yml`(기존 `deploy` 브랜치/`deploy-ec2.yml`은 그대로 둠)을 씁니다. 리포지토리 Secrets에 `TF_EC2_HOST=$(terraform output -raw backend_public_ip)`, `TF_EC2_USER=ubuntu`, `TF_EC2_SSH_KEY=<ssh_private_key_path 파일 내용>`, `TF_PROD_ENV=<.env 전체 내용>`, `TF_VECTOR_DB_S3_URI=$(terraform output -raw vector_db_s3_uri)`를 등록하면 됩니다 (기존 `EC2_HOST` 등과 이름이 겹치지 않도록 `TF_` 접두사를 붙임). 브랜치와 시크릿을 모두 분리했기 때문에 `deploy-terraform`에 push해도 기존 운영 서버는 전혀 영향받지 않습니다.
  - **최초 1회는 수동 빌드가 필요합니다** — 이 워크플로우는 `--no-build`로 이미 빌드된 이미지를 재사용하는 방식이라, 새 서버엔 아직 이미지가 없습니다. `apply` 직후 한 번 SSH 접속해서 `~/law_project2/deploy_backend.sh`를 실행해 최초 이미지를 만들어두세요. 그 이후 코드가 바뀔 때마다는 `deploy-terraform` 브랜치 push만으로 충분합니다 (`docker-compose.backend.terraform.yml`이 `apps/backend`를 볼륨 마운트하므로 대부분의 코드 변경은 재빌드 없이 반영됨 — `requirements.txt`가 바뀌는 경우는 이미지 재빌드가 필요하니 그때는 다시 수동으로 `deploy_backend.sh` 실행).
  - `docker-compose.backend.aws.yml`/`docker/nginx.conf`(기존 운영 서버 전용, IP/도메인 하드코딩)와 `docker-compose.backend.terraform.yml`/`docker/nginx.terraform.conf`(이 Terraform 전용, HTTP만·하드코딩 없음)는 서로 다른 파일이라 어느 쪽을 건드려도 다른 서버에 영향이 없습니다.

`enable_rds`/`enable_vector_db_s3_backup`을 `false`로 끄면 해당 리소스 자체가 안 만들어지고, Backend는 기존처럼 SQLite + 수동 `vector_db` scp 방식으로 동작합니다.

## 모드 전환 시 주의

`ranker_deployment` 값을 바꿔서 `terraform apply`하면:
- `ec2` → `runpod`: 기존 Ranker EC2/SG는 삭제되고 RunPod Pod가 새로 생성됩니다.
- `runpod` → `ec2`: 기존 RunPod Pod/Volume은 삭제되고 (Network Volume 삭제 시 캐시된 모델도 함께 사라짐) EC2가 새로 생성됩니다.
- 두 경우 모두 Backend는 in-place로 유지되지만 `.env`의 `RANKER_URL`/`RANKER_API_KEY`는 새 값으로 직접 갱신하고 `deploy_backend.sh`를 재실행해야 합니다.
- `runpod_serverless_worker`를 `"infinity"` ↔ `"custom"`으로 바꾸면 `runpod_template` 리소스의 `image_name`/`env`가 바뀌므로 Terraform이 in-place update로 반영합니다. Backend `.env`의 `RANKER_BACKEND`/`RANKER_MODEL`도 그에 맞게 같이 바꿔야 합니다.

## 리소스 정리

```bash
terraform destroy
```

- `ec2` 모드: GPU EC2는 켜두는 동안 계속 과금되므로 사용하지 않을 때는 `destroy` 권장
- `runpod` 모드: Pod는 사용 시간 기반 과금이라 상대적으로 저렴하지만, Network Volume은 별도로 저장 용량만큼 과금됩니다
- `runpod_serverless` 모드: 워커가 0으로 스케일다운되면 유휴 상태에선 거의 과금되지 않지만(`workers_min=0` 기준), Network Volume은 계속 과금됩니다. Template/Endpoint 모두 Terraform 네이티브 리소스라 `destroy` 시 함께 정리됩니다.
- `enable_rds`: 기본값(`rds_skip_final_snapshot=true`)이면 최종 스냅샷 없이 완전 삭제됩니다 — 운영 데이터가 있다면 destroy 전에 백업하거나 `rds_skip_final_snapshot=false`로 바꿔서 스냅샷을 남기세요.
- `enable_vector_db_s3_backup`: 기본값(`vector_db_s3_force_destroy=true`)이면 버킷 안 내용물까지 통째로 삭제됩니다.

## 원격 state (선택)

여러 명이 같이 작업하거나 CI에서 apply할 계획이라면 `providers.tf`의 `backend "s3"` 블록 주석을 해제하고 S3 버킷 + DynamoDB 락 테이블을 먼저 만든 뒤 `terraform init -migrate-state`를 실행하세요.
