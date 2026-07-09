# ranker_deployment = "ec2"일 때만 생성됨 (doc/aws-ec2-two-server-deploy.md 경로)
resource "aws_instance" "ranker" {
  count = var.ranker_deployment == "ec2" ? 1 : 0

  ami                    = data.aws_ami.dlami_gpu[0].id
  instance_type          = var.ranker_instance_type
  subnet_id              = aws_subnet.public.id
  vpc_security_group_ids = [aws_security_group.ranker[0].id]
  key_name               = aws_key_pair.main.key_name

  root_block_device {
    volume_size = var.ranker_root_volume_size_gb
    volume_type = "gp3"
  }

  user_data = templatefile("${path.module}/user_data/ranker.sh.tftpl", {
    git_repo_url = var.git_repo_url
    git_branch   = var.git_branch
    app_dir      = var.app_dir
  })

  tags = {
    Name = "${var.project_name}-ranker-gpu"
  }
}
