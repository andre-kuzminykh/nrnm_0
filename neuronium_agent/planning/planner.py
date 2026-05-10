"""HTN planner: recursively decomposes a root task using declared methods."""

from __future__ import annotations

from typing import Any, Callable, Dict, List, Optional

from neuronium_agent.planning.errors import PlanningError
from neuronium_agent.planning.models import (
    HTNMethod,
    HTNTask,
    HierarchicalPlan,
    PlanNode,
    TaskKind,
)


def _safe_eval(expr: str, state: Dict[str, Any]) -> bool:
    if not expr or expr.strip() == "true":
        return True
    if expr.strip() == "false":
        return False
    try:
        return bool(eval(expr, {"__builtins__": {}}, dict(state)))
    except Exception:  # noqa: BLE001
        return False


class HTNPlanner:
    """Builds a hierarchical plan from a task registry."""

    MAX_DEPTH = 32

    def __init__(self, tasks: Dict[str, HTNTask]) -> None:
        self.tasks = dict(tasks)

    @classmethod
    def from_pack_tasks(cls, tasks: List[HTNTask]) -> "HTNPlanner":
        registry: Dict[str, HTNTask] = {}
        for task in tasks:
            if task.id in registry:
                raise PlanningError([f"duplicate HTN task id '{task.id}'"])
            registry[task.id] = task
        return cls(registry)

    def plan(self, root_task_id: str, state: Optional[Dict[str, Any]] = None) -> HierarchicalPlan:
        state = state or {}
        if root_task_id not in self.tasks:
            raise PlanningError([f"root task '{root_task_id}' not registered"])
        errors: List[str] = []
        method_choices: Dict[str, str] = {}

        def _expand(task_id: str, task_path: List[str], depth: int) -> PlanNode:
            if depth > self.MAX_DEPTH:
                errors.append(f"max decomposition depth exceeded at '{task_id}'")
                return PlanNode(task_id=task_id, kind=TaskKind.PRIMITIVE, task_path=task_path)
            if task_id in task_path:
                errors.append(
                    f"cycle detected: '{task_id}' is already in path {task_path}"
                )
                return PlanNode(task_id=task_id, kind=TaskKind.PRIMITIVE, task_path=task_path)
            if task_id not in self.tasks:
                errors.append(f"unknown task reference '{task_id}'")
                return PlanNode(task_id=task_id, kind=TaskKind.PRIMITIVE, task_path=task_path)
            task = self.tasks[task_id]
            new_path = task_path + [task_id]
            if task.kind == TaskKind.PRIMITIVE:
                return PlanNode(
                    task_id=task.id,
                    kind=TaskKind.PRIMITIVE,
                    phase_id=task.phase_id,
                    task_path=new_path,
                )
            # Compound: pick a method.
            chosen: Optional[HTNMethod] = None
            for method in task.methods:
                if _safe_eval(method.applies_when, state):
                    chosen = method
                    break
            if chosen is None:
                errors.append(
                    f"no applicable method for compound task '{task.id}'"
                )
                return PlanNode(task_id=task.id, kind=TaskKind.COMPOUND, task_path=new_path)
            method_choices[task.id] = chosen.id
            children = [_expand(sub, new_path, depth + 1) for sub in chosen.subtasks]
            return PlanNode(
                task_id=task.id,
                kind=TaskKind.COMPOUND,
                method_id=chosen.id,
                task_path=new_path,
                children=children,
            )

        root = _expand(root_task_id, [], 0)
        if errors:
            raise PlanningError(errors)
        leaves = _collect_leaves(root)
        if not leaves:
            raise PlanningError([f"plan rooted at '{root_task_id}' has no primitive leaves"])
        return HierarchicalPlan(root=root, leaves=leaves, method_choices=method_choices)


def _collect_leaves(node: PlanNode) -> List[PlanNode]:
    if node.kind == TaskKind.PRIMITIVE:
        return [node]
    out: List[PlanNode] = []
    for child in node.children:
        out.extend(_collect_leaves(child))
    return out


def build_implicit_plan_from_phases(
    workflow_id: str, phase_ids: List[str]
) -> HierarchicalPlan:
    """Fallback: build a depth-1 plan from a flat list of phase ids.

    Used when a pack does not declare HTN tasks; preserves backward compat with
    the existing workflow → phases flow.
    """
    children: List[PlanNode] = []
    for phase_id in phase_ids:
        children.append(
            PlanNode(
                task_id=f"phase.{phase_id}",
                kind=TaskKind.PRIMITIVE,
                phase_id=phase_id,
                task_path=[workflow_id, f"phase.{phase_id}"],
            )
        )
    root = PlanNode(
        task_id=workflow_id,
        kind=TaskKind.COMPOUND,
        method_id="implicit_sequence",
        task_path=[workflow_id],
        children=children,
    )
    return HierarchicalPlan(
        root=root,
        leaves=list(children),
        method_choices={workflow_id: "implicit_sequence"},
    )
