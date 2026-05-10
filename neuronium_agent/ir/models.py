"""Workflow IR pydantic models.

The IR is Neuronium's stable execution contract: any backend (LangGraph today,
others tomorrow) must consume the same shapes.
"""

from __future__ import annotations

from enum import Enum
from typing import Any, Callable, Dict, List, Literal, Optional, Union

from pydantic import BaseModel, ConfigDict, Field


class NodeKind(str, Enum):
    MODEL = "model"
    TOOL = "tool"
    OPERATOR = "operator"
    HUMAN_GATE = "human_gate"
    CRITIC = "critic"
    RECOVER = "recover"
    TERMINAL = "terminal"


class _NodeBase(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: str
    name: str
    description: Optional[str] = None
    task_path: List[str] = Field(default_factory=list)
    task_id: Optional[str] = None


class ModelNode(_NodeBase):
    kind: Literal[NodeKind.MODEL] = NodeKind.MODEL
    agent_ref: str
    prompt_ref: str
    inputs: List[str] = Field(default_factory=list)
    outputs: List[str] = Field(default_factory=list)


class ToolNode(_NodeBase):
    kind: Literal[NodeKind.TOOL] = NodeKind.TOOL
    agent_ref: str
    tool_ref: str
    args: Dict[str, Any] = Field(default_factory=dict)
    outputs: List[str] = Field(default_factory=list)


class OperatorNode(_NodeBase):
    kind: Literal[NodeKind.OPERATOR] = NodeKind.OPERATOR
    op: Literal["assign", "merge", "select", "format"]
    args: Dict[str, Any] = Field(default_factory=dict)
    outputs: List[str] = Field(default_factory=list)


class HumanGateNode(_NodeBase):
    kind: Literal[NodeKind.HUMAN_GATE] = NodeKind.HUMAN_GATE
    purpose: Literal["approval", "input", "review"] = "approval"
    message: str = "Continue?"


class CriticCheck(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: str
    condition: str
    on_fail: Literal["retry", "replan", "abort"] = "replan"


class CriticNode(_NodeBase):
    kind: Literal[NodeKind.CRITIC] = NodeKind.CRITIC
    agent_ref: str
    checks: List[CriticCheck] = Field(default_factory=list)
    outputs: List[str] = Field(default_factory=lambda: ["verdict"])


class RecoveryNode(_NodeBase):
    kind: Literal[NodeKind.RECOVER] = NodeKind.RECOVER
    strategy: Literal["retry", "replan", "abort"] = "retry"
    classification: str = "unknown"


class TerminalNode(_NodeBase):
    kind: Literal[NodeKind.TERMINAL] = NodeKind.TERMINAL
    outcome_template: Optional[str] = None


Node = Union[
    ModelNode,
    ToolNode,
    OperatorNode,
    HumanGateNode,
    CriticNode,
    RecoveryNode,
    TerminalNode,
]


class Edge(BaseModel):
    model_config = ConfigDict(extra="forbid")
    from_id: str
    to_id: str
    condition: Optional[str] = None
    label: Optional[str] = None


class AgentRef(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: str
    role: str
    pack_agent_id: Optional[str] = None


class Commitment(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: str
    statement: str
    required_evidence: List[str] = Field(default_factory=list)


class Program(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: str
    version: str = "0.1"
    pack_id: Optional[str] = None
    objective: str
    inputs: Dict[str, str] = Field(default_factory=dict)
    outputs: Dict[str, str] = Field(default_factory=dict)
    agents: List[AgentRef] = Field(default_factory=list)
    commitments: List[Commitment] = Field(default_factory=list)
    start: Optional[str] = None
    nodes: List[Node] = Field(default_factory=list)
    edges: List[Edge] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)

    def node_by_id(self, node_id: str) -> Optional[Node]:
        for node in self.nodes:
            if node.id == node_id:
                return node
        return None

    def outgoing(self, node_id: str) -> List[Edge]:
        return [e for e in self.edges if e.from_id == node_id]

    def incoming(self, node_id: str) -> List[Edge]:
        return [e for e in self.edges if e.to_id == node_id]


class CompiledGraph(BaseModel):
    """A compiled, runnable workflow.

    `run` is filled in by the compiler; we expose it as an attribute on the
    pydantic model. We allow arbitrary callables here.
    """

    model_config = ConfigDict(arbitrary_types_allowed=True)
    program: Program
    runner: Callable[..., Dict[str, Any]]

    def run(self, state: Dict[str, Any], runtime: Any) -> Dict[str, Any]:
        return self.runner(state, runtime)
