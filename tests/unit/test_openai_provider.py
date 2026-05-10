"""OpenAIProvider tests with an injected fake client."""

from __future__ import annotations

import json
from types import SimpleNamespace
from typing import Any, Dict, List

import pytest

import neuronium_agent.providers.openai as openai_mod
from neuronium_agent.providers.base import ModelRequest
from neuronium_agent.providers.openai import OpenAIProvider


class _FakeUsage(SimpleNamespace):
    pass


class _FakeMessage(SimpleNamespace):
    pass


class _FakeChoice(SimpleNamespace):
    pass


class _FakeResponse(SimpleNamespace):
    pass


class _FakeChatCompletions:
    def __init__(self, scripted: List[_FakeResponse]) -> None:
        self.scripted = list(scripted)
        self.calls: List[Dict[str, Any]] = []

    def create(self, **params: Any) -> _FakeResponse:
        self.calls.append(params)
        if not self.scripted:
            raise RuntimeError("no scripted responses left")
        return self.scripted.pop(0)


class _FakeChat(SimpleNamespace):
    pass


class _FakeOpenAIClient:
    def __init__(self, scripted: List[_FakeResponse]) -> None:
        self.chat = _FakeChat(completions=_FakeChatCompletions(scripted))


def _resp(content: str, finish: str = "stop", usage=(50, 10, 60)) -> _FakeResponse:
    msg = _FakeMessage(content=content, tool_calls=None)
    choice = _FakeChoice(message=msg, finish_reason=finish)
    return _FakeResponse(
        choices=[choice],
        usage=_FakeUsage(prompt_tokens=usage[0], completion_tokens=usage[1], total_tokens=usage[2]),
    )


def _resp_tool_call(name: str, args: Dict[str, Any], call_id: str = "call_1") -> _FakeResponse:
    fn = SimpleNamespace(name=name, arguments=json.dumps(args))
    tc = SimpleNamespace(id=call_id, type="function", function=fn)
    msg = _FakeMessage(content=None, tool_calls=[tc])
    choice = _FakeChoice(message=msg, finish_reason="tool_calls")
    return _FakeResponse(choices=[choice], usage=_FakeUsage(prompt_tokens=10, completion_tokens=5))


def test_provider_not_ready_without_openai(monkeypatch) -> None:
    monkeypatch.setattr(openai_mod, "_try_import_openai", lambda: None)
    provider = OpenAIProvider()
    assert provider.ready is False
    assert provider.diagnostics()["openai_installed"] is False
    with pytest.raises(RuntimeError):
        provider.generate(ModelRequest(role="smart", agent_id="x", prompt=""))


def test_basic_call_request_shape() -> None:
    client = _FakeOpenAIClient([_resp('{"plan": ["a"]}')])
    provider = OpenAIProvider(client=client, model="gpt-4o", max_output_tokens=2048)
    response = provider.generate(
        ModelRequest(role="planner", agent_id="p", prompt="system text", state={"x": 1}, expected_keys=["plan"])
    )
    params = client.chat.completions.calls[0]
    assert params["model"] == "gpt-4o"
    assert params["max_tokens"] == 2048
    assert params["messages"][0]["role"] == "system"
    assert params["messages"][0]["content"] == "system text"
    assert params["messages"][1]["role"] == "user"
    assert "Agent: p" in params["messages"][1]["content"]
    assert response.output == {"plan": ["a"]}
    assert response.usage["input_tokens"] == 50
    assert response.usage["output_tokens"] == 10
    assert response.usage["total_tokens"] == 60
    assert response.stop_reason == "stop"


def test_structured_output_uses_response_format() -> None:
    from neuronium_agent.agents.models import OutputContract

    client = _FakeOpenAIClient([_resp('{"plan": []}')])
    provider = OpenAIProvider(client=client)
    provider.generate(
        ModelRequest(
            role="planner",
            agent_id="p",
            prompt="sys",
            output_contract=OutputContract(type="object", required=["plan"]),
        )
    )
    params = client.chat.completions.calls[0]
    rf = params.get("response_format")
    assert rf and rf["type"] == "json_schema"
    assert rf["json_schema"]["schema"]["required"] == ["plan"]


def test_tool_use_loop_runs_executor() -> None:
    client = _FakeOpenAIClient(
        [
            _resp_tool_call("fs__read", {"path": "/x.txt"}, call_id="call_1"),
            _resp('{"summary": "read"}'),
        ]
    )
    provider = OpenAIProvider(client=client)
    captured: Dict[str, Any] = {}

    def executor(name: str, inp: Dict[str, Any]) -> Dict[str, Any]:
        captured["call"] = (name, dict(inp))
        return {"content": "hello"}

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
    assert response.output == {"summary": "read"}
    assert captured["call"][0] == "fs__read"
    # Second call should carry the tool result message.
    second = client.chat.completions.calls[1]["messages"][-1]
    assert second["role"] == "tool"
    assert second["tool_call_id"] == "call_1"


def test_executor_error_returns_json_error() -> None:
    client = _FakeOpenAIClient(
        [
            _resp_tool_call("explode", {}),
            _resp("{}"),
        ]
    )
    provider = OpenAIProvider(client=client)

    def boom(n: str, i: Dict[str, Any]):
        raise RuntimeError("nope")

    provider.generate(
        ModelRequest(
            role="executor",
            agent_id="x",
            prompt="",
            tools=[{"name": "explode", "description": "", "input_schema": {"type": "object"}}],
            tool_executor=boom,
        )
    )
    second = client.chat.completions.calls[1]["messages"][-1]
    payload = json.loads(second["content"])
    assert "error" in payload


def test_iteration_cap() -> None:
    client = _FakeOpenAIClient(
        [_resp_tool_call("x", {}, call_id=f"c_{i}") for i in range(10)]
    )
    provider = OpenAIProvider(client=client, max_tool_iterations=2)
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


def test_text_fallback_when_no_json() -> None:
    client = _FakeOpenAIClient([_resp("just words")])
    provider = OpenAIProvider(client=client)
    response = provider.generate(ModelRequest(role="planner", agent_id="p", prompt="sys"))
    assert response.output == {"text": "just words"}
