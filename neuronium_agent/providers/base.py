"""Provider base classes."""

from __future__ import annotations

from typing import Any, Callable, Dict, List, Optional, Protocol

from pydantic import BaseModel, ConfigDict, Field


ToolExecutor = Callable[[str, Dict[str, Any]], Any]


class ModelRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", arbitrary_types_allowed=True)
    role: str
    agent_id: str
    prompt: str
    state: Dict[str, Any] = Field(default_factory=dict)
    expected_keys: List[str] = Field(default_factory=list)
    tools: List[Dict[str, Any]] = Field(default_factory=list)
    tool_executor: Optional[Any] = None  # ToolExecutor callable
    output_contract: Optional[Any] = None  # OutputContract
    trace_emit: Optional[Any] = None  # Callable[[str, dict], None] for token/thinking events


class ModelResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")
    role: str
    agent_id: str
    output: Dict[str, Any] = Field(default_factory=dict)
    usage: Dict[str, Any] = Field(default_factory=dict)
    thinking_summary: Optional[str] = None
    stop_reason: Optional[str] = None


class ModelProvider(Protocol):
    """Protocol implemented by model providers (mock, anthropic, ...)."""

    name: str

    def supports(self, role: str) -> bool: ...

    def generate(self, request: ModelRequest) -> ModelResponse: ...
