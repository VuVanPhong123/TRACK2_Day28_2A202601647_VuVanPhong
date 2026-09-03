"""CLI bulk-seed tests for gateway rate-limit handling."""

from __future__ import annotations

from types import SimpleNamespace

from lab28_platform import cli


def test_seed_retries_a_rate_limited_request(monkeypatch) -> None:
    responses = [
        SimpleNamespace(status_code=429, headers={}),
        SimpleNamespace(status_code=202, headers={}),
    ]
    calls: list[tuple[str, dict[str, str]]] = []
    sleeps: list[float] = []

    class FakeClient:
        def post(self, path: str, *, json: dict[str, str]) -> SimpleNamespace:
            calls.append((path, json))
            return responses.pop(0)

    monkeypatch.setattr(cli.time, "sleep", sleeps.append)

    response = cli._post_with_rate_limit_backoff(FakeClient(), "/api/v1/documents", {"id": "a"})

    assert response.status_code == 202
    assert calls == [
        ("/api/v1/documents", {"id": "a"}),
        ("/api/v1/documents", {"id": "a"}),
    ]
    assert sleeps == [1.0]


def test_seed_uses_retry_after_header(monkeypatch) -> None:
    responses = [
        SimpleNamespace(status_code=429, headers={"retry-after": "2.5"}),
        SimpleNamespace(status_code=202, headers={}),
    ]

    class FakeClient:
        def post(self, path: str, *, json: dict[str, str]) -> SimpleNamespace:
            return responses.pop(0)

    sleeps: list[float] = []
    monkeypatch.setattr(cli.time, "sleep", sleeps.append)

    cli._post_with_rate_limit_backoff(FakeClient(), "/api/v1/feedback", {"id": "b"})

    assert sleeps == [2.5]
