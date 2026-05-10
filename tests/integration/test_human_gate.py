"""Human-gate denial test (NR-IT-RUN-002)."""

from __future__ import annotations

import pytest

from neuronium_agent.runtime.objective_runner import ObjectiveRunner


def test_human_gate_denial_aborts_run(tmp_path) -> None:
    runner = ObjectiveRunner(
        trace_dir=str(tmp_path),
        auto_approve=False,
    )
    # Provide a non-interactive input that always denies.
    import builtins

    real_input = builtins.input

    def fake_input(prompt: str = "") -> str:
        return "n"

    builtins.input = fake_input
    try:
        with pytest.raises(PermissionError):
            runner.run("Fix failing tests", pack_id="coding")
    finally:
        builtins.input = real_input


def test_session_override_can_deny_tool() -> None:
    from neuronium_agent.tools.governance import PermissionDecision, PolicyEngine

    engine = PolicyEngine()
    engine.set_session("shell.run", PermissionDecision.DENY)
    assert engine.resolve("shell.run") == PermissionDecision.DENY
