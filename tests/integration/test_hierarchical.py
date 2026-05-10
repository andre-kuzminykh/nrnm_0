"""Integration tests for hierarchical planning in the runtime."""

from __future__ import annotations

from pathlib import Path
from typing import Dict, List

from neuronium_agent import run_objective
from neuronium_agent.packs.registry import PackRegistry


def _events_of(result, kinds) -> List[dict]:
    return [e for e in result.events if e["kind"] in kinds]


# NR-IT-PLAN-001
def test_coding_pack_emits_plan_decomposed(tmp_path: Path) -> None:
    result = run_objective(
        "Fix failing tests in this repository",
        pack="coding",
        mock=True,
        trace_dir=str(tmp_path / "traces"),
    )
    plan_events = _events_of(result, {"plan.decomposed"})
    assert len(plan_events) == 1
    payload = plan_events[0]["payload"]
    assert payload["htn"] is True
    assert payload["root"] == "fix_bug_root"
    assert payload["depth"] >= 3
    assert payload["leaves"] == [
        "task_plan",
        "task_research",
        "task_edit",
        "task_test",
        "task_review",
    ]
    assert payload["method_choices"]["fix_bug_root"] == "standard"


# NR-IT-PLAN-002
def test_subplan_entered_completed_pair_balances(tmp_path: Path) -> None:
    result = run_objective(
        "Fix failing tests",
        pack="coding",
        mock=True,
        trace_dir=str(tmp_path / "traces"),
    )
    opens = [e for e in result.events if e["kind"] == "subplan.entered"]
    closes = [e for e in result.events if e["kind"] == "subplan.completed"]
    assert len(opens) == len(closes), "subplan.entered/completed must be balanced"
    # The first subplan opened (root) must be the last one closed.
    assert opens[0]["payload"]["subplan"] == "fix_bug_root"
    assert closes[-1]["payload"]["subplan"] == "fix_bug_root"


# NR-IT-PLAN-003
def test_hierarchical_replan_narrows_scope(tmp_path: Path) -> None:
    result = run_objective(
        "Fix failing tests",
        pack="coding",
        mock=True,
        trace_dir=str(tmp_path / "traces"),
        force_failure_first=True,
    )
    failures = [e for e in result.events if e["kind"] == "subplan.failed"]
    replans = [e for e in result.events if e["kind"] == "replan.completed"]
    assert failures and replans
    # The smarter scope selection should target a sibling subplan, not the root.
    assert replans[0]["payload"]["subplan"] != "fix_bug_root"
    assert replans[0]["payload"]["scope"] == "subplan"
    assert result.run.status.value == "succeeded"
    assert result.replans == 1


# NR-IT-PLAN-004
def test_task_path_recorded_on_ir_nodes() -> None:
    compiled = PackRegistry().get_compiled("coding")
    program = compiled.ir_templates["fix_bug"]
    for node in program.nodes:
        if node.id == "n_final":
            continue
        if node.id.endswith("_gate"):
            # Approval gate inherits the parent task path.
            assert node.task_path, f"approval gate {node.id} missing task_path"
            continue
        assert node.task_path, f"{node.id} missing task_path"
        assert node.task_path[0] == "fix_bug_root"


# NR-IT-PLAN-005
def test_marketing_pack_falls_back_to_implicit_plan(tmp_path: Path) -> None:
    result = run_objective(
        "Create a marketing campaign for launch",
        pack="marketing",
        mock=True,
        trace_dir=str(tmp_path / "traces"),
    )
    plan = _events_of(result, {"plan.decomposed"})[0]["payload"]
    assert plan["htn"] is False
    # Implicit plan keeps depth=2 with the workflow id as root.
    assert plan["depth"] == 2
    assert plan["method_choices"][plan["root"]] == "implicit_sequence"
