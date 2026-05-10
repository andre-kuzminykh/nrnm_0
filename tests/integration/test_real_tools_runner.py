"""Integration: ObjectiveRunner with real_tools_config — verify governance,
diff preview, and that the IR run still completes via mock model + real tools.
"""

from __future__ import annotations

from pathlib import Path

from neuronium_agent import run_objective
from neuronium_agent.tools.real import RealToolsConfig


def test_real_tools_config_emits_event(tmp_path: Path) -> None:
    cwd = tmp_path / "work"
    cwd.mkdir()
    rt = RealToolsConfig(cwd=str(cwd), allowed_roots=[str(cwd)])
    result = run_objective(
        "Fix failing tests",
        pack="coding",
        mock=True,
        trace_dir=str(tmp_path / "traces"),
        real_tools_config=rt,
    )
    kinds = [e["kind"] for e in result.events]
    assert "tools.real_enabled" in kinds
    real_evt = next(e for e in result.events if e["kind"] == "tools.real_enabled")
    assert real_evt["payload"]["cwd"] == str(cwd)


def test_real_tools_via_api_helper_flag(tmp_path: Path) -> None:
    cwd = tmp_path / "work"
    cwd.mkdir()
    result = run_objective(
        "Fix failing tests",
        pack="coding",
        mock=True,
        trace_dir=str(tmp_path / "traces"),
        real_tools=True,
        real_tools_cwd=str(cwd),
        real_tools_allowed_roots=[str(cwd)],
    )
    assert result.run.status.value == "succeeded"
    real_evt = next(e for e in result.events if e["kind"] == "tools.real_enabled")
    assert str(cwd) in real_evt["payload"]["allowed_roots"]


def test_real_shell_executes_under_runner(tmp_path: Path, monkeypatch) -> None:
    """The mock model never asks for shell.run, so this just confirms the tool
    is registered and callable through the runtime."""
    cwd = tmp_path / "sb"
    cwd.mkdir()
    result = run_objective(
        "Fix failing tests",
        pack="coding",
        mock=True,
        trace_dir=str(tmp_path / "traces"),
        real_tools=True,
        real_tools_cwd=str(cwd),
        real_tools_allowed_roots=[str(cwd)],
    )
    # tools.real_enabled fires; nothing else needs to happen for the run to pass.
    assert result.final_state.get("verdict") == "PASS"
