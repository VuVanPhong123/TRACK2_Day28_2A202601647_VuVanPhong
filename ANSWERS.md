# Day 28 Track 2 - Answers

Student: Vu Van Phong
Mode: Individual
Repository: https://github.com/VuVanPhong123/TRACK2_Day28_2A202601647_VuVanPhong
Date: 2026-09-03
Runtime: Windows, Python 3.11.8, Docker Desktop Engine 28.5.1, full Docker Compose profile.
Immutable baseline: `2bafc86eb9f58568253ea298def58df76e467f55` / `day28-vu-van-phong-v1`.

The v1 and v2 tags and their commits were preserved. Final GPU remediation was
merged by PR #3 at `9101da9ae0623f3697f69e3142535b770bc21f9a`; the provenance
follow-up records that merge as `final_submission_commit` before v3 is tagged.

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

- J1: PASS - `15 passed`; Airflow run `it-b5d0ad87`, trace
  `809124c5d6164177961d8aac998687c8`, Delta feedback v41 and documents v21.
- J2: PASS - `9 passed`; latest replay used asker `it-j2-2d5f2656`, three Kafka
  deliveries at offsets 57, 58 and 59, and one durable Delta row / one Qdrant
  point after replay.
- J3: PASS - GPU promotion/rollback assertions passed; MLflow version 15 was
  promoted from champion v3 with run `d8a464e2a6e6478482aef0e901bea4b4`, then
  the alias was rolled back to v3.
- J4: PASS - `13 passed`; Feast degradation, Qdrant mandatory
  failure/recovery, poison parking, valid replay and no duplicate row were
  observed. The recovery artifact contains the actual DLQ coordinates and run
  IDs.
- J5/IP10: PASS - `14 passed, 1 skipped`; the local trace crosses gateway, API,
  Kafka, Airflow, Spark, and the transparent runtime vLLM proxy. The only
  skipped test is the external LangSmith credential gate.

The real-GPU command `uv run pytest integration-tests -m "gpu and not langsmith"
-vv` passed `15` tests. A remote-readiness timeout and recovery interval were
fixed in Envoy configuration; no assertion, marker, skip, or xfail was changed.

## 3. Kafka, at-least-once delivery and idempotency

The producer uses `acks=all`, idempotence and flush. Consumers commit offsets
only after durable processing. Delta collapses duplicate source rows before
`MERGE`; later redelivery matches the same idempotency key. Qdrant uses a
deterministic point ID derived from `doc_id`. J2's live result is recorded in
[evidence/no-data-loss.json](evidence/no-data-loss.json).

## 4. Feast and Qdrant

J1 served Feast entity `it-j1-dbfc0c12` through `asker_serving_v1` with all
features present and Delta version 41. The Qdrant evidence contains collection
`lab28_documents`, 29 points, five retrieval results and the pinned embedding
identity:
`sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2@faf4aa4225822f3bc6376869cb1164e8e3feedd0`.

Feast is optional in serving and is reported as `degraded` when unavailable.
Qdrant is mandatory for readiness and is reported as `not_ready` / HTTP 503
when unavailable. The API can still return a flagged direct request during a
mandatory dependency outage, but the gateway removes an unready upstream.

## 5. MLflow release and rollback

The registered model is `lab28-rag-release`. The current champion is v3 with
run `a98ca59bd52f41cdb14a323666d93878`. J3 promoted v15 with provenance tags
for prompt, vLLM model, embedding model, Qdrant collection, Feast service and
Delta version, then restored champion v3. See
[evidence/ip06-mlflow-release.json](evidence/ip06-mlflow-release.json) and
[evidence/rollback.json](evidence/rollback.json).

## 6. Readiness and recovery semantics

`/health` is liveness and remains independent of dependency probes. `/ready`
returns HTTP 503 only for a mandatory failure. Kafka, MLflow and Qdrant are
mandatory; Feast is degradable; vLLM becomes mandatory when
`LAB28_VLLM_REQUIRE_REAL=true`. The final runtime had all components ready,
including the real remote vLLM identity probe through the local transparent
proxy.

J4 stopped and restarted real Compose services. The successful record is in
[evidence/failure-recovery.md](evidence/failure-recovery.md). The GPU-marked
Envoy-ejection and recovery assertions passed with the real serving baseline;
Envoy's active check is `/ready`, with a 15-second timeout and 2-second
recovery interval for the remote GPU latency.

