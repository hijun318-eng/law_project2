variable "aws_region" {
  description = "배포 리전"
  type        = string
  default     = "ap-northeast-2"
}

variable "project_name" {
  description = "리소스 이름에 붙일 프로젝트 식별자"
  type        = string
  default     = "law-project2"
}

variable "vpc_cidr" {
  description = "VPC CIDR 블록"
  type        = string
  default     = "10.0.0.0/16"
}

variable "public_subnet_cidr" {
  description = "Backend/Ranker가 위치할 퍼블릭 서브넷 CIDR"
  type        = string
  default     = "10.0.1.0/24"
}

variable "availability_zone" {
  description = "인스턴스를 배치할 가용영역"
  type        = string
  default     = "ap-northeast-2a"
}

variable "availability_zone_secondary" {
  description = "RDS DB Subnet Group용 두 번째 가용영역 (RDS는 최소 서로 다른 AZ의 서브넷 2개가 필요함). enable_rds=true일 때만 사용"
  type        = string
  default     = "ap-northeast-2c"
}

variable "public_subnet_b_cidr" {
  description = "두 번째 가용영역의 서브넷 CIDR (RDS Subnet Group용). enable_rds=true일 때만 사용"
  type        = string
  default     = "10.0.2.0/24"
}

variable "ssh_allowed_cidr" {
  description = "SSH(22)를 허용할 CIDR (본인 IP/32 권장). 예: 1.2.3.4/32"
  type        = string
}

variable "web_allowed_cidr" {
  description = "Backend 80 포트(nginx)를 허용할 CIDR"
  type        = string
  default     = "0.0.0.0/0"
}

variable "ssh_public_key_path" {
  description = "EC2 키페어에 등록할 로컬 SSH 공개키 경로"
  type        = string
  default     = "~/.ssh/id_rsa.pub"
}

variable "ssh_private_key_path" {
  description = "auto_deploy_backend=true일 때 Backend EC2에 SSH 접속하는 데 쓰는 로컬 개인키 경로 (ssh_public_key_path와 짝이 맞아야 함)"
  type        = string
  default     = "~/.ssh/id_rsa"
}

variable "local_bash_path" {
  description = "local-exec provisioner가 쓸 bash 실행 파일 경로. macOS/Linux는 기본값 \"bash\" 그대로. Windows는 PATH상 System32\\bash.exe(WSL 런처)가 먼저 잡혀서 Git Bash 전체 경로로 override 필요 (예: \"C:/Program Files/Git/usr/bin/bash.exe\")"
  type        = string
  default     = "bash"
}

variable "auto_deploy_backend" {
  description = "true(기본값)면 terraform apply가 Backend EC2에 SSH로 접속해 .env 병합 + vector_db/data 업로드 + deploy_backend.sh 실행까지 자동 수행. false면 기존처럼 수동 scp 필요"
  type        = bool
  default     = true
}

variable "backend_instance_type" {
  description = "Backend EC2 인스턴스 타입"
  type        = string
  default     = "t3.medium"
}

variable "ranker_instance_type" {
  description = "Ranker GPU EC2 인스턴스 타입"
  type        = string
  default     = "g4dn.2xlarge"
}

variable "backend_root_volume_size_gb" {
  description = "Backend 인스턴스 루트 볼륨 크기(GB)"
  type        = number
  default     = 30
}

variable "ranker_root_volume_size_gb" {
  description = "Ranker 인스턴스 루트 볼륨 크기(GB) - DLAMI는 루트가 작으므로 여유 있게"
  type        = number
  default     = 100
}

variable "git_repo_url" {
  description = "애플리케이션 소스가 있는 git 저장소 URL"
  type        = string
  default     = "https://github.com/hijun318-eng/law_project2.git"
}

variable "git_branch" {
  description = "배포할 git 브랜치"
  type        = string
  default     = "main"
}

variable "app_dir" {
  description = "인스턴스 내부에 소스를 clone할 경로"
  type        = string
  default     = "/opt/law_project2"
}

# ── Ranker 배포 방식 선택 ─────────────────────────────────────────
variable "ranker_deployment" {
  description = "Ranker(재랭커)를 어디에 배포할지 선택: \"ec2\" (AWS GPU EC2), \"runpod\" (RunPod Pod), \"runpod_serverless\" (RunPod Serverless Endpoint)"
  type        = string
  default     = "ec2"

  validation {
    condition     = contains(["ec2", "runpod", "runpod_serverless"], var.ranker_deployment)
    error_message = "ranker_deployment는 \"ec2\", \"runpod\", \"runpod_serverless\" 중 하나여야 합니다."
  }
}

# ── RunPod 설정 (ranker_deployment = "runpod"일 때만 사용) ─────────
variable "runpod_api_key" {
  description = "RunPod API 키 (https://www.runpod.io/console/user/settings)"
  type        = string
  default     = ""
  sensitive   = true
}

