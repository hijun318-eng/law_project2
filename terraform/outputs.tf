output "backend_public_ip" {
  description = "Backend EC2 퍼블릭 IP (브라우저 접속용)"
  value       = aws_instance.backend.public_ip
}

output "backend_private_ip" {
  value = aws_instance.backend.private_ip
}

output "ranker_deployment_mode" {
  value = var.ranker_deployment
}

output "ranker_private_ip" {
  description = "ec2 모드일 때만 값이 있음. Backend .env의 RANKER_URL에 사용"
  value       = var.ranker_deployment == "ec2" ? aws_instance.ranker[0].private_ip : null
}

output "ranker_public_ip" {
  description = "ec2 모드일 때만 값이 있음 (SSH 접속용)"
  value       = var.ranker_deployment == "ec2" ? aws_instance.ranker[0].public_ip : null
}

output "ranker_runpod_pod_id" {
  description = "runpod(Pod) 모드일 때만 값이 있음"
  value       = var.ranker_deployment == "runpod" ? runpod_pod.ranker[0].id : null
}

output "ranker_runpod_proxy_url" {
  description = "runpod(Pod) 모드일 때만 값이 있음. Backend .env의 RANKER_URL에 그대로 사용 (뒤에 /rerank/ 포함)"
  value       = var.ranker_deployment == "runpod" ? "https://${runpod_pod.ranker[0].id}-8001.proxy.runpod.net/rerank/" : null
}

output "ranker_runpod_serverless_endpoint_id" {
  description = "runpod_serverless 모드일 때만 값이 있음"
  value       = var.ranker_deployment == "runpod_serverless" ? runpod_endpoint.ranker[0].id : null
}

output "ranker_runpod_serverless_url" {
  description = "runpod_serverless 모드일 때만 값이 있음. Backend .env의 RANKER_URL에 사용 (runsync 방식). RANKER_API_KEY는 커스텀 비밀키가 아니라 RunPod 계정 API 키(runpod_api_key와 동일값)를 넣어야 함"
  value       = var.ranker_deployment == "runpod_serverless" ? "https://api.runpod.ai/v2/${runpod_endpoint.ranker[0].id}/runsync" : null
}

output "ssh_backend" {
  value = "ssh -i <프라이빗키> ubuntu@${aws_instance.backend.public_ip}"
}

output "ssh_ranker" {
  value = (
    var.ranker_deployment == "ec2"
    ? "ssh -i <프라이빗키> ubuntu@${aws_instance.ranker[0].public_ip}"
    : var.ranker_deployment == "runpod"
    ? "runpod Pod는 SSH 대신 RunPod 콘솔/API로 관리하세요 (pod id: ${runpod_pod.ranker[0].id})"
    : "runpod_serverless는 SSH 대상이 없습니다 (endpoint id: ${runpod_endpoint.ranker[0].id})"
  )
}

output "scp_backend_secrets" {
  description = "Backend에 .env / vector_db / data 업로드하는 예시 명령"
  value       = "scp -i <프라이빗키> -r ../.env ../vector_db ../data ubuntu@${aws_instance.backend.public_ip}:${var.app_dir}/"
}

output "rds_endpoint" {
  description = "enable_rds=true일 때만 값이 있음"
  value       = var.enable_rds ? aws_db_instance.main[0].address : null
}

output "rds_master_password" {
  description = "enable_rds=true일 때만 값이 있음. rds_master_password를 안 채웠으면 자동 생성된 값"
  sensitive   = true
  value       = var.enable_rds ? (var.rds_master_password != "" ? var.rds_master_password : random_password.rds[0].result) : null
}

output "database_url" {
  description = "Backend .env의 DATABASE_URL에 그대로 사용. enable_rds=true일 때만 값이 있음"
  sensitive   = true
  value = (
    var.enable_rds
    ? "postgresql://${var.rds_master_username}:${var.rds_master_password != "" ? var.rds_master_password : random_password.rds[0].result}@${aws_db_instance.main[0].address}:5432/${var.rds_db_name}"
    : null
  )
}

output "vector_db_s3_bucket_name" {
  description = "enable_vector_db_s3_backup=true일 때만 값이 있음"
  value       = var.enable_vector_db_s3_backup ? aws_s3_bucket.vector_db[0].bucket : null
}

output "vector_db_s3_uri" {
  description = "GitHub Actions TF_VECTOR_DB_S3_URI secret(deploy-ec2-terraform.yml)에 그대로 사용. enable_vector_db_s3_backup=true일 때만 값이 있음"
  value       = var.enable_vector_db_s3_backup ? "s3://${aws_s3_bucket.vector_db[0].bucket}/vector_db" : null
}

output "scp_ranker_secrets" {
  description = "ec2 모드일 때만 의미 있음. runpod/runpod_serverless는 콘솔 또는 Template에서 값을 직접 설정"
  value = (
    var.ranker_deployment == "ec2"
    ? "scp -i <프라이빗키> ../.env ubuntu@${aws_instance.ranker[0].public_ip}:${var.app_dir}/"
    : "해당 없음 (${var.ranker_deployment} 모드)"
  )
}
