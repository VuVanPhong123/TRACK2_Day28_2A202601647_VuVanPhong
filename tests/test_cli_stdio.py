"""CLI boundary tests for Unicode-safe operator output."""

from __future__ import annotations

from io import BytesIO, TextIOWrapper

from lab28_platform import cli


def test_stdout_is_reconfigured_for_unicode_third_party_messages(monkeypatch) -> None:
    raw = BytesIO()
    stream = TextIOWrapper(raw, encoding="cp1252")
    monkeypatch.setattr(cli.sys, "stdout", stream)

    cli._configure_stdout()
    stream.write("🏃 MLflow run\n")
    stream.flush()

    assert stream.encoding.lower().replace("-", "") == "utf8"
    assert raw.getvalue().replace(b"\r\n", b"\n") == "🏃 MLflow run\n".encode()
    stream.detach()
