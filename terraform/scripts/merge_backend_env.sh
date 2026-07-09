#!/bin/bash
# null_resource.backend_app_deploy의 local-exec provisioner가 실행하는 스크립트.
#
# 로컬 .env(개인 시크릿: OPENAI_API_KEY, NAVER_*, DJANGO_SECRET_KEY 등)를 베이스로 삼되,
# RANKER_*/DATABASE_URL 등 "이번 terraform apply로 새로 생성된 인프라에 맞는 값"만
# Terraform이 계산한 값으로 덮어써서 $OUT_PATH에 새로 만든다.
#
# 값 자체는 전부 environment 블록(local-exec의 `environment = {...}`)으로 넘어오므로
# 이 command 문자열 안에는 절대 실제 값이 노출되지 않는다 (terraform plan/apply 로그에
# RunPod API 키/RDS 비밀번호 같은 게 그대로 찍히는 걸 피하기 위함).
set -e

cp "$LOCAL_ENV_PATH" "$OUT_PATH.tmp"

for k in RANKER_URL RANKER_API_KEY RANKER_BACKEND RANKER_MODEL DATABASE_URL DB_CONN_MAX_AGE DB_SSL_REQUIRE; do
  grep -v "^$k=" "$OUT_PATH.tmp" > "$OUT_PATH.tmp2" 2>/dev/null || cp "$OUT_PATH.tmp" "$OUT_PATH.tmp2"
  mv "$OUT_PATH.tmp2" "$OUT_PATH.tmp"
done

{
  echo "RANKER_URL=$RANKER_URL"
  [ -n "$RANKER_API_KEY" ] && echo "RANKER_API_KEY=$RANKER_API_KEY"
  echo "RANKER_BACKEND=$RANKER_BACKEND"
  [ -n "$RANKER_MODEL" ] && echo "RANKER_MODEL=$RANKER_MODEL"
  [ -n "$DATABASE_URL" ] && echo "DATABASE_URL=$DATABASE_URL"
  [ -n "$DB_CONN_MAX_AGE" ] && echo "DB_CONN_MAX_AGE=$DB_CONN_MAX_AGE"
  [ -n "$DB_SSL_REQUIRE" ] && echo "DB_SSL_REQUIRE=$DB_SSL_REQUIRE"
  true
} >> "$OUT_PATH.tmp"

mv "$OUT_PATH.tmp" "$OUT_PATH"
