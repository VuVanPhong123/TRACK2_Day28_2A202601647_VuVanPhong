# J4 failure and recovery record

Observed on 2026-09-03 against the full Docker Compose profile.

## Incident and hypothesis

The injected incident was loss of Qdrant, the mandatory vector store. The
hypothesis was that the API would remain alive but become unready (`503`),
while a restored Qdrant would return the API to its pre-injection verdict. A
separate optional-dependency check stopped Feast; it was expected to remain a
served, visible `degraded` state rather than a total outage.

## Signals and readiness

- Baseline: direct API `/ready` was HTTP 200 with status `degraded`; Kafka,
  MLflow, Qdrant and Feast were ready, and only vLLM was unavailable.
- Feast injection: J4 observed the Feast component become unready without
  changing the baseline HTTP verdict; the component had an owner and recovered.
- Qdrant injection: J4 observed direct API `/ready` become HTTP 503 with
  status `not_ready` and the Qdrant component marked unready.
- Recovery: `docker compose start qdrant` restored Qdrant and direct API
  readiness to the baseline HTTP 200 / `degraded` verdict. The recovery helper
  also waited for Envoy's live `api::...::health_flags::healthy` signal before
  allowing the next gateway operation.

The GPU-marked full gateway-ejection assertion was not run because this
environment has no real vLLM. Envoy's configured active health check is
`/ready`, and the post-recovery admin state was healthy; this record does not
claim the gated ejection test passed.

## Data behavior and DLQ

The latest successful non-GPU J4 run used poison suffix `9c14a0b5`:

- good event: `it-j4-9c14a0b5`, one Delta feedback row after recovery;
- poison Kafka key: `it-j4-poison-9c14a0b5`;
- poison coordinates: topic `data.raw`, partition `0`, offset `29`;
- DLQ category: `validation`, attempts `1`, one matching envelope;
- poison-batch Airflow run: `it-ce528fba`, state `success`;
- valid replay asker: `it-j4-replay-332effd0`;
- replay Airflow run: `it-6186051d`, state `success`;
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
