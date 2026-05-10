"""AnthropicProvider tests with an injected fake client.

These tests verify request shape and behavior without calling the real API.
The `anthropic` package is not installed in CI; the provider remains importable
via `_try_import_anthropic` returning None, and we supply a fake client directly.
"""

from __future__ import annotations

import json
from types import SimpleNamespace
from typing import Any, Dict, List

import pytest

import neuronium_agent.providers.anthropic as anthropic_mod
from neuronium_agent.agents.models import AgentRole, OutputContract
from neuronium_agent.providers.anthropic import AnthropicProvider
from neuronium_agent.providers.base import ModelRequest


class _Block(SimpleNamespace):
    pass


class _Usage(SimpleNamespace):
    pass


class _Message(SimpleNamespace):
    pass


class _FakeStream:
    def __init__(self, message: _Message) -> None:
        self._message = message

    def __iter__(self):
        return iter([])

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def get_final_message(self) -> _Message:
        return self._message


class _FakeMessages:
    def __init__(self, scripted: List[_Message]) -> None:
        self.scripted = list(scripted)
        self.calls: List[Dict[str, Any]] = []

    def stream(self, **params: Any) -> _FakeStream:
        self.calls.append(params)
        if not self.scripted:
            raise RuntimeError("no scripted messages left")
        return _FakeStream(self.scripted.pop(0))


class _FakeClient:
    def __init__(self, scripted: List[_Message]) -> None:
        self.messages = _FakeMessages(scripted)


def _text_block(text: str) -> _Block:
    return _Block(type="text", text=text)


def _thinking_block(text: str) -> _Block:
    return _Block(type="thinking", thinking=text)


def _tool_use_block(name: str, input_: Dict[str, Any], block_id: str = "tu_1") -> _Block:
    return _Block(type="tool_use", name=name, input=input_, id=block_id)


def _msg(content: List[Any], stop: str, usage: Dict[str, int] | None = None) -> _Message:
    return _Message(
        content=content,
        stop_reason=stop,
        usage=_Usage(
            input_tokens=(usage or {}).get("input_tokens"),
            output_tokens=(usage or {}).get("output_tokens"),
            cache_creation_input_tokens=(usage or {}).get("cache_creation_input_tokens"),
            cache_read_input_tokens=(usage or {}).get("cache_read_input_tokens"),
        ),
    )


# ---- fallback / readiness ----


# NR-UT-ANTH-001
def test_provider_not_ready_without_anthropic(monkeypatch) -> None:
    monkeypatch.setattr(anthropic_mod, "_try_import_anthropic", lambda: None)
    provider = AnthropicProvider()
    assert provider.ready is False
    diag = provider.diagnostics()
    assert diag["anthropic_installed"] is False
    assert "not installed" in (diag["init_error"] or "")
    with pytest.raises(RuntimeError):
        provider.generate(ModelRequest(role="smart", agent_id="x", prompt=""))


def test_provider_ready_with_injected_client() -> None:
    client = _FakeClient([_msg([_text_block("{}")], "end_turn")])
    provider = AnthropicProvider(client=client)
    assert provider.ready is True
    assert provider.diagnostics()["ready"] is True


# ---- request shape ----


