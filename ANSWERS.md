# Day 28 Track 2 - Answers

Student: Vu Van Phong
Mode: Individual
Repository: https://github.com/VuVanPhong123/TRACK2_Day28_2A202601647_VuVanPhong
Date: 2026-09-03
Runtime: Windows, Python 3.11.8, Docker Desktop Engine 28.5.1, full Docker Compose profile.
Immutable baseline: `2bafc86eb9f58568253ea298def58df76e467f55` / `day28-vu-van-phong-v1`.

The v1 tag and its commit were preserved. Remediation is being prepared on
`remediation/day28-live-evidence`; the final v2 commit/tag is recorded after
the reviewed branch is merged.

## 1. Architecture and integration points

The live path is Envoy -> FastAPI -> Kafka -> Airflow/Spark -> Delta Lake.
Delta feeds Feast and Qdrant; MLflow holds the release/champion; the API uses
vLLM for the optional GPU serving leg. Prometheus, Grafana, OTLP Collector and
Jaeger observe the boundaries. Ownership and the diagram are in
[docs/submission-architecture.md](docs/submission-architecture.md).

The implementation uses `event.entity_id` as the Kafka record key for ordering
per asker. `event.idempotency_key` remains in the payload and in the
`idempotency-key` header. The live IP01 artifact verifies that these values are
distinct fields with the intended relationship.

## 2. Live journey results

- J1: PASS - `12 passed, 3 deselected`; Airflow run `it-358be933`, trace
  `b8d89110c23244588449f592e2f1703b`, Delta feedback v22 and documents v13.
- J2: PASS - `9 passed`; latest replay used asker `it-j2-80a282bf`, three Kafka
  deliveries at offsets 43, 44 and 45, and one durable Delta row / one Qdrant
  point after replay.
- J3: PASS - `6 passed`; MLflow version 9 was promoted from champion v3 with
  run `79ebc5f763534c8ea4d8f2a1f8d94eaa`, then the alias was rolled back to v3.
- J4: PASS - `9 passed, 4 deselected`; Feast degradation, Qdrant mandatory
  failure/recovery, poison parking, valid replay and no duplicate row were
  observed. The recovery artifact contains the actual DLQ coordinates and run
  IDs.
- J5: PASS for the non-GPU local leg - `9 passed, 1 deselected`; the trace
  `3b3c0150af7b4c6c8ff3019951b4f95b` crosses gateway, API, Kafka, Airflow and
  Spark. Serving/vLLM spans remain gated by the absent real endpoint.

The full command `uv run pytest integration-tests -m "not gpu and not langsmith" -vv`
also passed: `56 passed, 16 deselected`. A recovery race in the test utility was
fixed by waiting for Envoy's live `health_flags::healthy` signal after a
dependency restart; no assertion or marker was weakened.

## 3. Kafka, at-least-once delivery and idempotency

The producer uses `acks=all`, idempotence and flush. Consumers commit offsets
only after durable processing. Delta collapses duplicate source rows before
`MERGE`; later redelivery matches the same idempotency key. Qdrant uses a
deterministic point ID derived from `doc_id`. J2's live result is recorded in
[evidence/no-data-loss.json](evidence/no-data-loss.json).

## 4. Feast and Qdrant

J1 served Feast entity `it-j1-24b4124e` through `asker_serving_v1` with all
features present and Delta version 22. The Qdrant evidence contains collection
`lab28_documents`, 23 points, five retrieval results and the pinned embedding
identity:
`sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2@faf4aa4225822f3bc6376869cb1164e8e3feedd0`.

Feast is optional in serving and is reported as `degraded` when unavailable.
Qdrant is mandatory for readiness and is reported as `not_ready` / HTTP 503
when unavailable. The API can still return a flagged direct request during a
mandatory dependency outage, but the gateway removes an unready upstream.

## 5. MLflow release and rollback

The registered model is `lab28-rag-release`. The current champion is v3 with
run `a98ca59bd52f41cdb14a323666d93878`. J3 promoted v9 with provenance tags
for prompt, vLLM model, embedding model, Qdrant collection, Feast service and
Delta version, then restored champion v3. See
[evidence/ip06-mlflow-release.json](evidence/ip06-mlflow-release.json) and
[evidence/rollback.json](evidence/rollback.json).

## 6. Readiness and recovery semantics

