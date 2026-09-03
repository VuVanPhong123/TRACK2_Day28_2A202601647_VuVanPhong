"""Unit coverage for the standard-library readiness load helper."""

from __future__ import annotations

import importlib.util
import io
from pathlib import Path
from urllib.error import HTTPError, URLError

import pytest

MODULE_PATH = Path(__file__).parents[1] / "load-tests" / "run_profile.py"
SPEC = importlib.util.spec_from_file_location("run_profile", MODULE_PATH)
assert SPEC and SPEC.loader
run_profile = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(run_profile)


def test_http_error_preserves_the_application_status(monkeypatch: pytest.MonkeyPatch) -> None:
    def raise_rate_limit(*args: object, **kwargs: object) -> object:
        raise HTTPError(
            url="http://localhost:8080/ready",
            code=429,
            msg="rate limited",
            hdrs=None,
            fp=io.BytesIO(),
        )

    monkeypatch.setattr(run_profile.urllib.request, "urlopen", raise_rate_limit)

    elapsed_ms, status = run_profile.request("http://localhost:8080")

    assert status == 429
    assert elapsed_ms >= 0


def test_transport_error_is_the_only_zero_status(monkeypatch: pytest.MonkeyPatch) -> None:
    def raise_transport_error(*args: object, **kwargs: object) -> object:
        raise URLError("connection refused")

    monkeypatch.setattr(run_profile.urllib.request, "urlopen", raise_transport_error)

    _, status = run_profile.request("http://localhost:8080")

    assert status == 0
