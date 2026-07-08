# RDS PostgreSQL 전환 가이드

이 문서는 Django 기본 SQLite DB를 AWS RDS PostgreSQL로 분리하는 절차입니다.

## 목표 구조

```text
Nginx
  ↓
Django Backend EC2
  ↓
AWS RDS PostgreSQL
```

RDS로 옮기는 대상:

- Django 사용자/세션/관리자 테이블
- 상담 이력
- 피드백
- 프롬프트 템플릿
- 성능/비용 모니터링 데이터

Chroma `vector_db`는 이 작업 대상이 아닙니다. 벡터 DB는 별도 백업 또는 별도 벡터 저장소 전환 작업으로 다룹니다.

## 1. RDS 생성 권장값

엔진:

```text
PostgreSQL
```

DB 이름 예시:

```text
law_project2
```

마스터 사용자 예시:

```text
law_user
```

네트워크:

- EC2와 같은 VPC
- Public access는 가능하면 `No`
- 보안 그룹은 EC2 보안 그룹에서 오는 5432만 허용

RDS 보안 그룹 인바운드 예시:

| 포트 | 소스 |
|---:|---|
| 5432 | Backend EC2 보안 그룹 |

## 2. EC2 .env 설정

EC2의 `~/law_project2/.env`에 아래 값을 추가합니다.

```env
DATABASE_URL=postgresql://law_user:PASSWORD@RDS_ENDPOINT:5432/law_project2
DB_CONN_MAX_AGE=600
DB_SSL_REQUIRE=False
```

RDS가 SSL 연결을 강제하도록 설정했다면:

```env
DB_SSL_REQUIRE=True
```

`DATABASE_URL`이 비어 있으면 기존처럼 SQLite를 사용합니다.

## 3. 기존 SQLite 데이터 백업

RDS로 전환하기 전에 현재 SQLite 데이터를 JSON으로 백업합니다.

```bash
cd ~/law_project2
docker compose -f docker/docker-compose.backend.aws.yml exec backend \
  python manage.py dumpdata \
  --exclude contenttypes \
  --exclude auth.permission \
  --indent 2 \
  > sqlite-backup.json
```

이 파일은 EC2에 보관하거나 필요하면 안전한 위치로 복사합니다.

## 4. RDS 마이그레이션 실행

`.env`에 `DATABASE_URL`을 설정한 뒤 컨테이너를 재생성합니다.

```bash
docker compose --env-file .env -f docker/docker-compose.backend.aws.yml up -d --build
```

현재 compose 명령은 backend 시작 시 자동으로 아래 명령을 실행합니다.

```bash
python manage.py migrate --noinput
python manage.py collectstatic --noinput
```

따라서 RDS에 테이블이 자동 생성됩니다.

## 5. SQLite 데이터 복원

기존 SQLite 데이터를 RDS에 넣으려면:

```bash
docker compose -f docker/docker-compose.backend.aws.yml exec -T backend \
  python manage.py loaddata --format=json - < sqlite-backup.json
```

복원 후 관리자 계정과 상담 이력이 정상인지 확인합니다.

## 6. 확인 명령

```bash
docker compose -f docker/docker-compose.backend.aws.yml logs --tail=100 backend
docker compose -f docker/docker-compose.backend.aws.yml exec backend python manage.py check
```

브라우저 확인:

```text
http://52.79.204.190/
```

## 7. 롤백

RDS 연결에 문제가 있으면 `.env`에서 `DATABASE_URL`을 비우고 다시 재기동합니다.

```env
DATABASE_URL=
```

```bash
docker compose --env-file .env -f docker/docker-compose.backend.aws.yml up -d --build
```

이 경우 기존 SQLite로 돌아갑니다.