variable "runpod_ranker_image" {
  description = "RunPod Pod가 pull할 ranker 이미지. docker/Dockerfile.ranker.gpu를 미리 빌드/푸시해야 함 (doc/runpod-ranker-deploy.md 1번). 예: docker.io/<id>/law-ranker:latest"
  type        = string
  default     = ""
}

variable "runpod_gpu_type_ids" {
  # 가격 오름차순 (Community Cloud 기준 대략치, 변동 가능하니 RunPod 콘솔에서 재확인 권장):
  # RTX A4000 ~$0.17/hr < RTX 3090 ~$0.22/hr < RTX A5000 ~$0.27/hr < RTX 4090 ~$0.34/hr
  # runpod_serverless 모드에서 이 소비자용 GPU들이 실제로 Endpoint GPU 목록에 뜨는지는
  # RunPod 콘솔의 Serverless > New Endpoint 화면에서 직접 확인 권장 (문서상 명시적 확정 불가)
  description = "우선순위대로 시도할 RunPod GPU 타입 목록 (앞에서부터 사용 가능한 것을 선택, 가격 오름차순)"
  type        = list(string)
  default = [
    "NVIDIA RTX A4000",
    "NVIDIA GeForce RTX 3090",
    "NVIDIA RTX A5000",
    "NVIDIA GeForce RTX 4090",
  ]
}

variable "runpod_cloud_type" {
  description = "RunPod Cloud 타입: SECURE 또는 COMMUNITY"
  type        = string
  default     = "COMMUNITY"
}

variable "runpod_data_center_ids" {
  description = "RunPod Pod를 배치할 데이터센터 후보 목록 (runpod_use_network_volume=false일 때만 사용, 비우면 제한 없음)"
  type        = list(string)
  default     = []
}

variable "runpod_use_network_volume" {
  description = "Hugging Face 모델 캐시용 RunPod Network Volume 생성 여부 (없으면 Pod 재시작마다 모델 재다운로드)"
  type        = bool
  default     = true
}

variable "runpod_network_volume_data_center_id" {
  description = "Network Volume을 생성할 데이터센터 ID. runpod_use_network_volume=true일 때 필수이며 Pod도 같은 데이터센터에 배치됨. 예: US-CA-2"
  type        = string
  default     = ""
}

variable "runpod_container_disk_gb" {
  description = "RunPod Pod의 컨테이너 디스크 크기(GB, 재시작 시 초기화됨)"
  type        = number
  default     = 20
}

variable "runpod_volume_gb" {
  description = "RunPod Network Volume 크기(GB)"
  type        = number
  default     = 30
}

# ── Ranker 공통 튜닝값 (RunPod Pod 환경변수로 주입, EC2는 .env로 직접 관리) ──
variable "ranker_django_secret_key" {
  description = "RunPod ranker Pod의 DJANGO_SECRET_KEY (ec2 모드에서는 사용 안 함)"
  type        = string
  default     = ""
  sensitive   = true
}

variable "ranker_api_key" {
  description = "Backend↔Ranker 인증 공유 비밀키. RunPod 모드일 때 Pod 환경변수와 Backend .env의 RANKER_API_KEY에 동일한 값을 넣어야 함"
  type        = string
  default     = ""
  sensitive   = true
}

variable "reranker_batch_size" {
  type    = number
  default = 4
}

variable "reranker_max_documents" {
  type    = number
  default = 30
}

variable "reranker_max_chars" {
  type    = number
  default = 1800
}

# ── RunPod Serverless 설정 (ranker_deployment = "runpod_serverless"일 때만 사용) ──
# Template/Endpoint는 공식 runpod/runpod provider(runpod_template/runpod_endpoint 리소스)로
# 관리되므로 콘솔에서 미리 만들 필요가 없음 (terraform apply/destroy가 전체 생명주기를 관리).
variable "runpod_serverless_worker" {
  # "infinity"면 RunPod 공식 워커(runpod-workers/worker-infinity-embedding)를 그대로 pull해서 씀 —
  # 우리 이미지를 빌드/푸시할 필요가 없고 reranker_model 변수로 HF 모델만 지정하면 됨.
  # 단, RunPod 공식 vLLM 워커(runpod/worker-v1-vllm)는 generate 전용이라 CrossEncoder/reranker를
  # 지원하지 않으므로 이 용도로는 worker-infinity-embedding을 씀. Backend .env에도
  # RANKER_BACKEND=runpod_infinity를 맞춰서 설정해야 함 (apps/backend/backend/settings.py 참고).
  # "custom"이면 docker/Dockerfile.ranker.serverless로 직접 빌드한 이미지(runpod_serverless_image)를 씀.
  description = "RunPod Serverless에 어떤 워커를 올릴지: \"infinity\" (RunPod 공식 이미지, 이미지 빌드 불필요) 또는 \"custom\" (직접 빌드한 이미지)"
  type        = string
  default     = "infinity"

  validation {
    condition     = contains(["infinity", "custom"], var.runpod_serverless_worker)
    error_message = "runpod_serverless_worker는 \"infinity\" 또는 \"custom\"이어야 합니다."
  }
}

