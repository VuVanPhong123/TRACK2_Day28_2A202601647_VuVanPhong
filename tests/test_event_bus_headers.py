"""Regression coverage for the IP01 Kafka key/header distinction."""

from __future__ import annotations

from types import SimpleNamespace

from lab28_platform import event_bus
from lab28_platform.contracts import FeedbackPayload, IngestionEvent


class FakeProducer:
    def __init__(self) -> None:
        self.produced: dict[str, object] = {}

    def produce(self, topic: str, **kwargs: object) -> None:
        self.produced = {"topic": topic, **kwargs}

    def flush(self, _timeout: float) -> int:
        return 0


def test_publish_uses_entity_record_key_and_event_idempotency_header(monkeypatch) -> None:
    producer = FakeProducer()
    publisher = object.__new__(event_bus.EventPublisher)
    publisher._producer = producer
    publisher._settings = SimpleNamespace(delivery_timeout_seconds=1.0)

    event = IngestionEvent(
        idempotency_key="feedback:42",
        entity_id="student-7",
        traceparent="00-4bf92f3577b34da6a3ce929d0e0e4736-00f067aa0ba902b7-01",
        payload=FeedbackPayload(
            asker_id="student-7", text="Dịch vụ đủ dài để kiểm thử", rating=5
        ),
    )
    monkeypatch.setattr(event_bus, "current_traceparent", lambda: None)

    publisher.publish("data.raw", event.entity_id, event)

    assert producer.produced["key"] == b"student-7"
    headers = dict(producer.produced["headers"])  # type: ignore[arg-type]
    assert headers["idempotency-key"] == b"feedback:42"
    assert headers["traceparent"] == event.traceparent.encode()