# NR-UT-ANTH-002
def test_basic_call_emits_expected_params() -> None:
    client = _FakeClient(
        [_msg([_text_block('{"plan": ["step"]}')], "end_turn", {"input_tokens": 10})]
    )
    provider = AnthropicProvider(client=client, model="claude-opus-4-7", max_tokens=8000)
    contract = OutputContract(type="object", required=["plan"])
    response = provider.generate(
        ModelRequest(
            role="planner",
            agent_id="code_planner",
            prompt="# Planner system prompt",
            state={"objective": "x"},
            expected_keys=["plan"],
            output_contract=contract,
        )
    )
    assert client.messages.calls, "client should have been called"
    params = client.messages.calls[0]
    # Opus 4.7 hard rules per Claude API skill
    assert params["model"] == "claude-opus-4-7"
    assert "temperature" not in params
    assert "top_p" not in params
    assert "top_k" not in params
    # Adaptive thinking with summarized display
    assert params["thinking"] == {"type": "adaptive", "display": "summarized"}
    # Effort routes — planner → xhigh
    assert params["output_config"]["effort"] == "xhigh"
    # Output contract → JSON schema
    fmt = params["output_config"]["format"]
    assert fmt["type"] == "json_schema"
    assert fmt["schema"]["required"] == ["plan"]
    # Prompt caching: cache_control on the last system text block
    last_system_block = params["system"][-1]
    assert last_system_block["cache_control"] == {"type": "ephemeral"}
    # State is in the user message, not in system
    user_msg = params["messages"][0]
    assert user_msg["role"] == "user"
    user_text_blocks = [b for b in user_msg["content"] if b["type"] == "text"]
    assert any('"objective"' in b["text"] for b in user_text_blocks)
    # No "temperature" interpreted as deterministic — opus 4.7 disallows.
    # Parsed output
    assert response.output == {"plan": ["step"]}
    assert response.usage["input_tokens"] == 10
    assert response.stop_reason == "end_turn"


def test_effort_routes_per_role() -> None:
    client = _FakeClient([
        _msg([_text_block("{}")], "end_turn"),
        _msg([_text_block("{}")], "end_turn"),
        _msg([_text_block("{}")], "end_turn"),
    ])
    provider = AnthropicProvider(client=client)
    for role, expected in [("fast", "low"), ("executor", "high"), ("critic", "xhigh")]:
        provider.generate(ModelRequest(role=role, agent_id="x", prompt="sys"))
    efforts = [c["output_config"]["effort"] for c in client.messages.calls]
    assert efforts == ["low", "high", "xhigh"]
    # Fast role disables thinking
    assert client.messages.calls[0]["thinking"] == {"type": "disabled"}
    # Critic uses adaptive + summarized
    assert client.messages.calls[2]["thinking"] == {"type": "adaptive", "display": "summarized"}


def test_prompt_caching_can_be_disabled() -> None:
    client = _FakeClient([_msg([_text_block("{}")], "end_turn")])
    provider = AnthropicProvider(client=client, enable_prompt_cache=False)
    provider.generate(ModelRequest(role="planner", agent_id="x", prompt="hello"))
    last_block = client.messages.calls[0]["system"][-1]
    assert "cache_control" not in last_block


# ---- tool-use loop ----


# NR-UT-ANTH-003
def test_tool_use_loop_runs_executor_and_iterates() -> None:
    client = _FakeClient(
        [
            _msg(
                [_tool_use_block("fs__read", {"path": "/x.txt"}, "use_1")],
                "tool_use",
            ),
            _msg([_text_block('{"summary": "read"}')], "end_turn"),
        ]
    )
    provider = AnthropicProvider(client=client)
    captured: Dict[str, Any] = {}

    def executor(name: str, inp: Dict[str, Any]) -> Dict[str, Any]:
        captured["call"] = (name, dict(inp))
        return {"content": "hello"}

    response = provider.generate(
        ModelRequest(
            role="executor",
            agent_id="code_editor",
            prompt="be careful",
            state={},
            expected_keys=["summary"],
            tools=[
                {
                    "name": "fs__read",
                    "description": "read file",
                    "input_schema": {"type": "object", "properties": {"path": {"type": "string"}}},
                }
            ],
            tool_executor=executor,
        )
    )
    assert response.output == {"summary": "read"}
    assert captured["call"] == ("fs__read", {"path": "/x.txt"})
    # Second call must have tools and the tool_result appended.
    second_call = client.messages.calls[1]
    assert second_call["messages"][-1]["role"] == "user"
    tool_result = second_call["messages"][-1]["content"][0]
    assert tool_result["type"] == "tool_result"
    assert tool_result["tool_use_id"] == "use_1"