variable "runpod_infinity_worker_image" {
  description = "runpod_serverless_worker=\"infinity\"일 때 사용할 RunPod 공식 이미지 태그"
  type        = string
  default     = "runpod/worker-infinity-embedding:1.1.4"
}

variable "reranker_model" {
  description = "로드할 HF reranker 모델. custom 워커의 RERANKER_MODEL / infinity 워커의 MODEL_NAMES로 각각 주입됨"
  type        = string
  default     = "Dongjin-kr/ko-reranker"
}

variable "runpod_serverless_image" {
  description = "runpod_serverless_worker=\"custom\"일 때만 사용. docker/Dockerfile.ranker.serverless를 미리 build & push해야 함. 예: docker.io/<id>/law-ranker-serverless:latest"
  type        = string
  default     = ""
}

variable "runpod_serverless_workers_min" {
  description = "최소 워커 수 (0이면 요청 없을 때 완전히 스케일다운, 콜드스타트 발생)"
  type        = number
  default     = 0
}

variable "runpod_serverless_workers_max" {
  description = "최대 워커 수"
  type        = number
  default     = 2
}

variable "runpod_serverless_idle_timeout" {
  description = "요청이 없을 때 워커를 스케일다운하기까지 대기 시간(초)"
  type        = number
  default     = 5
}

# ── AWS RDS (선택, 기본 활성화) ──────────────────────────────────────
# doc/rds-postgres-migration.md의 SQLite→RDS 전환 가이드를 Terraform으로 프로비저닝.
# Backend 코드는 DATABASE_URL이 비어 있으면 자동으로 SQLite를 쓰므로 false로 꺼도 무방.
variable "enable_rds" {
  description = "AWS RDS PostgreSQL 생성 여부. false면 Backend는 SQLite로 동작 (.env의 DATABASE_URL을 비워둠)"
  type        = bool
  default     = true
}

variable "rds_engine_version" {
  description = "RDS PostgreSQL 엔진 버전"
  type        = string
  default     = "16"
}

variable "rds_instance_class" {
  description = "RDS 인스턴스 클래스"
  type        = string
  default     = "db.t4g.micro"
}

variable "rds_allocated_storage_gb" {
  description = "RDS 스토리지 크기(GB)"
  type        = number
  default     = 20
}

variable "rds_db_name" {
  description = "RDS DB 이름 (doc/rds-postgres-migration.md 권장값과 동일)"
  type        = string
  default     = "law_project2"
}

variable "rds_master_username" {
  description = "RDS 마스터 사용자명 (doc/rds-postgres-migration.md 권장값과 동일)"
  type        = string
  default     = "law_user"
}

variable "rds_master_password" {
  description = "비워두면(기본값) random_password로 자동 생성됨 — terraform output -raw rds_master_password로 확인 가능"
  type        = string
  default     = ""
  sensitive   = true
}

variable "rds_backup_retention_days" {
  description = "RDS 자동 백업 보관 일수"
  type        = number
  default     = 1
}

variable "rds_skip_final_snapshot" {
  description = "true(기본값)면 destroy 시 최종 스냅샷 없이 완전 삭제(개발용). 운영 환경이면 false + rds_final_snapshot_identifier 지정 권장"
  type        = bool
  default     = true
}

variable "rds_final_snapshot_identifier" {
  description = "rds_skip_final_snapshot=false일 때 destroy 시 남길 최종 스냅샷 식별자"
  type        = string
  default     = ""
}

# ── vector_db S3 백업/복원 (선택, 기본 활성화) ─────────────────────────
# .github/workflows/deploy-ec2-terraform.yml의 TF_VECTOR_DB_S3_URI secret과 대응
# (기존 운영 서버용 deploy-ec2.yml의 VECTOR_DB_S3_URI와는 별개의 버킷/secret).
variable "enable_vector_db_s3_backup" {
  description = "Chroma vector_db를 S3와 동기화할 버킷 + Backend EC2용 IAM 인스턴스 프로필 생성 여부"
  type        = bool
  default     = true
}

variable "vector_db_s3_bucket_name" {
  description = "비워두면 <project_name>-vector-db-<계정ID>로 자동 생성 (S3 버킷명은 전역에서 유일해야 함)"
  type        = string
  default     = ""
}

variable "vector_db_s3_force_destroy" {
  description = "true(기본값)면 버킷에 객체가 남아있어도 destroy 허용 (개발 편의). 운영 환경이면 false 권장"
  type        = bool
  default     = true
}

variable "vector_db_s3_auto_upload" {
  description = "true(기본값)면 버킷 생성 시 terraform apply가 로컬 vector_db/를 aws cli로 자동 업로드 (최초 1회). false면 수동으로 aws s3 sync 필요"
  type        = bool
  default     = true
}
