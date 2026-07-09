# AWS RDS PostgreSQL — doc/rds-postgres-migration.md에서 설명한 SQLite→RDS 전환을
# Terraform으로도 프로비저닝할 수 있게 함. Backend 코드(apps/backend/backend/settings.py)는
# DATABASE_URL이 비어 있으면 자동으로 SQLite를 쓰므로, enable_rds=false면 이 리소스 자체가
# 생성되지 않고 기존과 동일하게 동작한다.
#
# 실제 운영 환경(EC2 52.79.204.190 등)은 이미 콘솔에서 수동으로 만든 RDS를 쓰고 있을 수
# 있음 — 이 리소스는 그 수동 RDS를 대체하는 게 아니라, 이 terraform/ 모듈로 처음부터
# 새로 배포할 때도 동일한 아키텍처(RDS 포함)를 재현할 수 있도록 채워 넣은 것.

resource "aws_security_group" "rds" {
  count = var.enable_rds ? 1 : 0

  name        = "${var.project_name}-rds-sg"
  description = "RDS PostgreSQL: 5432 allowed from Backend EC2 security group only"
  vpc_id      = aws_vpc.main.id

  ingress {
    description     = "PostgreSQL from backend"
    from_port       = 5432
    to_port         = 5432
    protocol        = "tcp"
    security_groups = [aws_security_group.backend.id]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name = "${var.project_name}-rds-sg"
  }
}

resource "aws_db_subnet_group" "main" {
  count = var.enable_rds ? 1 : 0

  name       = "${var.project_name}-rds-subnet-group"
  subnet_ids = [aws_subnet.public.id, aws_subnet.public_b[0].id]

  tags = {
    Name = "${var.project_name}-rds-subnet-group"
  }
}

# rds_master_password를 비워두면(기본값) 자동 생성. terraform output -raw rds_master_password로 확인.
resource "random_password" "rds" {
  count = var.enable_rds && var.rds_master_password == "" ? 1 : 0

  length  = 20
  special = false
}

resource "aws_db_instance" "main" {
  count = var.enable_rds ? 1 : 0

  identifier     = "${var.project_name}-db"
  engine         = "postgres"
  engine_version = var.rds_engine_version
  instance_class = var.rds_instance_class

  allocated_storage = var.rds_allocated_storage_gb
  storage_type      = "gp3"

  db_name  = var.rds_db_name
  username = var.rds_master_username
  password = var.rds_master_password != "" ? var.rds_master_password : random_password.rds[0].result

  db_subnet_group_name   = aws_db_subnet_group.main[0].name
  vpc_security_group_ids = [aws_security_group.rds[0].id]
  publicly_accessible    = false

  backup_retention_period = var.rds_backup_retention_days

  # 기본값(true)은 개발 편의용 — destroy 시 최종 스냅샷 없이 완전 삭제됨.
  # 운영 환경이면 false로 두고 rds_final_snapshot_identifier를 지정할 것.
  skip_final_snapshot       = var.rds_skip_final_snapshot
  final_snapshot_identifier = var.rds_skip_final_snapshot ? null : var.rds_final_snapshot_identifier

  tags = {
    Name = "${var.project_name}-db"
  }
}
