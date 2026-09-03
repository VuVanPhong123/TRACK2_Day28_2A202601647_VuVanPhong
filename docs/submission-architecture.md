# Submission architecture and ownership

![Lab 28 architecture](images/lab28-architecture-overview.png)

[SVG version](images/lab28-architecture-overview.svg)

The actual owner for every point in this individual submission is **Vu Van Phong**.
The role column retains the logical platform role from the instructor matrix; it does
not claim additional contributors.

| Point | Logical role | Owner | Implementation/runtime | Evidence/status |
|---|---|---|---|---|
| IP01 | Ingestion → Kafka | Vu Van Phong | `integration_tasks.py`, `event_bus.py`, `api.py`; Kafka `data.raw` | `evidence/ip01-kafka-consume.json`; live `UNVERIFIED` |
| IP02 | Kafka → Airflow | Vu Van Phong | `event_bus.py`, `airflow/dags/lab28_ingestion_pipeline.py` | `evidence/ip02-airflow-run.json`; live `UNVERIFIED` |
| IP03 | Spark → Delta | Vu Van Phong | `integration_tasks.py`, `delta_store.py`, `spark/delta_merge.py` | `evidence/ip03-delta-history.json`; live `UNVERIFIED` |
| IP04 | Delta → Feast | Vu Van Phong | `integration_tasks.py`, `feature_store.py`, `feature-repo/` | `evidence/ip04-feast-online.json`; live `UNVERIFIED` |
| IP05 | Documents → Qdrant | Vu Van Phong | `vector_store.py`; hybrid dense/sparse retrieval | `evidence/ip05-qdrant-search.json`; live `UNVERIFIED` |
| IP06 | Evaluation → MLflow | Vu Van Phong | `model_registry.py`; champion alias and rollback | `evidence/ip06-mlflow-release.json`; live `UNVERIFIED` |
| IP07 | RAG → real vLLM | Vu Van Phong | `llm_client.py`, `compose.gpu.yaml` | `evidence/ip07-vllm-identity.json`; GPU `UNVERIFIED` |
| IP08 | API → Envoy | Vu Van Phong | `api.py`, `gateway/envoy.yaml` | `evidence/ip08-gateway.json`; live `UNVERIFIED` |
| IP09 | Components → metrics | Vu Van Phong | `monitoring/prometheus.yml`, `alerts.yml`, Grafana provisioning | `evidence/ip09-*.json`; live `UNVERIFIED` |
| IP10 | OTLP trace | Vu Van Phong | `telemetry.py`, `monitoring/otel-collector.yaml` | `evidence/ip10-trace.json`; local live `UNVERIFIED`, LangSmith `UNVERIFIED` |

## Readiness semantics

`/health` is process liveness and remains 200 without dependency calls. `/ready` uses
the same probes as the serving path and returns 503 only for a mandatory failure.
Kafka, MLflow and Qdrant are mandatory; Feast is optional and visible as `degraded`;
vLLM is mandatory when real serving is required by configuration. The four student
boundaries in `src/lab28_platform/integration_tasks.py` implement header propagation,
replay-safe deduplication, Feast request construction and severity-aware status.

## Validation boundary

Fast/static validation is reproducible from the repository. Docker, Airflow, live
Prometheus/Grafana/Jaeger, real vLLM, LangSmith and a Kubernetes cluster require
external runtime resources; this submission reports those gates as `UNVERIFIED` when
they cannot be observed. See [ANSWERS.md](../ANSWERS.md) for the current evidence
boundary and production gaps.
