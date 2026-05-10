"""End-to-end tests through the CLI."""

from __future__ import annotations

import json
import os
from pathlib import Path

from click.testing import CliRunner

from neuronium_agent.cli.main import cli


def test_cli_packs_list() -> None:
    runner = CliRunner()
    result = runner.invoke(cli, ["packs", "list"])
    assert result.exit_code == 0
    assert "coding" in result.output
    assert "marketing" in result.output
    assert "hr" in result.output


def test_cli_packs_validate_path(tmp_path: Path) -> None:
    runner = CliRunner()
    builtin_path = Path("neuronium_agent/packs/builtin/coding.yaml").resolve()
    result = runner.invoke(cli, ["packs", "validate", str(builtin_path)])
    assert result.exit_code == 0


def test_cli_packs_validate_id() -> None:
    runner = CliRunner()
    result = runner.invoke(cli, ["packs", "validate", "coding"])
    assert result.exit_code == 0


def test_cli_packs_init_scaffold(tmp_path: Path) -> None:
    runner = CliRunner()
    with runner.isolated_filesystem(temp_dir=str(tmp_path)):
        result = runner.invoke(cli, ["packs", "init", "myc"])
        assert result.exit_code == 0
        assert os.path.exists("./packs/myc.yaml")


def test_cli_packs_generate(tmp_path: Path) -> None:
    template = tmp_path / "tpl.md"
    template.write_text(
        "# Workflow Pack: TestGen\n\n## 1. Domain\nTesting.\n\n## 2. What should the user be able to ask?\n- do something\n\n## 3. What outcomes should the system produce?\n- result\n\n## 4. What agents are needed?\n```text\nName: Worker\nRole: executor\nDoes: do work\nTools:\nOutput: result\n```\n\n## 5. What tools are needed?\n- doc.write\n\n## 6. What actions are risky?\n- publish\n\n## 7. When should a human approve?\n- before publish\n\n## 8. What memory / context is needed?\n- prior runs\n\n## 9. What quality checks are needed?\n- result not empty\n\n## 10. What should the final output look like?\n- report\n"
    )
    out = tmp_path / "pack.yaml"
    runner = CliRunner()
    result = runner.invoke(
        cli,
        ["packs", "generate", str(template), "--out", str(out), "--id", "testgen"],
    )
    assert result.exit_code == 0
    assert out.exists()
    # validate it
    result = runner.invoke(cli, ["packs", "validate", str(out)])
    assert result.exit_code == 0


def test_cli_objective_run_coding_mock(tmp_path: Path) -> None:
    runner = CliRunner()
    trace_dir = tmp_path / "traces"
    result = runner.invoke(
        cli,
        [
            "objective",
            "run",
            "Fix failing tests",
            "--pack",
            "coding",
            "--mock",
            "--trace-dir",
            str(trace_dir),
            "--json",
        ],
    )
    assert result.exit_code == 0, result.output
    data = json.loads(result.output)
    assert data["status"] == "succeeded"
    assert data["pack_id"] == "coding"
    assert "n_final" in data["visited"]


def test_cli_code_command(tmp_path: Path) -> None:
    runner = CliRunner()
    trace_dir = tmp_path / "traces"
    result = runner.invoke(
        cli,
        ["code", "Fix failing tests", "--trace-dir", str(trace_dir)],
    )
    assert result.exit_code == 0
    assert "succeeded" in result.output


def test_cli_packs_test_coding() -> None:
    runner = CliRunner()
    result = runner.invoke(cli, ["packs", "test", "coding"])
    # Coding pack has 2 tests; both should pass in mock mode.
    assert result.exit_code == 0, result.output


def test_cli_doctor() -> None:
    runner = CliRunner()
    result = runner.invoke(cli, ["doctor"])
    assert result.exit_code == 0
    assert "version" in result.output
