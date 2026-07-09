# ranker_deployment = "runpod"일 때만 생성됨 (doc/runpod-ranker-deploy.md 경로)
#
# 전제조건: docker/Dockerfile.ranker.gpu 이미지가 미리 빌드되어
# var.runpod_ranker_image에 지정한 레지스트리로 push되어 있어야 함.
# (Terraform은 인프라만 관리하며 이미지 빌드/푸시는 자동화하지 않음)

resource "runpod_network_volume" "ranker_cache" {
  count = var.ranker_deployment == "runpod" && var.runpod_use_network_volume ? 1 : 0

  name           = "${var.project_name}-ranker-hf-cache"
  size           = var.runpod_volume_gb
  data_center_id = var.runpod_network_volume_data_center_id
}

resource "runpod_pod" "ranker" {
  count = var.ranker_deployment == "runpod" ? 1 : 0

  name       = "${var.project_name}-ranker"
  image_name = var.runpod_ranker_image

  gpu_type_ids = var.runpod_gpu_type_ids
  data_center_ids = (
    var.runpod_use_network_volume
    ? [var.runpod_network_volume_data_center_id]
    : (length(var.runpod_data_center_ids) > 0 ? var.runpod_data_center_ids : null)
  )

  gpu_count         = 1
  cloud_type        = var.runpod_cloud_type
  support_public_ip = true

  container_disk_in_gb = var.runpod_container_disk_gb
  volume_in_gb         = var.runpod_volume_gb
  network_volume_id    = var.runpod_use_network_volume ? runpod_network_volume.ranker_cache[0].id : null

  # doc/runpod-ranker-deploy.md의 Pod 환경변수와 동일
  env = {
    DJANGO_SETTINGS_MODULE = "ranker.settings"
    DJANGO_SECRET_KEY      = var.ranker_django_secret_key
    DEBUG                  = "False"
    ALLOWED_HOSTS          = "*"
    RERANKER_DEVICE        = "cuda"
    RERANKER_MODEL         = var.reranker_model
    RERANKER_BATCH_SIZE    = tostring(var.reranker_batch_size)
    RERANKER_MAX_DOCUMENTS = tostring(var.reranker_max_documents)
    RERANKER_MAX_CHARS     = tostring(var.reranker_max_chars)
    RANKER_API_KEY         = var.ranker_api_key
  }

  ports = ["8001/http", "22/tcp"]
}

# ── ranker_deployment = "runpod_serverless" ──────────────────────────
#
# Template/Endpoint는 공식 runpod/runpod provider(alias: runpod_official)로 관리한다.
# 커뮤니티 provider(decentralized-infrastructure/runpod)에는 애초에 Template 리소스가
# 없어 CLI 스크립트로 우회했었는데, 공식 provider는 진짜 runpod_template 리소스가 있고
# Create가 HTTP 201을 거부하던 버그(CE-1681)도 v1.0.8(2026-07-01, PR #44)에서 고쳐져
# 실사용 가능한 상태로 확인했다. 이제 terraform apply/destroy가 Template까지 온전히
# 추적/정리한다 (예전엔 destroy해도 Template이 안 지워졌음).
#
# 알려진 제약 (공식 provider 스키마 확인 결과):
#   - runpod_endpoint에 gpu_type_ids가 없음 — GPU "모델"을 지정할 방법이 없고
#     gpu_count(개수)만 지정 가능. 어떤 GPU가 배정될지는 RunPod가 결정한다.
#   - runpod_endpoint에 scaler_type/scaler_value가 없음 — 오토스케일링 전략을
#     Terraform으로 설정 불가 (RunPod 플랫폼 기본값을 따름).
#   - runpod_network_volume 리소스가 없음 — 그래서 Network Volume은 아래처럼
#     커뮤니티 provider로 그대로 만들고 id만 공식 provider 쪽 리소스에 넘겨준다
#     (서로 다른 provider raw 리소스 사이에서도 문자열 ID 참조는 문제없이 동작).
#
# runpod_serverless_worker = "infinity"(기본값): RunPod 공식 워커(worker-infinity-embedding)를
# 그대로 pull해서 씀 — 이미지 빌드/푸시 불필요, reranker_model만 지정하면 됨.
# (RunPod 공식 vLLM 워커는 generate 전용이라 CrossEncoder/reranker를 지원하지 않아 제외함 —
#  runpod-workers/worker-vllm의 handler.py가 engine.generate()만 호출하고 score/classify
#  경로가 없음을 소스로 확인함. reranker 전용으로는 worker-infinity-embedding을 사용.)
#
# runpod_serverless_worker = "custom": docker/Dockerfile.ranker.serverless를 build & push한
# 이미지를 씀 (전제조건, Terraform이 자동화 못 함).

