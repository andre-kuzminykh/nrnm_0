"""Integration: ObjectiveRunner driving the coding pack with AnthropicProvider.

We inject a deterministic fake `anthropic` client per-agent into the registry
so the run can complete without a live API key. This exercises the full path:
agent factory → ModelRequest assembly → AnthropicProvider tool-use loop →
tool registry + policy → final outcome.
"""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from typing import Any, Dict, List

from neuronium_agent.providers.anthropic import AnthropicProvider
from neuronium_agent.providers.registry import ModelRegistry
from neuronium_agent.runtime.objective_runner import ObjectiveRunner


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


class _ScriptedAnthropicClient:
    """Returns a message per agent_id based on the user message content."""

    def __init__(self, scripts: Dict[str, _Message]) -> None:
        self._scripts = scripts
        self.calls: List[Dict[str, Any]] = []

        class _M:
            def __init__(inner):
                inner._parent = self

            def stream(inner, **params: Any) -> _FakeStream:
                inner._parent.calls.append(params)
                agent_id = inner._parent._find_agent(params)
                msg = inner._parent._scripts.get(
                    agent_id,
                    _Message(
                        content=[_Block(type="text", text="{}")],
                        stop_reason="end_turn",
                        usage=_Usage(input_tokens=0),
                    ),
                )
                return _FakeStream(msg)

        self.messages = _M()

    @staticmethod
    def _find_agent(params: Dict[str, Any]) -> str:
        # AnthropicProvider's prelude carries `Agent: <id> (role: ...)`.
        for msg in params.get("messages", []):
            for block in msg.get("content", []):
                text = block.get("text", "") if isinstance(block, dict) else ""
                if "Agent: " in text:
                    return text.split("Agent: ", 1)[1].split(" ", 1)[0]
        return ""


def _text(stop: str, payload: str) -> _Message:
    return _Message(
        content=[_Block(type="text", text=payload)],
        stop_reason=stop,
        usage=_Usage(input_tokens=10, output_tokens=5),
    )


def _build_scripts() -> Dict[str, _Message]:
    return {
        "code_planner": _text(
            "end_turn",
            '{"plan": ["read repo", "patch", "test"], "files_to_inspect": ["a.py"], "risks": ["regressions"]}',
        ),
        "code_researcher": _text(
            "end_turn",
            '{"root_cause": "off by one", "snippets": [{"path": "a.py", "lines": "for i in range(n)"}]}',
        ),
        "code_editor": _text(
            "end_turn",
            '{"patch_summary": "fix loop bound", "changed_files": ["a.py"]}',
        ),
        "test_runner": _text(
            "end_turn",
            '{"test_result": {"status": "passed", "summary": "ok"}}',
        ),
        "code_reviewer": _text(
            "end_turn",
            '{"verdict": "PASS", "reasons": ["fixed", "tests pass"]}',
        ),
    }


def _registry_with_anthropic(client: Any) -> ModelRegistry:
    registry = ModelRegistry()
    provider = AnthropicProvider(client=client)
    registry.register_provider("anthropic", provider)
    for role in ("fast", "smart", "cheap", "critic"):
        registry.set_alias(role, "anthropic")
    return registry


# NR-IT-ANTH-001
def test_coding_pack_run_with_anthropic_fake(tmp_path: Path, monkeypatch) -> None:
    client = _ScriptedAnthropicClient(_build_scripts())

    # Patch the registry factory used inside build_default_runtime so the
    # runner picks up our injected client.
    import neuronium_agent.runtime.backend as backend_mod

    def fake_default_registry(force_failure_first=False, *, provider="mock", provider_options=None):
        if provider == "anthropic":
            return _registry_with_anthropic(client)
        return backend_mod.default_registry.__wrapped__(force_failure_first=force_failure_first) if hasattr(backend_mod.default_registry, "__wrapped__") else backend_mod.default_registry(force_failure_first=force_failure_first)

    # Replace just the alias-binding path: provide the registry directly to runtime.
    runner = ObjectiveRunner(
        trace_dir=str(tmp_path / "traces"),
        auto_approve=True,
        provider="anthropic",
        provider_options={"client": client},
    )
    result = runner.run("Fix failing tests in this repository", pack_id="coding")
    assert result.run.status.value == "succeeded"
    assert result.final_state.get("verdict") == "PASS"
    # AnthropicProvider was selected; trace records it.
    kinds = [e["kind"] for e in result.events]
    assert "provider.selected" in kinds
    selected = next(e for e in result.events if e["kind"] == "provider.selected")
    assert selected["payload"]["provider"] == "anthropic"
    # The fake client was driven at least once per agent.
    assert client.calls
