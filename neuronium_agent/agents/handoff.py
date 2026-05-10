"""Handoff protocol between agents."""

from __future__ import annotations

from typing import Any, Dict, Optional

from pydantic import BaseModel, ConfigDict


class Handoff(BaseModel):
    model_config = ConfigDict(extra="forbid")
    from_agent: str
    to_agent: str
    reason: str
    payload: Dict[str, Any] = {}
    follow_up: Optional[str] = None
