"""Model providers and the model registry."""

from neuronium_agent.providers.anthropic import AnthropicProvider, DEFAULT_MODEL as ANTHROPIC_DEFAULT_MODEL
from neuronium_agent.providers.base import ModelProvider, ModelRequest, ModelResponse
from neuronium_agent.providers.gemini import GeminiProvider, DEFAULT_MODEL as GEMINI_DEFAULT_MODEL
from neuronium_agent.providers.mock import MockModelProvider
from neuronium_agent.providers.openai import OpenAIProvider, DEFAULT_MODEL as OPENAI_DEFAULT_MODEL
from neuronium_agent.providers.registry import ModelRegistry, default_registry

# Backward-compat alias.
DEFAULT_MODEL = ANTHROPIC_DEFAULT_MODEL


__all__ = [
    "ANTHROPIC_DEFAULT_MODEL",
    "AnthropicProvider",
    "DEFAULT_MODEL",
    "GEMINI_DEFAULT_MODEL",
    "GeminiProvider",
    "ModelProvider",
    "ModelRegistry",
    "ModelRequest",
    "ModelResponse",
    "MockModelProvider",
    "OPENAI_DEFAULT_MODEL",
    "OpenAIProvider",
    "default_registry",
]
