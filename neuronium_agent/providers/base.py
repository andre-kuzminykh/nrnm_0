"""Provider base classes."""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Protocol

from pydantic import BaseModel, ConfigDict, Field


class ModelRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    role: str
    agent_id: str
    prompt: str
    state: Dict[str, Any] = Field(default_factory=dict)
    expected_keys: List[str] = Field(default_factory=list)


class ModelResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")
    role: str
    agent_id: str
    output: Dict[str, Any] = Field(default_factory=dict)


class ModelProvider(Protocol):
    """Protocol implemented by model providers (mock, openai, ...)."""

    name: str

    def supports(self, role: str) -> bool: ...

    def generate(self, request: ModelRequest) -> ModelResponse: ...
