# auto_deploy_backend=true(기본값)일 때, Backend EC2가 뜬 뒤 terraform apply가 SSH로
# 직접 접속해서:
#   1. user_data(cloud-init) 완료 대기 (.bootstrap_complete 마커 파일)
#   2. 로컬 .env(개인 시크릿) + Terraform이 계산한 RANKER_*/DATABASE_URL을 병합
#   3. 병합된 .env, vector_db/, data/ 를 인스턴스로 업로드
#   4. deploy_backend.sh 실행 (docker compose up)
# 까지 전부 자동으로 수행한다. false로 끄면 예전처럼 scp + deploy_backend.sh를
# 수동으로 진행해야 한다 (README "앱 배포" 섹션 참고).
#
# triggers를 인스턴스 id에만 묶어서, 인스턴스가 재생성될 때만 재실행된다 (로컬 .env나
# vector_db/data를 바꾼 뒤 다시 배포하고 싶으면 아래처럼 강제 재실행):
#   terraform apply -replace=null_resource.backend_app_deploy[0]
resource "null_resource" "backend_app_deploy" {
  count = var.auto_deploy_backend ? 1 : 0

  triggers = {
    instance_id = aws_instance.backend.id
  }

  connection {
    type        = "ssh"
    host        = aws_instance.backend.public_ip
    user        = "ubuntu"
    private_key = file(var.ssh_private_key_path)
    timeout     = "5m"
  }

  # 1) cloud-init(user_data) 완료 대기
  provisioner "remote-exec" {
    inline = [
      "timeout 300 bash -c 'until [ -f ${var.app_dir}/.bootstrap_complete ]; do sleep 5; done'"
    ]
  }

  # 2) 로컬 .env 병합 (실제 값은 environment로만 전달 — command 문자열에 시크릿 노출 안 됨)
  provisioner "local-exec" {
    interpreter = [var.local_bash_path, "-c"]
    command     = file("${path.module}/scripts/merge_backend_env.sh")

    environment = {
      LOCAL_ENV_PATH  = "${path.module}/../.env"
      OUT_PATH        = "${path.module}/.generated-backend.env"
      RANKER_URL      = lookup(local.backend_env_overrides, "RANKER_URL", "")
      RANKER_API_KEY  = lookup(local.backend_env_overrides, "RANKER_API_KEY", "")
      RANKER_BACKEND  = lookup(local.backend_env_overrides, "RANKER_BACKEND", "custom")
      RANKER_MODEL    = lookup(local.backend_env_overrides, "RANKER_MODEL", "")
      DATABASE_URL    = lookup(local.backend_env_overrides, "DATABASE_URL", "")
      DB_CONN_MAX_AGE = lookup(local.backend_env_overrides, "DB_CONN_MAX_AGE", "")
      DB_SSL_REQUIRE  = lookup(local.backend_env_overrides, "DB_SSL_REQUIRE", "")
    }
  }

  # 3) 병합된 .env 업로드
  provisioner "file" {
    source      = "${path.module}/.generated-backend.env"
    destination = "${var.app_dir}/.env"
  }

  # 4) vector_db/, data/ 업로드 (source 끝에 슬래시 = 디렉토리 내용물만 복사)
  provisioner "file" {
    source      = "${path.module}/../vector_db/"
    destination = "${var.app_dir}/vector_db"
  }

  provisioner "file" {
    source      = "${path.module}/../data/"
    destination = "${var.app_dir}/data"
  }

  # 5) 실제 배포
  provisioner "remote-exec" {
    inline = [
      "chmod +x ${var.app_dir}/deploy_backend.sh",
      "${var.app_dir}/deploy_backend.sh"
    ]
  }

  depends_on = [aws_instance.backend]
}
