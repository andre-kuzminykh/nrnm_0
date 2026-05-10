"""Integration tests for the Objective Runner."""

from __future__ import annotations

from pathlib import Path

from neuronium_agent import run_objective


def test_coding_run_succeeds_in_mock_mode(tmp_path: Path) -> None:
    result = run_objective(
        "Fix failing tests in this repository",
        pack="coding",
        mock=True,
        trace_dir=str(tmp_path / "traces"),
    )
    assert result.run.status.value == "succeeded"
    assert result.replans == 0
    assert result.final_state.get("verdict") == "PASS"
    assert result.final_report.startswith("# Final Outcome")
    assert (tmp_path / "traces").exists()


def test_coding_run_recovers_via_replan(tmp_path: Path) -> None:
    result = run_objective(
        "Fix failing tests",
        pack="coding",
        mock=True,
        trace_dir=str(tmp_path / "traces"),
        force_failure_first=True,
    )
    assert result.run.status.value == "succeeded"
    assert result.replans == 1
    assert result.final_state.get("verdict") == "PASS"


def test_marketing_run_succeeds(tmp_path: Path) -> None:
    result = run_objective(
        "Create a marketing campaign for our launch",
        pack="marketing",
        mock=True,
        trace_dir=str(tmp_path / "traces"),
    )
    assert result.run.status.value == "succeeded"
    assert "campaign_plan" in result.final_state


def test_hr_run_succeeds(tmp_path: Path) -> None:
    result = run_objective(
        "Screen candidates for a senior backend role",
        pack="hr",
        mock=True,
        trace_dir=str(tmp_path / "traces"),
    )
    assert result.run.status.value == "succeeded"
    assert "shortlist" in result.final_state


def test_agent_events_recorded(tmp_path: Path) -> None:
    result = run_objective(
        "Fix failing tests",
        pack="coding",
        mock=True,
        trace_dir=str(tmp_path / "traces"),
    )
    kinds = [e["kind"] for e in result.events]
    assert "agent.created" in kinds
    assert "agent.started" in kinds
    assert "agent.completed" in kinds
    assert "pack.selected" in kinds
    assert "pack.compiled" in kinds
    assert "ir.built" in kinds
    assert "outcome.produced" in kinds


def test_objective_can_be_inferred_from_text(tmp_path: Path) -> None:
    result = run_objective(
        "Please fix this bug in my repo",
        pack=None,
        mock=True,
        trace_dir=str(tmp_path / "traces"),
    )
    assert result.run.pack_id == "coding"


def test_trace_file_contains_redacted_secrets(tmp_path: Path) -> None:
    import json

    # Simulate a secret arriving via input.
    result = run_objective(
        "Fix the bug",
        pack="coding",
        mock=True,
        trace_dir=str(tmp_path / "traces"),
        inputs={"api_key": "sk-do-not-leak-12345"},
    )
    trace_text = Path(result.run.trace_path).read_text()
    assert "sk-do-not-leak-12345" not in trace_text
    assert "REDACTED" in trace_text
