"""Run / session models."""

from __future__ import annotations

from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field


class RunStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    AWAITING_APPROVAL = "awaiting_approval"
    SUCCEEDED = "succeeded"
    FAILED = "failed"


class Run(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: str
    objective: str
    pack_id: Optional[str] = None
    status: RunStatus = RunStatus.PENDING
    inputs: Dict[str, Any] = Field(default_factory=dict)
    outputs: Dict[str, Any] = Field(default_factory=dict)
    attachments: List[str] = Field(default_factory=list)
    trace_path: Optional[str] = None
