# GitHub Actions EC2 배포 가이드

이 저장소는 `deploy` 브랜치에서만 EC2 배포 workflow가 실행되도록 구성합니다.

## 동작 흐름

```text
deploy 브랜치 push 또는 Actions 수동 실행
  ↓
GitHub Actions
  ↓
EC2 SSH 접속
  ↓
~/law_project2에서 main 브랜치 pull
  ↓
docker compose up -d --build
```

실제 EC2에 배포되는 코드는 `main` 브랜치입니다.
`deploy` 브랜치는 배포 트리거 역할만 합니다.

## 필요한 GitHub Secrets

GitHub 저장소에서 아래 값을 등록합니다.

```text
Settings
→ Secrets and variables
→ Actions
→ New repository secret
```

필수 Secret:

| 이름 | 값 |
|---|---|
| `EC2_HOST` | `43.201.66.21` |
| `EC2_USER` | `ubuntu` |
| `EC2_SSH_KEY` | EC2 접속용 private key 전체 내용 |

`EC2_SSH_KEY`는 `.pem` 파일 내용을 그대로 넣습니다.
키 파일은 저장소에 커밋하면 안 됩니다.

## 배포 방법

1. EC2 보안 그룹에서 22번 포트를 임시로 허용합니다.
2. `main`에 배포할 코드를 push합니다.
3. `deploy` 브랜치를 push하거나 GitHub Actions 화면에서 수동 실행합니다.

로컬에서 deploy 브랜치 push로 트리거:

```bash
git switch deploy
git merge main
git push origin deploy
```

또는 GitHub 웹에서:

```text
Actions
→ Deploy EC2
→ Run workflow
→ Branch: deploy
```

배포가 끝나면 EC2 보안 그룹에서 22번 포트를 다시 닫거나 내 IP만 허용합니다.

## EC2 배포 명령

workflow가 EC2에서 실행하는 명령은 다음과 같습니다.

```bash
cd ~/law_project2
git fetch origin main
git checkout main
git pull --ff-only origin main
docker compose --env-file .env -f docker/docker-compose.backend.aws.yml up -d --build
docker compose -f docker/docker-compose.backend.aws.yml ps
```

