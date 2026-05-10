"""HTN planning models."""

from __future__ import annotations

from enum import Enum
from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field


class TaskKind(str, Enum):
    COMPOUND = "compound"
    PRIMITIVE = "primitive"


class HTNMethod(BaseModel):
    """An ordered decomposition of a compound task into subtasks.

    The planner picks the first method whose `applies_when` predicate evaluates
    truthy against the current state. A method whose `applies_when` is omitted
    (or `"true"`) always applies.
    """

    model_config = ConfigDict(extra="forbid")
    id: str
    applies_when: str = "true"
    subtasks: List[str] = Field(default_factory=list)


class HTNTask(BaseModel):
    """A compound or primitive HTN task.

    - Compound tasks own a list of `methods` and must decompose.
    - Primitive tasks reference a workflow phase by `phase_id` and emit one IR
      node.
    """

    model_config = ConfigDict(extra="forbid")
    id: str
    kind: TaskKind
    description: str = ""
    phase_id: Optional[str] = None
    methods: List[HTNMethod] = Field(default_factory=list)


class PlanNode(BaseModel):
    """Concrete node in a hierarchical plan tree."""

    model_config = ConfigDict(extra="forbid")
    task_id: str
    kind: TaskKind
    method_id: Optional[str] = None
    phase_id: Optional[str] = None
    task_path: List[str] = Field(default_factory=list)
    children: List["PlanNode"] = Field(default_factory=list)

    @property
    def is_primitive(self) -> bool:
        return self.kind == TaskKind.PRIMITIVE


PlanNode.model_rebuild()


class HierarchicalPlan(BaseModel):
    """A fully decomposed plan rooted at a single compound task.

    `leaves` is the depth-first preorder traversal of all primitive nodes,
    matching the execution order the IR compiler relies on.
    """

    model_config = ConfigDict(extra="forbid")
    root: PlanNode
    leaves: List[PlanNode] = Field(default_factory=list)
    method_choices: Dict[str, str] = Field(default_factory=dict)

    def depth(self) -> int:
        def _walk(node: PlanNode) -> int:
            if not node.children:
                return 1
            return 1 + max(_walk(c) for c in node.children)

        return _walk(self.root)

    def find_ancestor_subplan(self, task_id: str) -> Optional[PlanNode]:
        """Return the closest compound ancestor for the given task id."""
        def _walk(node: PlanNode, ancestor: Optional[PlanNode]) -> Optional[PlanNode]:
            if node.task_id == task_id:
                return ancestor if ancestor is not None else node
            for child in node.children:
                found = _walk(child, node if node.kind == TaskKind.COMPOUND else ancestor)
                if found is not None:
                    return found
            return None

        return _walk(self.root, None)
