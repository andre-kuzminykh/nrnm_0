"""Hierarchical Task Network (HTN) planning.

Neuronium's planner expands a root *compound* task into a tree of *primitive*
tasks using *methods* declared in a workflow pack. The resulting
`HierarchicalPlan` feeds the IR compiler, which preserves the hierarchy as
`task_path` metadata on each emitted node.

If a pack does not declare HTN tasks, the planner builds an implicit one-level
plan from `workflow.phases` so all existing packs keep working unchanged.
"""

from neuronium_agent.planning.errors import PlanningError
from neuronium_agent.planning.models import (
    HTNMethod,
    HTNTask,
    HierarchicalPlan,
    PlanNode,
    TaskKind,
)
from neuronium_agent.planning.planner import HTNPlanner

__all__ = [
    "HTNMethod",
    "HTNPlanner",
    "HTNTask",
    "HierarchicalPlan",
    "PlanNode",
    "PlanningError",
    "TaskKind",
]
