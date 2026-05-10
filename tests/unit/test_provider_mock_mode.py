"""Each real provider exposes mock_mode=True for credentialless development.

In mock_mode the provider is `ready=True` without an API key and `generate()`
delegates to MockModelProvider — so trace, tool routing, and pack execution
all proceed as if the real provider were live, but no network call happens.
"""

from __future__ import annotations

from neuronium_agent.providers.anthropic import AnthropicProvider
from neuronium_agent.providers.base import ModelRequest
from neuronium_agent.providers.gemini import GeminiProvider
from neuronium_agent.providers.openai import OpenAIProvider


def test_anthropic_mock_mode_ready_without_api_key(monkeypatch) -> None:
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    provider = AnthropicProvider(mock_mode=True)
    assert provider.ready is True
    diag = provider.diagnostics()
    assert diag["mock_mode"] is True
    response = provider.generate(
        ModelRequest(
            role="planner",
            agent_id="code_planner",
            prompt="sys",
            expected_keys=["plan", "files_to_inspect", "risks"],
        )
    )
    # MockModelProvider returns a deterministic plan for code_planner.
    assert "plan" in response.output
    assert response.usage.get("mock") == 1


def test_openai_mock_mode_returns_via_delegate(monkeypatch) -> None:
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    provider = OpenAIProvider(mock_mode=True)
    assert provider.ready is True
    response = provider.generate(
        ModelRequest(role="executor", agent_id="copywriter", prompt="sys")
    )
    assert response.output  # MockModelProvider has a copywriter handler


def test_gemini_mock_mode_returns_via_delegate(monkeypatch) -> None:
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    provider = GeminiProvider(mock_mode=True)
    assert provider.ready is True
    response = provider.generate(
        ModelRequest(role="researcher", agent_id="audience_researcher", prompt="sys")
    )
    assert response.output


def test_mock_mode_diagnostics() -> None:
    for provider in (
        AnthropicProvider(mock_mode=True),
        OpenAIProvider(mock_mode=True),
        GeminiProvider(mock_mode=True),
    ):
        diag = provider.diagnostics()
        assert diag["ready"] is True
        assert diag["mock_mode"] is True
