resource "aws_security_group" "backend" {
  name        = "${var.project_name}-backend-sg"
  description = "Backend EC2: SSH + Nginx(80), forwards to Django(internal 8000, not exposed on host)"
  vpc_id      = aws_vpc.main.id

  ingress {
    description = "SSH"
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = [var.ssh_allowed_cidr]
  }

  # docker-compose.backend.terraform.yml의 nginx 컨테이너가 80을 퍼블리시하고,
  # backend 컨테이너는 expose로만 내부 네트워크에 노출됨 (호스트 8000 리스닝 없음)
  ingress {
    description = "Backend web (nginx)"
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = [var.web_allowed_cidr]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name = "${var.project_name}-backend-sg"
  }
}

resource "aws_security_group" "ranker" {
  count = var.ranker_deployment == "ec2" ? 1 : 0

  name        = "${var.project_name}-ranker-sg"
  description = "Ranker GPU EC2: SSH + rerank(8001, backend SG only)"
  vpc_id      = aws_vpc.main.id

  ingress {
    description = "SSH"
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = [var.ssh_allowed_cidr]
  }

  ingress {
    description     = "Rerank API from backend only"
    from_port       = 8001
    to_port         = 8001
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
    Name = "${var.project_name}-ranker-sg"
  }
}
