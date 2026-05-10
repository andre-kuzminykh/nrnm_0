"""Unit tests for the HTN planner."""

from __future__ import annotations

import pytest

from neuronium_agent.planning import (
    HTNMethod,
    HTNPlanner,
    HTNTask,
    HierarchicalPlan,
    PlanNode,
    PlanningError,
    TaskKind,
)
from neuronium_agent.planning.planner import build_implicit_plan_from_phases


def _make_tasks(*tasks: HTNTask) -> dict[str, HTNTask]:
    return {t.id: t for t in tasks}


# NR-UT-PLAN-001
def test_planner_expands_compound_into_primitives() -> None:
    tasks = _make_tasks(
        HTNTask(
            id="root",
            kind=TaskKind.COMPOUND,
            methods=[HTNMethod(id="m1", subtasks=["a", "b"])],
        ),
        HTNTask(id="a", kind=TaskKind.PRIMITIVE, phase_id="phase_a"),
        HTNTask(id="b", kind=TaskKind.PRIMITIVE, phase_id="phase_b"),
    )
    plan = HTNPlanner(tasks).plan("root")
    assert plan.depth() == 2
    assert [leaf.task_id for leaf in plan.leaves] == ["a", "b"]
    assert plan.method_choices["root"] == "m1"


# NR-UT-PLAN-002
def test_planner_recursive_decomposition() -> None:
    tasks = _make_tasks(
        HTNTask(
            id="root",
            kind=TaskKind.COMPOUND,
            methods=[HTNMethod(id="m", subtasks=["mid", "c"])],
        ),
        HTNTask(
            id="mid",
            kind=TaskKind.COMPOUND,
            methods=[HTNMethod(id="m", subtasks=["a", "b"])],
        ),
        HTNTask(id="a", kind=TaskKind.PRIMITIVE, phase_id="p_a"),
        HTNTask(id="b", kind=TaskKind.PRIMITIVE, phase_id="p_b"),
        HTNTask(id="c", kind=TaskKind.PRIMITIVE, phase_id="p_c"),
    )
    plan = HTNPlanner(tasks).plan("root")
    assert plan.depth() == 3
    assert [leaf.task_id for leaf in plan.leaves] == ["a", "b", "c"]


# NR-UT-PLAN-003
def test_planner_picks_first_applicable_method() -> None:
    tasks = _make_tasks(
        HTNTask(
            id="root",
            kind=TaskKind.COMPOUND,
            methods=[
                HTNMethod(id="never", applies_when="False", subtasks=["a"]),
                HTNMethod(id="sometimes", applies_when="needs_test", subtasks=["a", "b"]),
                HTNMethod(id="fallback", subtasks=["a"]),
            ],
        ),
        HTNTask(id="a", kind=TaskKind.PRIMITIVE, phase_id="p_a"),
        HTNTask(id="b", kind=TaskKind.PRIMITIVE, phase_id="p_b"),
    )
    plan = HTNPlanner(tasks).plan("root", state={"needs_test": True})
    assert plan.method_choices["root"] == "sometimes"
    plan2 = HTNPlanner(tasks).plan("root", state={"needs_test": False})
    assert plan2.method_choices["root"] == "fallback"


# NR-UT-PLAN-004
def test_planner_detects_cycle() -> None:
    tasks = _make_tasks(
        HTNTask(
            id="a",
            kind=TaskKind.COMPOUND,
            methods=[HTNMethod(id="m", subtasks=["b"])],
        ),
        HTNTask(
            id="b",
            kind=TaskKind.COMPOUND,
            methods=[HTNMethod(id="m", subtasks=["a"])],
        ),
    )
    with pytest.raises(PlanningError):
        HTNPlanner(tasks).plan("a")


def test_planner_rejects_unknown_root() -> None:
    with pytest.raises(PlanningError):
        HTNPlanner({}).plan("missing")


def test_planner_errors_when_no_applicable_method() -> None:
    tasks = _make_tasks(
        HTNTask(
            id="root",
            kind=TaskKind.COMPOUND,
            methods=[HTNMethod(id="m", applies_when="False", subtasks=["a"])],
        ),
        HTNTask(id="a", kind=TaskKind.PRIMITIVE, phase_id="p_a"),
    )
    with pytest.raises(PlanningError):
        HTNPlanner(tasks).plan("root")


def test_planner_errors_when_primitive_used_as_root_without_decomposition() -> None:
    tasks = _make_tasks(
        HTNTask(id="p", kind=TaskKind.PRIMITIVE, phase_id="x"),
    )
    plan = HTNPlanner(tasks).plan("p")
    assert plan.leaves[0].task_id == "p"
    assert plan.depth() == 1


def test_task_path_records_ancestors() -> None:
    tasks = _make_tasks(
        HTNTask(
            id="root",
            kind=TaskKind.COMPOUND,
            methods=[HTNMethod(id="m", subtasks=["mid"])],
        ),
        HTNTask(
            id="mid",
            kind=TaskKind.COMPOUND,
            methods=[HTNMethod(id="m", subtasks=["leaf"])],
        ),
        HTNTask(id="leaf", kind=TaskKind.PRIMITIVE, phase_id="px"),
    )
    plan = HTNPlanner(tasks).plan("root")
    assert plan.leaves[0].task_path == ["root", "mid", "leaf"]


def test_find_ancestor_subplan() -> None:
    plan = HierarchicalPlan(
        root=PlanNode(
            task_id="root",
            kind=TaskKind.COMPOUND,
            task_path=["root"],
            children=[
                PlanNode(
                    task_id="mid",
                    kind=TaskKind.COMPOUND,
                    task_path=["root", "mid"],
                    children=[
                        PlanNode(
                            task_id="leaf",
                            kind=TaskKind.PRIMITIVE,
                            task_path=["root", "mid", "leaf"],
                        )
                    ],
                )
            ],
        ),
    )
    found = plan.find_ancestor_subplan("leaf")
    assert found is not None
    assert found.task_id == "mid"


# NR-UT-PLAN-005
def test_implicit_plan_from_phases() -> None:
    plan = build_implicit_plan_from_phases("wf", ["a", "b", "c"])
    assert plan.depth() == 2
    assert [leaf.phase_id for leaf in plan.leaves] == ["a", "b", "c"]
    assert plan.method_choices["wf"] == "implicit_sequence"
