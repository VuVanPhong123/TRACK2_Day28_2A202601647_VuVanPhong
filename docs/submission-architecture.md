# Submission architecture and ownership

![Lab 28 architecture](images/lab28-architecture-overview.png)

[SVG version](images/lab28-architecture-overview.svg)

The actual owner for every point in this individual submission is **Vu Van
Phong**. The role column retains the logical platform role from the instructor
matrix; it does not claim additional contributors.

| Point | Logical role | Owner | Implementation/runtime | Evidence/status |
|---|---|---|---|---|
| IP01 | Ingestion -> Kafka | Vu Van Phong | `integration_tasks.py`, `event_bus.py`, `api.py`; Kafka `data.raw` | `evidence/ip01-kafka-consume.json`; **PASS** |
| IP02 | Kafka -> Airflow | Vu Van Phong | `event_bus.py`, `airflow/dags/lab28_ingestion_pipeline.py` | `evidence/ip02-airflow-run.json`; **PASS** |
| IP03 | Spark -> Delta | Vu Van Phong | `integration_tasks.py`, `delta_store.py`, `spark/delta_merge.py` | `evidence/ip03-delta-history.json`; **PASS** |
| IP04 | Delta -> Feast | Vu Van Phong | `integration_tasks.py`, `feature_store.py`, `feature-repo/` | `evidence/ip04-feast-online.json`; **PASS** |
| IP05 | Documents -> Qdrant | Vu Van Phong | `vector_store.py`; hybrid dense/sparse retrieval | `evidence/ip05-qdrant-search.json`; **PASS** |
| IP06 | Evaluation -> MLflow | Vu Van Phong | `model_registry.py`; champion alias and rollback | `evidence/ip06-mlflow-release.json`, `evidence/rollback.json`; **PASS** for registry/promotion |
| IP07 | RAG -> real vLLM | Vu Van Phong | `llm_client.py`, `compose.gpu.yaml` | `evidence/ip07-vllm-identity.json`; **UNVERIFIED** without real GPU vLLM |
| IP08 | API -> Envoy | Vu Van Phong | `api.py`, `gateway/envoy.yaml` | `evidence/ip08-gateway.json`; **PASS** for non-GPU gateway policy |
| IP09 | Components -> metrics | Vu Van Phong | `monitoring/prometheus.yml`, `alerts.yml`, Grafana provisioning | `evidence/ip09-prometheus-targets.json`, `evidence/ip09-grafana-dashboards.json`; **PASS** for non-GPU targets |
| IP10 | OTLP trace | Vu Van Phong | `telemetry.py`, `monitoring/otel-collector.yaml` | `evidence/ip10-trace.json`; **PARTIAL**: local non-GPU path PASS, serving/LangSmith UNVERIFIED |

## Readiness semantics

`/health` is process liveness and remains 200 without dependency calls. `/ready`
uses the same probes as the serving path and returns 503 only for a mandatory
failure. Kafka, MLflow and Qdrant are mandatory; Feast is optional and visible
as `degraded`; vLLM is mandatory when real serving is required by configuration.
The four student boundaries in `src/lab28_platform/integration_tasks.py`
implement header propagation, replay-safe deduplication, Feast request
construction and severity-aware status.

## Live validation boundary

The full Docker Compose profile was healthy and the non-GPU integration suite
passed `56` selected tests. J1-J5 and the Prometheus/Grafana/gateway tests have
separate runtime transcripts and evidence. The process-level
`integration-report.json` intentionally keeps outside-process points
`unverified` and IP07 `not_ready`; it was not manually turned green.

Real vLLM, the GPU serving leg, external LangSmith and a Kubernetes cluster
require external resources not present in this environment. Kubernetes static
validation passed, but no live apply was attempted because there is no current
authorized cluster context. See [ANSWERS.md](../ANSWERS.md) for exact runtime
values and production gaps.
