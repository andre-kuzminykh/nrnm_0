"""Model registry: maps aliases (fast/smart/cheap/critic) and provider:model
strings to concrete `ModelProvider` instances."""

from __future__ import annotations

from typing import Any, Dict, Optional, Tuple

from neuronium_agent.providers.base import ModelProvider, ModelRequest, ModelResponse
from neuronium_agent.providers.mock import MockModelProvider


def _split_provider_model(name: str) -> Tuple[Optional[str], Optional[str]]:
    """Parse `<provider>:<model_id>` into (provider_name, model_id).

    Returns `(None, None)` for plain alias strings.
    """
    if ":" in name:
        provider_name, model_id = name.split(":", 1)
        return provider_name.strip(), model_id.strip() or None
    return None, None


class ModelRegistry:
    def __init__(self) -> None:
        self._aliases: Dict[str, str] = {
            "fast": "mock",
            "smart": "mock",
            "cheap": "mock",
            "critic": "mock",
            "vision": "mock",
            "long_context": "mock",
        }
        self._providers: Dict[str, ModelProvider] = {}

    def register_provider(self, name: str, provider: ModelProvider) -> None:
        self._providers[name] = provider

    def set_alias(self, alias: str, provider_name: str) -> None:
        self._aliases[alias] = provider_name

    def alias(self, alias: str) -> Optional[str]:
        return self._aliases.get(alias)

    def has_provider(self, name: str) -> bool:
        return name in self._providers

    def list_providers(self) -> Dict[str, ModelProvider]:
        return dict(self._providers)

    def get_provider(self, alias_or_name: str) -> ModelProvider:
        provider_name, _model_id = _split_provider_model(alias_or_name)
        if provider_name is not None:
            if provider_name not in self._providers:
                raise KeyError(
                    f"provider '{provider_name}' not registered (available: {sorted(self._providers)})"
                )
            return self._providers[provider_name]
        resolved = self._aliases.get(alias_or_name, alias_or_name)
        if resolved not in self._providers:
            raise KeyError(f"provider '{resolved}' not registered")
        return self._providers[resolved]

    def generate(self, alias: str, request: ModelRequest) -> ModelResponse:
        # Honor per-call model override embedded in the alias string.
        provider_name, model_id = _split_provider_model(alias)
        provider = self.get_provider(alias)
        original_model = None
        if model_id and hasattr(provider, "model_id"):
            original_model = getattr(provider, "model_id", None)
            try:
                provider.model_id = model_id  # type: ignore[attr-defined]
            except Exception:  # noqa: BLE001
                pass
        try:
            return provider.generate(request)
        finally:
            if original_model is not None:
                try:
                    provider.model_id = original_model  # type: ignore[attr-defined]
                except Exception:  # noqa: BLE001
                    pass


def default_registry(
    force_failure_first: bool = False,
    *,
    provider: str = "mock",
    provider_options: Optional[Dict[str, Any]] = None,
) -> ModelRegistry:
    """Build a model registry seeded with the requested provider.

    The mock provider is always registered as a fallback. When `provider` is
    `"anthropic"`, `"openai"`, or `"gemini"`, that provider is constructed
    (with `provider_options`) and aliased to all default roles when ready.

    For multi-provider routing (different agents use different providers),
    pass `provider="multi"` and configure aliases / per-agent models in the
    pack DSL.
    """
    registry = ModelRegistry()
    registry.register_provider(
        "mock", MockModelProvider(force_failure_first=force_failure_first)
    )
    options = dict(provider_options or {})
    if provider == "anthropic":
        try:
            from neuronium_agent.providers.anthropic import AnthropicProvider

            inst = AnthropicProvider(**options)
            registry.register_provider("anthropic", inst)
            if inst.ready:
                for role in ("fast", "smart", "cheap", "critic", "vision", "long_context"):
                    registry.set_alias(role, "anthropic")
        except Exception:  # noqa: BLE001
            pass
    elif provider == "openai":
        try:
            from neuronium_agent.providers.openai import OpenAIProvider

            inst = OpenAIProvider(**options)
            registry.register_provider("openai", inst)
            if inst.ready:
                for role in ("fast", "smart", "cheap", "critic", "vision"):
                    registry.set_alias(role, "openai")
        except Exception:  # noqa: BLE001
            pass
    elif provider == "gemini":
        try:
            from neuronium_agent.providers.gemini import GeminiProvider

            inst = GeminiProvider(**options)
            registry.register_provider("gemini", inst)
            if inst.ready:
                for role in ("fast", "smart", "cheap", "critic", "vision", "long_context"):
                    registry.set_alias(role, "gemini")
        except Exception:  # noqa: BLE001
            pass
    elif provider == "multi":
        # Construct every provider that imports cleanly. Aliases are not
        # auto-routed — packs should use `provider:model` strings on each agent.
        for name, opts in (
            ("anthropic", options.get("anthropic", {})),
            ("openai", options.get("openai", {})),
            ("gemini", options.get("gemini", {})),
        ):
            try:
                cls = {
                    "anthropic": "AnthropicProvider",
                    "openai": "OpenAIProvider",
                    "gemini": "GeminiProvider",
                }[name]
                module = __import__(
                    f"neuronium_agent.providers.{name}", fromlist=[cls]
                )
                inst = getattr(module, cls)(**(opts or {}))
                registry.register_provider(name, inst)
            except Exception:  # noqa: BLE001
                continue
    return registry
