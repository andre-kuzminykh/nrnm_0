"""Pydantic models for the Workflow Pack DSL."""

from __future__ import annotations

from enum import Enum
from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, model_validator


class RiskClass(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class PermissionMode(str, Enum):
    ALLOW = "allow"
    DENY = "deny"
    REQUIRE_APPROVAL = "require_approval"


class PackMetadata(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: str
    name: str
    version: str = "0.1.0"
    schema_version: str = "0.1"
    compatible_neuronium: str = ">=0.1.0"
    domain: str = ""
    description: str = ""


class Objective(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: str
    user_phrases: List[str] = Field(default_factory=list)
    expected_outcomes: List[str] = Field(default_factory=list)


class PackOutputContract(BaseModel):
    model_config = ConfigDict(extra="forbid")
    type: str = "object"
    required: List[str] = Field(default_factory=list)
    properties: Dict[str, Dict[str, Any]] = Field(default_factory=dict)


class PackAgent(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: str
    role: str
    goal: str = ""
    model: str = "smart"
    prompt_ref: Optional[str] = None
    tools: List[str] = Field(default_factory=list)
    permissions: Dict[str, str] = Field(default_factory=dict)
    skills: List[str] = Field(default_factory=list)
    memory_scope: str = "run"
    context_budget_tokens: int = 8000
    output_contract: Optional[PackOutputContract] = None
    acceptance_criteria: List[str] = Field(default_factory=list)


class PackTool(BaseModel):
    model_config = ConfigDict(extra="forbid")
    ref: str
    kind: Literal["mcp", "builtin", "mock"] = "mcp"
    risk: RiskClass = RiskClass.LOW
    default_permission: Optional[PermissionMode] = None


class WorkflowPhase(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: str
    agent: str
    tools: List[str] = Field(default_factory=list)
    outputs: List[str] = Field(default_factory=list)
    requires_approval: bool = False
    prompt_ref: Optional[str] = None
    kind: Literal["model", "tool", "operator", "critic"] = "model"


class PackWorkflow(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: str
    objective_match: str
    phases: List[WorkflowPhase] = Field(default_factory=list)


class QualityGate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: str
    condition: str
    on_fail: Literal["retry", "replan", "abort"] = "replan"


class OutputTemplate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: str
    type: Literal["markdown", "json", "table"] = "markdown"
    includes: List[str] = Field(default_factory=list)


class PackTest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: str
    objective: str
    expected: List[str] = Field(default_factory=list)
    workflow: Optional[str] = None


class WorkflowPack(BaseModel):
    model_config = ConfigDict(extra="forbid")
    pack: PackMetadata
    objectives: List[Objective] = Field(default_factory=list)
    agents: List[PackAgent] = Field(default_factory=list)
    tools: List[PackTool] = Field(default_factory=list)
    workflows: List[PackWorkflow] = Field(default_factory=list)
    quality_gates: List[QualityGate] = Field(default_factory=list)
    outputs: List[OutputTemplate] = Field(default_factory=list)
    tests: List[PackTest] = Field(default_factory=list)

    @property
    def id(self) -> str:
        return self.pack.id

    @model_validator(mode="after")
    def _check_unique(self) -> "WorkflowPack":
        agent_ids = [a.id for a in self.agents]
        if len(agent_ids) != len(set(agent_ids)):
            raise ValueError("duplicate agent ids in pack")
        tool_refs = [t.ref for t in self.tools]
        if len(tool_refs) != len(set(tool_refs)):
            raise ValueError("duplicate tool refs in pack")
        return self

    def get_workflow_for_objective(self, objective_id: str) -> Optional[PackWorkflow]:
        for workflow in self.workflows:
            if workflow.objective_match == objective_id:
                return workflow
        return None

    def get_objective_by_phrase(self, text: str) -> Optional[Objective]:
        text_lc = text.lower()
        for obj in self.objectives:
            for phrase in obj.user_phrases:
                if phrase.lower() in text_lc:
                    return obj
        return None
