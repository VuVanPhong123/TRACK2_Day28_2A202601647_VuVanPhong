# J4 failure and recovery record

Observed on 2026-09-03 against the full Docker Compose profile.

## Incident and hypothesis

The injected incident was loss of Qdrant, the mandatory vector store. The
hypothesis was that the API would remain alive but become unready (`503`),
while a restored Qdrant would return the API to its pre-injection verdict. A
separate optional-dependency check stopped Feast; it was expected to remain a
served, visible `degraded` state rather than a total outage.

## Signals and readiness

- Baseline: direct API `/ready` was HTTP 200 with status `ready`; Kafka,
  MLflow, Qdrant, Feast and the real vLLM identity probe were ready.
- Feast injection: J4 observed the Feast component become unready without
  changing the baseline HTTP verdict; the component had an owner and recovered.
- Qdrant injection: J4 observed direct API `/ready` become HTTP 503 with
  status `not_ready` and the Qdrant component marked unready.
- Recovery: `docker compose start qdrant` restored Qdrant and direct API
  readiness to the baseline HTTP 200 / `degraded` verdict. The recovery helper
  also waited for Envoy's live `api::...::health_flags::healthy` signal before
  allowing the next gateway operation.

The GPU-marked full gateway-ejection assertion passed against the real vLLM
baseline. Envoy's configured active health check is `/ready`; after Qdrant
recovery the API and Envoy admin state returned to healthy.

## Data behavior and DLQ

The latest successful real-vLLM J4 run used poison suffix `faf61031`:

- good event: `it-j4-faf61031`, one Delta feedback row after recovery;
- poison Kafka key: `it-j4-poison-faf61031`;
- poison coordinates: topic `data.raw`, partition `1`, offset `53`;
- DLQ category: `validation`, attempts `1`, one matching envelope;
- poison-batch Airflow run: `it-c7381f6b`, state `success`;
- valid replay asker: `it-j4-replay-ae4b1b4b`;
- replay Airflow run: `it-62b74716`, state `success`;
- the replayed valid fact has one Delta row, not a duplicate.

The malformed payload and its base64 representation remain in the runtime
DLQ store; no private credential or runtime database is included in this
submission artifact.

## Recovery conclusion

The successful J4 transcript proves optional Feast degradation, mandatory
Qdrant readiness failure and recovery, poison parking, good-record survival,
valid replay and idempotent row preservation. Source: `integration-tests/test_j4_degraded_recovery.py`,
`.lab28/j4-runtime.txt` (runtime-only transcript), and the Delta/Kafka values
recorded above.