`/health` is liveness and remains independent of dependency probes. `/ready`
returns HTTP 503 only for a mandatory failure. Kafka, MLflow and Qdrant are
mandatory; Feast is degradable; vLLM becomes mandatory when
`LAB28_VLLM_REQUIRE_REAL=true`. The local Compose API therefore reports
`degraded` because vLLM is absent, while its Kafka, MLflow, Qdrant and Feast
components are healthy.

J4 stopped and restarted real Compose services. The successful record is in
[evidence/failure-recovery.md](evidence/failure-recovery.md). The full
GPU-marked Envoy-ejection assertion was not claimed because the environment
has no real vLLM; Envoy's configured active check is `/ready` and its recovered
admin state was healthy.

## 7. Trace, metrics and gateway

The non-GPU J5 path proved W3C trace continuity across HTTP, Kafka and the
asynchronous Airflow/Spark path; collector export failures were zero. The
Prometheus/Grafana tests passed: all non-GPU component targets were up, alert
rules loaded/evaluated, and the provisioned `Lab 28 Platform Overview`
dashboard used the Prometheus datasource. The optional vLLM target is down by
design until a real GPU endpoint exists.

Gateway evidence records configured 10 RPS, HTTP 200 and HTTP 429 samples,
`x-request-id` on both, and Envoy rate-limit statistics. The public `/healthz`
route is answered by Envoy itself.

## 8. Performance profile

`load-tests/run_profile.py` only requests `/ready`, so these are readiness /
control-plane profiles, not LLM inference benchmarks:

- 8 workers, 200 requests: 21 HTTP 200 and 179 helper status `0`; P50/P95/P99
  4.80 / 380.72 / 494.48 ms.
- 16 workers, 200 requests: 13 HTTP 200 and 187 helper status `0`; P50/P95/P99
  6.91 / 580.07 / 758.97 ms.

The helper maps urllib exceptions (including Envoy's 429 rate-limit response)
to status `0`; it does not expose throughput. The dominant bottleneck in this
measurement is the intentional 10 RPS edge token bucket, not model execution.
Raw outputs are [load-profile-8.json](evidence/load-profile-8.json) and
[load-profile-16.json](evidence/load-profile-16.json).

## 9. GPU/vLLM and LangSmith gates

`nvidia-smi` is unavailable locally. The generated IP07 identity is
`reachable: false`, `is_real_vllm: false`, so IP07 is `UNVERIFIED`; no mock or
CPU classifier is used as evidence. The Kaggle extension specifies a T4 path
with the current `vllm==0.26.0` guide; it requires the user to run the notebook
with Internet/GPU and return only the public endpoint/model details if this
optional gate is needed. Do not send repository credentials or ngrok tokens.

External LangSmith is also `UNVERIFIED` because no credential was provided.
Local OTLP/Jaeger is proven for the non-GPU asynchronous leg; serving spans
are absent because the real inference leg was not run.

## 10. Kubernetes/GitOps

`scripts/validate_manifests.py` and `kubectl kustomize deploy/kubernetes/base`
both pass. `kubectl config current-context` reports no current context, so
Kubernetes runtime and GitOps runtime are `UNVERIFIED`; no live apply was run.
The existing v1 GitOps reference remains untouched until the final reviewed
v2 commit is known, then `gitops/application.yaml` is updated to
`refs/tags/day28-vu-van-phong-v2`.

## 11. Static verification and known gaps

- Fast suite: `91 passed`; [evidence/fast-suite.txt](evidence/fast-suite.txt).
- Ruff, matrix (245 checks), portability and manifest validation: PASS.
- Basic and full Compose config validation and runtime smoke: PASS.
- `lab28 integration` intentionally exits 1 in this environment: its
  process-level report has 5/6 verified points passing, four outside-process
  points unverified, and IP07 `not_ready`. The external test evidence above is
  the source for those outside-process points; the report was not manually
  turned green.
- `verify_starter_state.py` remains a pre-implementation scaffold check and is
  not applicable after the four integration tasks are implemented; the
  corresponding starter tests pass.

Remaining production gaps are immutable image digests, full dependency
deployment in Kubernetes, production secret management/TLS/authentication,
backup/restore and capacity evidence for real inference, the real GPU vLLM
gate, and external LangSmith.

## Contribution

This is an individual submission by Vu Van Phong. Runtime fixes were limited to
the Windows-safe CLI stdout boundary, bounded gateway 429 backoff for the
operator seed batch, and control-plane synchronization after dependency
recovery. No secret, `.env`, database, cache, model weight or `.lab28/` runtime
state is intended for commit.
