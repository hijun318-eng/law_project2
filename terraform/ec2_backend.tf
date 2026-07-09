locals {
  # ranker_deployment에 따라 backend user_data에 넘길 연결 안내 문구 (사람이 읽는 안내문)
  ranker_connection_note = (
    var.ranker_deployment == "ec2"
    ? "http://${aws_instance.ranker[0].private_ip}:8001/rerank/ (같은 VPC 내부망, 인증 불필요, RANKER_API_KEY 비워둠)"
    : var.ranker_deployment == "runpod"
    ? "RunPod Pod - terraform output ranker_runpod_proxy_url 확인 후 .env의 RANKER_URL/RANKER_API_KEY에 반영 (Authorization: Bearer 인증 필요, RANKER_API_KEY는 backend/ranker가 공유하는 임의의 비밀키)"
    : (
      var.runpod_serverless_worker == "infinity"
      ? "RunPod Serverless(infinity) - terraform output ranker_runpod_serverless_url 확인 후 .env에 RANKER_URL/RANKER_API_KEY(=RunPod 계정 API 키)/RANKER_BACKEND=runpod_infinity/RANKER_MODEL=${var.reranker_model} 반영"
      : "RunPod Serverless(custom) - terraform output ranker_runpod_serverless_url 확인 후 .env에 RANKER_URL/RANKER_API_KEY(=RunPod 계정 API 키) 반영. RANKER_BACKEND는 기본값(custom) 유지"
    )
  )

  # 위 ranker_connection_note를 사람이 읽는 대신, null_resource.backend_app_deploy가
  # .env에 실제로 주입할 key=value 형태로 계산한 값 (backend_deploy.tf에서 사용)
  ranker_env_overrides = (
    var.ranker_deployment == "ec2"
    ? {
      RANKER_URL     = "http://${aws_instance.ranker[0].private_ip}:8001/rerank/"
      RANKER_API_KEY = ""
      RANKER_BACKEND = "custom"
    }
    : var.ranker_deployment == "runpod"
    ? {
      RANKER_URL     = "https://${runpod_pod.ranker[0].id}-8001.proxy.runpod.net/rerank/"
      RANKER_API_KEY = var.ranker_api_key
      RANKER_BACKEND = "custom"
    }
    : (
      var.runpod_serverless_worker == "infinity"
      ? {
        RANKER_URL     = "https://api.runpod.ai/v2/${runpod_endpoint.ranker[0].id}/runsync"
        RANKER_API_KEY = var.runpod_api_key
        RANKER_BACKEND = "runpod_infinity"
        RANKER_MODEL   = var.reranker_model
      }
      : {
        RANKER_URL     = "https://api.runpod.ai/v2/${runpod_endpoint.ranker[0].id}/runsync"
        RANKER_API_KEY = var.runpod_api_key
        RANKER_BACKEND = "custom"
      }
    )
  )

  db_env_overrides = var.enable_rds ? {
    DATABASE_URL    = "postgresql://${var.rds_master_username}:${var.rds_master_password != "" ? var.rds_master_password : random_password.rds[0].result}@${aws_db_instance.main[0].address}:5432/${var.rds_db_name}"
    DB_CONN_MAX_AGE = "600"
    DB_SSL_REQUIRE  = "False"
  } : {}

  backend_env_overrides = merge(local.ranker_env_overrides, local.db_env_overrides)
}

resource "aws_instance" "backend" {
  ami                    = data.aws_ami.ubuntu.id
  instance_type          = var.backend_instance_type
  subnet_id              = aws_subnet.public.id
  vpc_security_group_ids = [aws_security_group.backend.id]
  key_name               = aws_key_pair.main.key_name
  iam_instance_profile   = var.enable_vector_db_s3_backup ? aws_iam_instance_profile.backend[0].name : null

  root_block_device {
    volume_size = var.backend_root_volume_size_gb
    volume_type = "gp3"
  }

  # ec2 모드면 ranker[0].private_ip를 참조하므로 Terraform이 ranker를 먼저 생성함 (암묵적 의존성)
  user_data = templatefile("${path.module}/user_data/backend.sh.tftpl", {
    git_repo_url           = var.git_repo_url
    git_branch             = var.git_branch
    app_dir                = var.app_dir
    ranker_connection_note = local.ranker_connection_note
  })

  tags = {
    Name = "${var.project_name}-backend"
  }
}
