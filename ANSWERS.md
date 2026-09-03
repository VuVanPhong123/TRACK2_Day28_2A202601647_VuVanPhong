# Day 28 Track 2 — Answers

Student: Vu Van Phong<br>
Mode: Individual<br>
Repository: https://github.com/VuVanPhong123/TRACK2_Day28_2A202601647_VuVanPhong<br>
Final commit/tag: được xác minh ở bước final Git; tag dự kiến `day28-vu-van-phong-v1`<br>
Date: 2026-09-03<br>
Environment profile: `browser-fallback` — Python 3.11.8, Docker CLI có nhưng daemon không chạy.

## 1. Architecture và 10 integration points

Luồng chính là gateway → FastAPI → Kafka → Airflow/Spark → Delta. Delta cấp dữ liệu
cho Feast và Qdrant; MLflow giữ release/champion; API gọi vLLM cho serving. Prometheus,
Grafana và OTLP/Jaeger theo dõi các boundary. Sở hữu và file triển khai được tổng hợp
ở [submission architecture](docs/submission-architecture.md).

## 2. Kafka record key và idempotency key

Kafka record key là `event.entity_id`, để mọi sự kiện của một asker đi cùng partition
và giữ ordering theo entity. `event.idempotency_key` được giữ trong JSON payload và
header `idempotency-key`. `EventPublisher` vẫn encode record key riêng, nhưng truyền
đúng idempotency key vào header. Phần prose IP01 của matrix đã được đồng bộ với hành vi
đó; không đổi ID, test hay scoring.

## 3. At-least-once và Delta MERGE

Producer dùng `acks=all`, idempotence và flush; consumer chỉ commit offset sau khi
Delta xử lý thành công. `dedupe_latest` đọc iterable một lần, dedupe theo
`idempotency_key`, chọn max `(occurred_at, event_id)` và trả thứ tự deterministic để
Spark MERGE không nhận duplicate source rows. Logic được chứng minh bởi
`evidence/fast-suite.txt` và `tests/test_delta_merge_idempotency.py`.

## 4. Replay và idempotency

Replay cùng logical fact giữ nguyên `idempotency_key`; Delta update matched row thay vì
append. Qdrant dùng UUID deterministic từ `doc_id`, nên replay không tạo point mới.
Live J2 chưa chạy vì Docker daemon không khả dụng: `UNVERIFIED`.

## 5. Feast offline/online và freshness

Snapshot offline được tạo từ Delta export. Online request dùng `FEATURE_REFS` từ
`contracts.py`, entity `asker_id` và `full_feature_names=false`. Feast là dependency
optional của serving: lỗi/missing feature hiển thị `degraded`, không làm pod mất
rotation. Live materialization/freshness evidence: `UNVERIFIED`.

## 6. Qdrant deterministic IDs và retrieval

Documents được embed dense+sparse và upsert vào collection `lab28_documents`; point ID
là UUID5 deterministic từ `doc_id`, retrieval dùng hybrid RRF. Live collection/search
evidence: `UNVERIFIED`.

## 7. MLflow release/champion/rollback

Release lưu prompt/config, signature, tags và provenance; alias `champion` là version
được serving resolve. J3 phải kiểm tra promoted version rồi resolve lại previous
champion sau rollback. MLflow runtime và rollback evidence: `UNVERIFIED`.

## 8–9. `ready`, `degraded`, `not_ready` và dependency severity

`/health` là liveness, không chạm dependency; `/ready` là dependency-aware. Kafka,
MLflow và Qdrant là mandatory; Feast optional; vLLM trở thành mandatory khi
`LAB28_VLLM_REQUIRE_REAL=true`. `readiness_status` ưu tiên mọi mandatory failure thành
`not_ready`, optional failure thành `degraded`, còn lại `ready`; iterable rỗng là
`ready`.

## 10. Failure, recovery và no-data-loss

