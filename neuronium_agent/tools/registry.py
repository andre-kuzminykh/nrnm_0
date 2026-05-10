"""Tool registry mapping `<server>.<tool>` refs to callables."""

from __future__ import annotations

from typing import Any, Callable, Dict, List, Optional

from pydantic import BaseModel, ConfigDict


class ToolDescriptor(BaseModel):
    model_config = ConfigDict(extra="forbid", arbitrary_types_allowed=True)
    ref: str
    kind: str = "mock"
    risk: str = "low"
    schema_version: str = "0.1"
    fn: Optional[Callable[..., Any]] = None


class ToolRegistry:
    def __init__(self) -> None:
        self._tools: Dict[str, ToolDescriptor] = {}

    def register(
        self,
        ref: str,
        fn: Callable[..., Any],
        *,
        kind: str = "mock",
        risk: str = "low",
        schema_version: str = "0.1",
    ) -> None:
        self._tools[ref] = ToolDescriptor(
            ref=ref, fn=fn, kind=kind, risk=risk, schema_version=schema_version
        )

    def has(self, ref: str) -> bool:
        return ref in self._tools

    def list(self) -> List[str]:
        return sorted(self._tools.keys())

    def descriptor(self, ref: str) -> ToolDescriptor:
        if ref not in self._tools:
            raise KeyError(f"tool '{ref}' not registered")
        return self._tools[ref]

    def call(self, ref: str, **kwargs: Any) -> Any:
        descriptor = self.descriptor(ref)
        if descriptor.fn is None:
            raise RuntimeError(f"tool '{ref}' has no implementation")
        return descriptor.fn(**kwargs)