## 7. Trace, metrics and gateway

The J5/IP10 path proved W3C trace continuity across HTTP, Kafka, Airflow/Spark,
and the real serving leg; collector export failures were zero. The
Prometheus/Grafana tests passed: all component targets, including the vLLM
proxy target, were up, alert rules loaded/evaluated, and the provisioned
`Lab 28 Platform Overview` dashboard used the Prometheus datasource.

Gateway evidence records configured 10 RPS, HTTP 200 and HTTP 429 samples,
`x-request-id` on both, and Envoy rate-limit statistics. The public `/healthz`
route is answered by Envoy itself.

## 8. Performance profile

`load-tests/run_profile.py` only requests `/ready`, so these are readiness /
control-plane profiles, not LLM inference benchmarks:

- 8 workers, 200 requests: 11 HTTP 200, 151 HTTP 429 rejected, 37 HTTP 503
  errors, and 1 transport status `0`; elapsed 19.48s, throughput 10.27 req/s,
  P50/P95/P99 20.13 / 7249.60 / 8911.65 ms.
- 16 workers, 200 requests: 186 HTTP 429 rejected and 14 HTTP 503 errors;
  elapsed 493.74ms, throughput 405.07 req/s, P50/P95/P99 34.33 / 60.88 /
  66.14 ms.

The helper records `HTTPError.code` as the actual HTTP status; only transport
exceptions become status `0`, and it reports elapsed time, throughput, and
success/rejected/error counts. The dominant bottleneck is the intentional
10-RPS edge token bucket and readiness control plane, not model execution.
Raw outputs are [load-profile-8.json](evidence/load-profile-8.json) and
[load-profile-16.json](evidence/load-profile-16.json).

## 9. GPU/vLLM and LangSmith gates

The generated IP07 identity is `reachable: true`, `version: 0.26.0`, served
model `Qwen/Qwen3-4B-Instruct-2507`, `vllm_metric_count: 111`, and
`is_real_vllm: true`. The full serving request returned HTTP 200 through
`/api/v1/ask` and used the same configured model identity. The tunnel and key
were session-only; neither is stored in the repository.

External LangSmith is also `UNVERIFIED` because no credential was provided.
Local OTLP/Jaeger is proven for the full local serving trace. The external
LangSmith exporter remains `UNVERIFIED` because no credential was provided.

## 10. Kubernetes/GitOps

`scripts/validate_manifests.py` and `kubectl kustomize deploy/kubernetes/base`
both pass. `kubectl config current-context` reports no current context, so
Kubernetes runtime and GitOps runtime are `UNVERIFIED`; no live apply was run.
The existing v1 and v2 GitOps references remain untouched. The reviewed final
branch updates `gitops/application.yaml` to
`refs/tags/day28-vu-van-phong-v3`; no live apply was run.

## 11. Static verification and known gaps

- Fast suite: `93 passed`; [evidence/fast-suite.txt](evidence/fast-suite.txt).
- Ruff, matrix (245 checks), portability and manifest validation: PASS.
- Basic and full Compose config validation and runtime smoke: PASS.
- Full `uv run pytest integration-tests -m "not langsmith" -q`: `71 passed, 1
  deselected` (the external LangSmith gate).
- `lab28 integration` returns a ready report with 6/6 process-level points
  passing and score 100. Outside-process evidence files provide the runtime
  proof for IP01/IP02/IP04/IP08/IP09/IP10; the report was generated by the
  CLI and not manually marked green.
- `verify_starter_state.py` remains a pre-implementation scaffold check and is
  not applicable after the four integration tasks are implemented; the
  corresponding starter tests pass.

Remaining external/production gaps are immutable image digests, full
dependency deployment in Kubernetes, production secret management/TLS/
authentication, backup/restore and real-inference capacity benchmarking, and
external LangSmith.

## Contribution

This is an individual submission by Vu Van Phong. Runtime fixes include the
Compose bearer-key interpolation, Envoy remote-readiness timeout/recovery
settings, immediate trace-pipeline export for the real proxy boundary, and
the load helper's HTTPError handling. The transparent proxy itself remains
runtime-only under ignored `.lab28/`. No secret, `.env`, database, cache, model
weight or `.lab28/` runtime state is intended for commit.