Thiết kế recovery là retry bounded → DLQ cho poison message → operator replay sau khi
sửa lỗi; offset không commit trước durable processing. J2/J4 cần chứng minh counts,
versions, offsets và replay IDs trước/sau. Do không có stack runtime, failure/recovery
và no-data-loss live artifacts: `UNVERIFIED`.

## 11. Trace continuity

W3C `traceparent` đi qua HTTP, Kafka headers và OTLP spans. `event_headers` bỏ header
trace khi giá trị rỗng nhưng luôn gửi `idempotency-key`; trace ID không bị thay đổi qua
async boundary. Local collector/Jaeger path có trong `monitoring/otel-collector.yaml`,
nhưng live trace query chưa chạy: `UNVERIFIED`.

## 12. Golden signals và alerts

API/gateway expose rate, error và duration; readiness/component gauges, Kafka exporter,
collector metrics và vLLM metrics được scrape theo `monitoring/prometheus.yml`.
`monitoring/alerts.yml` có alert API unavailable và high error ratio. Static config pass;
Prometheus/Grafana runtime: `UNVERIFIED`.

## 13. Performance

P50/P95/P99 của readiness hoặc `/api/v1/ask`: `UNVERIFIED` — không có gateway listener
vì Docker daemon không chạy. Vì vậy chưa tuyên bố throughput inference, hardware
capacity hay bottleneck runtime. `load-tests/run_profile.py` hiện là readiness/control-
plane probe, không phải benchmark LLM serving; cần chạy lại với 8 và 16 workers trên
stack thật trước khi báo số liệu.

## 14. Kubernetes/GitOps

Kubernetes static validation: `PASS` qua `scripts/validate_manifests.py` và
`kubectl kustomize deploy/kubernetes/base`. `kubectl apply --dry-run=client` không thể
hoàn tất vì client cố lấy OpenAPI từ API server không chạy; không apply live. GitOps
runtime: `UNVERIFIED`. `gitops/application.yaml` đã trỏ repo cá nhân và immutable tag
dự kiến, nhưng tag chỉ có sau final commit.

## 15. GPU/vLLM

`UNVERIFIED` — chưa có GPU-backed vLLM endpoint được xác minh. Không dùng mock/CPU
classifier làm bằng chứng IP07 và không tạo `ip07-vllm-identity.json` giả.

## 16. Local OTLP và external LangSmith

Local OTLP/Jaeger là path offline được cấu hình; runtime chưa chạy nên `UNVERIFIED`.
External LangSmith là optional và `UNVERIFIED` vì chưa có `LANGSMITH_API_KEY`; không
fake project/export.

## 17. Production gaps đã xác nhận từ source

- Compose/Kubernetes dùng image tags thay vì immutable image digests.
- K8s base chỉ mô tả API/gateway và tham chiếu dependency service; không phải full
  Kafka/Delta/Feast/Qdrant/MLflow deployment.
- Compose có Grafana credential dev `admin/admin`; không phù hợp production secret
  management.
- Envoy config có routing/rate limit nhưng chưa có gateway authentication/TLS.
- Chưa có persistent backup/restore evidence và remote GPU tunnel lifecycle.
- Chưa có production-capacity evidence cho real inference.

## Verification summary

- Fast suite: `PASS` — 88 tests, transcript tại `evidence/fast-suite.txt`.
- Ruff: `PASS`.
- Matrix: `PASS` — 245 checks; `tests/test_integration_matrix.py`: 2 passed.
- Portability: `PASS`.
- Manifest validator: `PASS`.
- Compose basic/full/GPU config: `PASS` (static only).
- Basic/full Docker, J1–J5, IP01–IP10 live evidence, load runtime: `UNVERIFIED` vì
  Docker daemon không chạy.

## Contribution

Vu Van Phong completed and verified the implementation, integration, evidence,
documentation and submission work in this individual repository.

Không commit secret, runtime DB/state, model weights/cache; không fake evidence.
