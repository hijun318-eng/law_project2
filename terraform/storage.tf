# Chroma vector_db 백업/복원용 S3 버킷.
# .github/workflows/deploy-ec2-terraform.yml(이 Terraform으로 만든 서버 전용, TF_VECTOR_DB_S3_URI
# secret)가 배포할 때마다 EC2 안에서 aws s3 sync "$TF_VECTOR_DB_S3_URI" vector_db --delete를
# 실행해 이 버킷 → EC2로 최신 vector_db를 복원한다 (기존 운영 서버용 deploy-ec2.yml은
# VECTOR_DB_S3_URI라는 별도 secret으로 별개의 버킷을 씀 — 이 리소스와 무관).
# 반대 방향(로컬 → S3 최초 업로드)은 vector_db_s3_auto_upload=true(기본값)일 때
# terraform apply가 로컬 aws cli로 직접 수행한다 (아래 null_resource).

data "aws_caller_identity" "current" {}

resource "aws_s3_bucket" "vector_db" {
  count = var.enable_vector_db_s3_backup ? 1 : 0

  # S3 버킷명은 전역에서 유일해야 해서, 값을 비워두면 계정 ID를 붙여 자동 생성
  bucket = var.vector_db_s3_bucket_name != "" ? var.vector_db_s3_bucket_name : "${var.project_name}-vector-db-${data.aws_caller_identity.current.account_id}"

  # true(기본값)면 버킷에 객체가 남아있어도 destroy가 통과됨(개발 편의).
  # 운영 환경에서 실수로 지우는 게 걱정되면 false로 두되, 그럴 경우 destroy 전에
  # 버킷을 직접 비워야 함 (버전 관리까지 켜져 있어 모든 버전을 지워야 함).
  force_destroy = var.vector_db_s3_force_destroy

  tags = {
    Name = "${var.project_name}-vector-db"
  }
}

resource "aws_s3_bucket_public_access_block" "vector_db" {
  count = var.enable_vector_db_s3_backup ? 1 : 0

  bucket = aws_s3_bucket.vector_db[0].id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_versioning" "vector_db" {
  count = var.enable_vector_db_s3_backup ? 1 : 0

  bucket = aws_s3_bucket.vector_db[0].id

  versioning_configuration {
    status = "Enabled"
  }
}

# 버킷이 처음 생성된 시점에 로컬 vector_db/를 자동으로 올려준다 (terraform apply를
# 실행하는 머신에 aws cli + S3 쓰기 권한이 있는 자격증명이 있어야 함, 예: aws configure).
# triggers를 버킷 id에만 묶어서 버킷이 그대로면 이후 apply에서는 재실행되지 않는다
# (= "최초 1회 업로드"이지 매번 도는 지속 동기화가 아님). 로컬 vector_db가 바뀐 뒤 다시
# 올리고 싶으면 `terraform apply -replace=null_resource.vector_db_initial_upload[0]`처럼
# 강제로 재실행하거나, vector_db_s3_auto_upload를 껐다 켜서 트리거를 바꾸면 됨.
resource "null_resource" "vector_db_initial_upload" {
  count = var.enable_vector_db_s3_backup && var.vector_db_s3_auto_upload ? 1 : 0

  triggers = {
    bucket_id = aws_s3_bucket.vector_db[0].id
  }

  provisioner "local-exec" {
    # 그냥 "bash"만 쓰면 Windows에서 PATH상 System32\bash.exe(WSL 런처)가 먼저 잡혀서
    # "execvpe(/bin/bash) failed" 에러가 남 — var.local_bash_path로 실제 경로를 지정
    # (기본값 "bash"는 macOS/Linux에서 그대로 동작, Windows는 tfvars에서 Git Bash 경로로 override)
    interpreter = [var.local_bash_path, "-c"]
    command     = <<-EOT
      if [ -d "${path.module}/../vector_db" ]; then
        aws s3 sync "${path.module}/../vector_db" "s3://${aws_s3_bucket.vector_db[0].bucket}/vector_db" --delete
      else
        echo "vector_db/ 디렉토리가 없어 초기 업로드를 건너뜁니다 (경로: ${path.module}/../vector_db)"
      fi
    EOT
  }

  depends_on = [aws_s3_bucket_public_access_block.vector_db]
}

# deploy-ec2-terraform.yml은 GitHub Actions 워커가 아니라 EC2 인스턴스 내부에서 aws s3
# sync를 실행하므로, EC2 자체가 S3에 접근할 IAM 권한을 가지고 있어야 함 (.env에 AWS 키를
# 박아넣지 않기 위해 인스턴스 프로필 방식을 씀).
resource "aws_iam_role" "backend" {
  count = var.enable_vector_db_s3_backup ? 1 : 0

  name = "${var.project_name}-backend-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action    = "sts:AssumeRole"
      Effect    = "Allow"
      Principal = { Service = "ec2.amazonaws.com" }
    }]
  })
}

resource "aws_iam_role_policy" "backend_s3" {
  count = var.enable_vector_db_s3_backup ? 1 : 0

  name = "${var.project_name}-backend-s3-vector-db"
  role = aws_iam_role.backend[0].id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect = "Allow"
      Action = ["s3:GetObject", "s3:ListBucket"]
      Resource = [
        aws_s3_bucket.vector_db[0].arn,
        "${aws_s3_bucket.vector_db[0].arn}/*",
      ]
    }]
  })
}

resource "aws_iam_instance_profile" "backend" {
  count = var.enable_vector_db_s3_backup ? 1 : 0

  name = "${var.project_name}-backend-profile"
  role = aws_iam_role.backend[0].name
}