def test_tool_executor_error_is_reported_as_is_error() -> None:
    client = _FakeClient(
        [
            _msg([_tool_use_block("explode", {}, "tu_1")], "tool_use"),
            _msg([_text_block('{"x": 1}')], "end_turn"),
        ]
    )
    provider = AnthropicProvider(client=client)

    def boom(name: str, inp: Dict[str, Any]) -> Any:
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
    second_call = client.messages.calls[1]
    result_block = second_call["messages"][-1]["content"][0]
    assert result_block["is_error"] is True
    assert "nope" in result_block["content"]


def test_tool_use_without_executor_falls_through() -> None:
    client = _FakeClient([_msg([_tool_use_block("x", {}, "tu_1")], "tool_use")])
    provider = AnthropicProvider(client=client)
    response = provider.generate(
        ModelRequest(role="executor", agent_id="x", prompt="", tools=[])
    )
    # With no tool_executor, we don't iterate; final output is best-effort text/JSON.
    assert response.stop_reason == "tool_use"


def test_tool_iteration_cap() -> None:
    # Always returns tool_use → loop should cap and return an error.
    client = _FakeClient(
        [
            _msg([_tool_use_block("x", {}, f"tu_{i}")], "tool_use")
            for i in range(10)
        ]
    )
    provider = AnthropicProvider(client=client, max_tool_iterations=2)
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


# ---- thinking ----


def test_thinking_text_collected_into_summary() -> None:
    client = _FakeClient(
        [
            _msg(
                [
                    _thinking_block("step 1: think"),
                    _thinking_block("step 2: choose"),
                    _text_block('{"plan": ["a"]}'),
                ],
                "end_turn",
            )
        ]
    )
    provider = AnthropicProvider(client=client)
    response = provider.generate(
        ModelRequest(role="planner", agent_id="p", prompt="sys")
    )
    assert response.thinking_summary is not None
    assert "step 1" in response.thinking_summary
    assert response.output == {"plan": ["a"]}


# ---- JSON parsing edge cases ----


def test_parser_handles_fenced_json() -> None:
    fence = "```json\n{\"plan\": [\"a\", \"b\"]}\n```"
    client = _FakeClient([_msg([_text_block(fence)], "end_turn")])
    provider = AnthropicProvider(client=client)
    response = provider.generate(ModelRequest(role="planner", agent_id="p", prompt="sys"))
    assert response.output["plan"] == ["a", "b"]


def test_parser_extracts_first_object_in_prose() -> None:
    prose = "Sure! Here is your answer: {\"plan\": [\"x\"]} and some more text."
    client = _FakeClient([_msg([_text_block(prose)], "end_turn")])
    provider = AnthropicProvider(client=client)
    response = provider.generate(ModelRequest(role="planner", agent_id="p", prompt="sys"))
    assert response.output == {"plan": ["x"]}


def test_parser_falls_back_to_text_when_no_json() -> None:
    client = _FakeClient([_msg([_text_block("just words")], "end_turn")])
    provider = AnthropicProvider(client=client)
    response = provider.generate(ModelRequest(role="planner", agent_id="p", prompt="sys"))
    assert response.output == {"text": "just words"}


# ---- usage accumulation ----


def test_usage_accumulates_across_iterations() -> None:
    client = _FakeClient(
        [
            _msg(
                [_tool_use_block("x", {}, "tu_1")],
                "tool_use",
                {"input_tokens": 100, "output_tokens": 5, "cache_read_input_tokens": 50},
            ),
            _msg(
                [_text_block("{}")],
                "end_turn",
                {"input_tokens": 30, "output_tokens": 12, "cache_read_input_tokens": 50},
            ),
        ]
    )
    provider = AnthropicProvider(client=client)
    response = provider.generate(
        ModelRequest(
            role="executor",
            agent_id="x",
            prompt="",
            tools=[{"name": "x", "description": "", "input_schema": {"type": "object"}}],
            tool_executor=lambda n, i: {"ok": True},
        )
    )
    assert response.usage["input_tokens"] == 130
    assert response.usage["output_tokens"] == 17
    assert response.usage["cache_read_input_tokens"] == 100
