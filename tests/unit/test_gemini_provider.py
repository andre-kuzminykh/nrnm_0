"""GeminiProvider tests with an injected fake client."""

from __future__ import annotations

import json
from types import SimpleNamespace
from typing import Any, Dict, List

import pytest

import neuronium_agent.providers.gemini as gemini_mod
from neuronium_agent.providers.base import ModelRequest
from neuronium_agent.providers.gemini import GeminiProvider


class _FakeUsage(SimpleNamespace):
    pass


class _FakeContent(SimpleNamespace):
    pass


class _FakeCandidate(SimpleNamespace):
    pass


class _FakeResponse(SimpleNamespace):
    pass


class _FakeModels:
    def __init__(self, scripted: List[_FakeResponse]) -> None:
        self.scripted = list(scripted)
        self.calls: List[Dict[str, Any]] = []

    def generate_content(self, **params: Any) -> _FakeResponse:
        self.calls.append(params)
        if not self.scripted:
            raise RuntimeError("no scripted responses left")
        return self.scripted.pop(0)


class _FakeGeminiClient:
    def __init__(self, scripted: List[_FakeResponse]) -> None:
        self.models = _FakeModels(scripted)


def _text_part(text: str) -> SimpleNamespace:
    return SimpleNamespace(text=text, function_call=None)


def _fc_part(name: str, args: Dict[str, Any]) -> SimpleNamespace:
    return SimpleNamespace(text=None, function_call=SimpleNamespace(name=name, args=args))


def _resp(parts: List[SimpleNamespace], finish: str = "STOP", usage=(50, 10, 60)) -> _FakeResponse:
    candidate = _FakeCandidate(
        content=_FakeContent(parts=parts), finish_reason=finish
    )
    return _FakeResponse(
        candidates=[candidate],
        usage_metadata=_FakeUsage(
            prompt_token_count=usage[0],
            candidates_token_count=usage[1],
            total_token_count=usage[2],
        ),
    )


def test_provider_not_ready_without_genai(monkeypatch) -> None:
    monkeypatch.setattr(gemini_mod, "_try_import_genai", lambda: None)
    provider = GeminiProvider()
    assert provider.ready is False
    assert provider.diagnostics()["google_genai_installed"] is False
    with pytest.raises(RuntimeError):
        provider.generate(ModelRequest(role="smart", agent_id="x", prompt=""))


def test_basic_call_request_shape() -> None:
    client = _FakeGeminiClient([_resp([_text_part('{"plan": ["a"]}')])])
    provider = GeminiProvider(client=client, model="gemini-2.5-pro")
    response = provider.generate(
        ModelRequest(role="planner", agent_id="p", prompt="system text", state={"x": 1}, expected_keys=["plan"])
    )
    params = client.models.calls[0]
    assert params["model"] == "gemini-2.5-pro"
    assert params["system_instruction"] == "system text"
    assert params["contents"][0]["role"] == "user"
    user_text = params["contents"][0]["parts"][0]["text"]
    assert "Agent: p" in user_text
    assert response.output == {"plan": ["a"]}
    assert response.usage["input_tokens"] == 50
    assert response.usage["output_tokens"] == 10
    assert response.stop_reason == "STOP"


def test_tool_use_loop() -> None:
    client = _FakeGeminiClient(
        [
            _resp([_fc_part("fs__read", {"path": "/x.txt"})]),
            _resp([_text_part('{"summary": "ok"}')]),
        ]
    )
    provider = GeminiProvider(client=client)
    captured: Dict[str, Any] = {}

    def executor(name: str, inp: Dict[str, Any]):
        captured["call"] = (name, dict(inp))
        return {"content": "hi"}

    response = provider.generate(
        ModelRequest(
            role="executor",
            agent_id="x",
            prompt="sys",
            tools=[
                {
                    "name": "fs__read",
                    "description": "read",
                    "input_schema": {"type": "object", "properties": {"path": {"type": "string"}}},
                }
            ],
            tool_executor=executor,
        )
    )
    assert captured["call"] == ("fs__read", {"path": "/x.txt"})
    assert response.output == {"summary": "ok"}
    # Second call has a function_response part.
    second_user = client.models.calls[1]["contents"][-1]
    assert second_user["role"] == "user"
    fn_resp = second_user["parts"][0]["function_response"]
    assert fn_resp["name"] == "fs__read"


def test_iteration_cap() -> None:
    client = _FakeGeminiClient(
        [_resp([_fc_part("x", {})]) for _ in range(10)]
    )
    provider = GeminiProvider(client=client, max_tool_iterations=2)
    response = provider.generate(
        ModelRequest(
            role="executor",
            agent_id="x",
            prompt="",
            tools=[{"name": "x", "description": "", "input_schema": {"type": "object"}}],
            tool_executor=lambda n, i: {"ok": True},
        )
    )
    assert response.output == {"error": "tool_iteration_cap_exceeded"}


def test_text_fallback() -> None:
    client = _FakeGeminiClient([_resp([_text_part("just words")])])
    provider = GeminiProvider(client=client)
    response = provider.generate(ModelRequest(role="planner", agent_id="p", prompt=""))
    assert response.output == {"text": "just words"}
