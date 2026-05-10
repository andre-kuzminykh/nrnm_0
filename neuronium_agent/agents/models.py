"""Agent models: definitions, instances, output contracts."""

from __future__ import annotations

from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field


class AgentRole(str, Enum):
    PLANNER = "planner"
    EXECUTOR = "executor"
    CRITIC = "critic"
    RESEARCHER = "researcher"
    RECOVERY = "recovery"
    CURATOR = "curator"
    DESIGNER = "designer"


class OutputContract(BaseModel):
    """Lightweight JSON-schema-ish contract for agent outputs."""

    model_config = ConfigDict(extra="forbid")
    type: str = "object"
    required: List[str] = Field(default_factory=list)
    properties: Dict[str, Dict[str, Any]] = Field(default_factory=dict)

    def validate_payload(self, payload: Any) -> List[str]:
        errors: List[str] = []
        if self.type == "object":
            if not isinstance(payload, dict):
                return ["expected object"]
            for key in self.required:
                if key not in payload:
                    errors.append(f"missing required field '{key}'")
        return errors


class AgentDefinition(BaseModel):
    """Static description of an agent declared by a pack."""

    model_config = ConfigDict(extra="forbid")
    id: str
    role: AgentRole
    goal: str = ""
    prompt_ref: Optional[str] = None
    model: str = "smart"
    tools: List[str] = Field(default_factory=list)
    permissions: Dict[str, str] = Field(default_factory=dict)
    skills: List[str] = Field(default_factory=list)
    memory_scope: str = "run"
    context_budget_tokens: int = 8000
    output_contract: Optional[OutputContract] = None
    acceptance_criteria: List[str] = Field(default_factory=list)
    pack_id: Optional[str] = None


class AgentInstance(BaseModel):
    """Per-run materialization of an AgentDefinition."""

    model_config = ConfigDict(extra="forbid")
    instance_id: str
    definition: AgentDefinition
    run_id: str
    state: Dict[str, Any] = Field(default_factory=dict)
    handoff_chain: List[str] = Field(default_factory=list)

    @property
    def id(self) -> str:
        return self.instance_id

    @property
    def role(self) -> AgentRole:
        return self.definition.role
