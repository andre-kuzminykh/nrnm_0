"""CLI tests for `neuronium-agent memory ...` subcommands."""

from __future__ import annotations

import json
from pathlib import Path

from click.testing import CliRunner

from neuronium_agent.cli.main import cli


# NR-E2E-MEM-001
def test_memory_backends_lists_defaults() -> None:
    runner = CliRunner()
    result = runner.invoke(cli, ["memory", "backends"])
    assert result.exit_code == 0
    assert "mock" in result.output
    assert "raganything" in result.output


def test_memory_diagnostics_mock() -> None:
    runner = CliRunner()
    result = runner.invoke(cli, ["memory", "diagnostics", "--backend", "mock"])
    assert result.exit_code == 0
    payload = json.loads(result.output)
    assert payload["backend"] == "mock"
    assert payload["ready"] is True


def test_memory_diagnostics_raganything_reports_install_state() -> None:
    runner = CliRunner()
    result = runner.invoke(cli, ["memory", "diagnostics", "--backend", "raganything"])
    assert result.exit_code == 0
    payload = json.loads(result.output)
    assert payload["backend"] == "raganything"
    # In CI raganything is not installed; ready is False.
    assert payload["ready"] is False
    assert payload["raganything_installed"] is False


# NR-E2E-MEM-002
def test_memory_ingest_and_query_roundtrip(tmp_path: Path) -> None:
    file_path = tmp_path / "doc.txt"
    file_path.write_text("Neuronium is a Super Agent Platform with packs.")
    runner = CliRunner()
    ingest = runner.invoke(
        cli,
        ["memory", "ingest", str(file_path), "--backend", "mock", "--pack", "coding"],
    )
    # `memory ingest` produces JSON diagnostics; for mock backend this only
    # validates the CLI surface — the in-process index is per-invocation.
    assert ingest.exit_code == 0
    payload = json.loads(ingest.output)
    assert payload["total_documents"] == 1
    query = runner.invoke(
        cli,
        ["memory", "query", "calculator", "--backend", "mock", "--pack", "coding"],
    )
    assert query.exit_code == 0
    qpayload = json.loads(query.output)
    assert qpayload["backend"] == "mock"


def test_objective_run_accepts_memory_flags(tmp_path: Path) -> None:
    runner = CliRunner()
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
            str(tmp_path / "traces"),
            "--memory-backend",
            "mock",
            "--json",
        ],
    )
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert data["status"] == "succeeded"


def test_doctor_reports_raganything_status() -> None:
    runner = CliRunner()
    result = runner.invoke(cli, ["doctor"])
    assert result.exit_code == 0
    assert "raganything" in result.output
