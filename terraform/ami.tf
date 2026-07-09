# Backend: 표준 Ubuntu 22.04 LTS
data "aws_ami" "ubuntu" {
  most_recent = true
  owners      = ["099720109477"] # Canonical

  filter {
    name   = "name"
    values = ["ubuntu/images/hvm-ssd/ubuntu-jammy-22.04-amd64-server-*"]
  }

  filter {
    name   = "virtualization-type"
    values = ["hvm"]
  }
}

# Ranker: NVIDIA driver + Docker + Container Toolkit이 준비된 AWS Deep Learning AMI
# ranker_deployment = "ec2"일 때만 조회 (runpod 모드에서는 GPU AMI가 필요 없음)
data "aws_ami" "dlami_gpu" {
  count = var.ranker_deployment == "ec2" ? 1 : 0

  most_recent = true
  owners      = ["amazon"]

  filter {
    name   = "name"
    values = ["Deep Learning AMI GPU PyTorch*(Ubuntu*"]
  }

  filter {
    name   = "virtualization-type"
    values = ["hvm"]
  }
}
