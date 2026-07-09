terraform {
  required_version = ">= 1.5.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
    # rds_master_password를 안 채웠을 때 자동 생성용 (enable_rds=true일 때만 사용)
    random = {
      source  = "hashicorp/random"
      version = "~> 3.6"
    }
    # runpod_deployment = "runpod"(Pod) 모드 전용. 이 provider의 runpod_pod 리소스는
    # gpu_type_id/machine_id를 실제 API 요청에 반영하지 못하는 활성 버그(#51)가 있지만,
    # Pod 모드에서는 다른 대안이 없어 그대로 사용.
    runpod = {
      source  = "decentralized-infrastructure/runpod"
      version = "~> 1.0"
    }
    # runpod_deployment = "runpod_serverless" 모드 전용(alias: runpod-official).
    # 공식 provider로, Template/Endpoint의 Create가 HTTP 201을 거부하던 버그(CE-1681)가
    # v1.0.8(2026-07-01)에서 수정되어 실사용 가능. 단 이 provider는 network_volume
    # 리소스가 없고(위 community provider로 대체), endpoint에 gpu_type_ids/scaler
    # 설정이 없음(GPU 모델 지정·오토스케일링 전략 불가, gpu_count만 지정 가능).
    runpod-official = {
      source  = "runpod/runpod"
      version = "~> 1.0"
    }
  }

  # 원격 state를 쓰려면 아래 주석을 해제하고 값을 채운 뒤
  # `terraform init -migrate-state`를 실행하세요.
  # backend "s3" {
  #   bucket         = "law-project2-terraform-state"
  #   key            = "law-project2/terraform.tfstate"
  #   region         = "ap-northeast-2"
  #   dynamodb_table = "law-project2-terraform-lock"
  #   encrypt        = true
  # }
}

provider "aws" {
  region = var.aws_region
}

# ranker_deployment != "runpod"/"runpod_serverless"일 때는 사용되지 않지만, provider 자체는
# 항상 선언되어 있어야 함. runpod_api_key가 비어 있어도 관련 리소스가 없으면(count=0) 실제
# API 호출은 발생하지 않음.
provider "runpod" {
  api_key = var.runpod_api_key
}

provider "runpod-official" {
  api_key = var.runpod_api_key
}
