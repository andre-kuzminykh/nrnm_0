"""Model registry: maps aliases (fast/smart/cheap/critic) to providers."""

from __future__ import annotations

from typing import Any, Dict, Optional

from neuronium_agent.providers.base import ModelProvider, ModelRequest, ModelResponse
from neuronium_agent.providers.mock import MockModelProvider


class ModelRegistry:
    def __init__(self) -> None:
        self._aliases: Dict[str, str] = {
            "fast": "mock",
            "smart": "mock",
            "cheap": "mock",
            "critic": "mock",
        }
        self._providers: Dict[str, ModelProvider] = {}

    def register_provider(self, name: str, provider: ModelProvider) -> None:
        self._providers[name] = provider

    def set_alias(self, alias: str, provider_name: str) -> None:
        self._aliases[alias] = provider_name

    def alias(self, alias: str) -> Optional[str]:
        return self._aliases.get(alias)

    def get_provider(self, alias_or_name: str) -> ModelProvider:
        provider_name = self._aliases.get(alias_or_name, alias_or_name)
        if provider_name not in self._providers:
            raise KeyError(f"provider '{provider_name}' not registered")
        return self._providers[provider_name]

    def has_provider(self, name: str) -> bool:
        return name in self._providers

    def generate(self, alias: str, request: ModelRequest) -> ModelResponse:
        return self.get_provider(alias).generate(request)


def default_registry(
    force_failure_first: bool = False,
    *,
    provider: str = "mock",
    provider_options: Optional[Dict[str, Any]] = None,
) -> ModelRegistry:
    """Build a model registry seeded with the requested provider.

    The mock provider is always registered so `provider="anthropic"` can fall
    back to deterministic mock outputs in tests / CI.
    """
    registry = ModelRegistry()
    registry.register_provider(
        "mock", MockModelProvider(force_failure_first=force_failure_first)
    )
    if provider == "anthropic":
        try:
            from neuronium_agent.providers.anthropic import AnthropicProvider

            options = dict(provider_options or {})
            anthropic_provider = AnthropicProvider(**options)
            registry.register_provider("anthropic", anthropic_provider)
            if anthropic_provider.ready:
                for role in ("fast", "smart", "cheap", "critic"):
                    registry.set_alias(role, "anthropic")
        except Exception:  # noqa: BLE001
            pass
    elif provider != "mock":
        # Unknown provider: keep mock as the active backend.
        pass
    return registry
