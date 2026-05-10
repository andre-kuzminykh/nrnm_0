"""Trace recorder and secret redaction tests."""

from __future__ import annotations

import json

from neuronium_agent.trace.recorder import TraceRecorder
from neuronium_agent.trace.redact import redact_payload


def test_trace_sequence_increments(tmp_path) -> None:
    path = tmp_path / "trace.jsonl"
    recorder = TraceRecorder("r1", path=str(path))
    recorder.emit("a", {"x": 1})
    recorder.emit("b", {"y": 2})
    events = [json.loads(l) for l in path.read_text().splitlines()]
    assert [e["seq"] for e in events] == [1, 2]
    assert events[0]["kind"] == "a"


def test_trace_redacts_keys() -> None:
    payload = {"api_key": "sk-1234567890", "value": 1, "token": "abc"}
    redacted = redact_payload(payload)
    assert redacted["api_key"] == "***REDACTED***"
    assert redacted["token"] == "***REDACTED***"
    assert redacted["value"] == 1


def test_trace_redacts_inline_patterns() -> None:
    payload = {"note": "use sk-aaaaaaaa to call", "auth": "Bearer abc.def"}
    redacted = redact_payload(payload)
    assert "***REDACTED***" in redacted["note"]
    assert redacted["auth"].startswith("***REDACTED***") or "***REDACTED***" in redacted["auth"]


def test_trace_redacts_nested() -> None:
    payload = {"args": {"password": "p", "name": "ok"}}
    redacted = redact_payload(payload)
    assert redacted["args"]["password"] == "***REDACTED***"
    assert redacted["args"]["name"] == "ok"