resource "runpod_network_volume" "ranker_serverless_cache" {
  count = var.ranker_deployment == "runpod_serverless" && var.runpod_use_network_volume ? 1 : 0

  name           = "${var.project_name}-ranker-serverless-hf-cache"
  size           = var.runpod_volume_gb
  data_center_id = var.runpod_network_volume_data_center_id
}

resource "runpod_template" "ranker_serverless" {
  count    = var.ranker_deployment == "runpod_serverless" ? 1 : 0
  provider = runpod-official

  name = "${var.project_name}-ranker-serverless"
  image_name = (
    var.runpod_serverless_worker == "infinity"
    ? var.runpod_infinity_worker_image
    : var.runpod_serverless_image
  )
  is_serverless        = true
  container_disk_in_gb = var.runpod_container_disk_gb

  # readme/ports/container_registry_auth_id를 안 넣으면 RunPod API가 자체 기본값
  # (ports=["8888/http","22/tcp"] 등)을 채워 넣는데, 이 provider(v1.0.8)는 그 경우를
  # "provider produced inconsistent result after apply" 에러로 처리하는 스키마 버그가
  # 있음 — 그래서 API 기본값과 동일한 값을 여기서 명시적으로 선언해 불일치를 없앰.
  readme                     = ""
  ports                      = ["8888/http", "22/tcp"]
  container_registry_auth_id = ""

  env = (
    var.runpod_serverless_worker == "infinity"
    ? {
      MODEL_NAMES = var.reranker_model
      BATCH_SIZES = tostring(var.reranker_batch_size)
      BACKEND     = "torch"
    }
    : {
      RERANKER_DEVICE        = "cuda"
      RERANKER_MODEL         = var.reranker_model
      RERANKER_BATCH_SIZE    = tostring(var.reranker_batch_size)
      RERANKER_MAX_DOCUMENTS = tostring(var.reranker_max_documents)
      RERANKER_MAX_CHARS     = tostring(var.reranker_max_chars)
    }
  )
}

resource "runpod_endpoint" "ranker" {
  count    = var.ranker_deployment == "runpod_serverless" ? 1 : 0
  provider = runpod-official

  name        = "${var.project_name}-ranker-endpoint"
  template_id = runpod_template.ranker_serverless[0].id

  workers_min  = var.runpod_serverless_workers_min
  workers_max  = var.runpod_serverless_workers_max
  idle_timeout = var.runpod_serverless_idle_timeout
  gpu_count    = 1

  # flashboot/gpu_type_ids를 안 넣으면 RunPod API가 자체 기본값을 채워 넣는데(flashboot=true,
  # gpu_type_ids=계정에서 쓸 수 있는 전체 GPU 목록), 이 provider는 이 드리프트를 매 plan마다
  # "1 to change"로 잡아서 불필요한 Update 호출을 유발하고, 그 Update가 다시 아래
  # network_volume_ids류의 "provider produced inconsistent result" 버그를 반복 트리거함.
  # 그래서 template과 동일하게 여기서도 명시적으로 선언해 드리프트를 없앰.
  flashboot    = true
  gpu_type_ids = var.runpod_gpu_type_ids

  data_center_ids = (
    var.runpod_use_network_volume
    ? [var.runpod_network_volume_data_center_id]
    : (length(var.runpod_data_center_ids) > 0 ? var.runpod_data_center_ids : null)
  )

  # use_network_volume=false일 때 API가 network_volume_id를 null이 아니라 빈 문자열("")로
  # 돌려줘서, null을 넣으면 "provider produced inconsistent result"(null -> "") 에러가 남
  network_volume_id = var.runpod_use_network_volume ? runpod_network_volume.ranker_serverless_cache[0].id : ""

  # network_volume_ids(복수, computed 전용 필드)는 일부러 안 건드림 — 여기에 값을
  # 직접 넣으면 GraphQL API가 문자열이 아니라 객체를 기대하는 스키마 불일치로 500 에러가
  # 남(실제로 확인함). network_volume_id(단수)만 넣어도 기능은 정상 동작하고, API가
  # 사후에 network_volume_ids를 자동으로 채워 돌려주면서 생기는 "provider produced
  # inconsistent result" 에러는 provider(v1.0.8)의 알려진 버그 — 리소스 자체는 실제로
  # 정상 생성되므로 apply 실패 후 `terraform untaint runpod_endpoint.ranker[0]`로 넘어감.
  #
  # gpu_type_ids도 RunPod API가 저장 시 순서를 자기 마음대로 바꿔서 돌려줘서(집합은 같은데
  # 순서만 다름), 매 plan마다 "순서 원복" Update가 발생하고 그 Update가 다시 위와 같은
  # "provider produced inconsistent result" 버그를 반복 트리거함 — 순서는 기능에
  # 영향 없으므로 아예 무시함.
  lifecycle {
    ignore_changes = [network_volume_ids, gpu_type_ids]
  }
}
