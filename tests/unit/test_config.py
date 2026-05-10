"""Config hierarchy tests."""

from __future__ import annotations

import os
from pathlib import Path

from neuronium_agent.config import resolve_config


def test_builtin_defaults_present() -> None:
    cfg = resolve_config(project_root="/tmp/no-such-project")
    assert cfg.model_aliases["fast"] == "mock"


def test_project_overrides_global(tmp_path, monkeypatch) -> None:
    fake_home = tmp_path / "home"
    fake_home.mkdir()
    monkeypatch.setenv("HOME", str(fake_home))
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    (fake_home / ".neuronium").mkdir()
    (fake_home / ".neuronium" / "config.yaml").write_text(
        "model_aliases:\n  fast: provider-global\n"
    )
    project = tmp_path / "project"
    (project / ".neuronium").mkdir(parents=True)
    (project / ".neuronium" / "config.yaml").write_text(
        "model_aliases:\n  fast: provider-project\n"
    )
    cfg = resolve_config(project_root=str(project))
    assert cfg.model_aliases["fast"] == "provider-project"


def test_local_overrides_project(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("HOME", str(tmp_path / "home"))
    project = tmp_path / "p"
    (project / ".neuronium").mkdir(parents=True)
    (project / ".neuronium" / "config.yaml").write_text(
        "model_aliases:\n  fast: project\n"
    )
    (project / ".neuronium" / "config.local.yaml").write_text(
        "model_aliases:\n  fast: local\n"
    )
    cfg = resolve_config(project_root=str(project))
    assert cfg.model_aliases["fast"] == "local"


def test_env_overrides_local(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("HOME", str(tmp_path / "home"))
    project = tmp_path / "p"
    (project / ".neuronium").mkdir(parents=True)
    (project / ".neuronium" / "config.local.yaml").write_text("mock: false\n")
    monkeypatch.setenv("NEURONIUM_MOCK", "true")
    cfg = resolve_config(project_root=str(project))
    assert cfg.mock is True


def test_cli_overrides_env(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("HOME", str(tmp_path / "home"))
    monkeypatch.setenv("NEURONIUM_MOCK", "true")
    cfg = resolve_config(project_root=str(tmp_path), cli_overrides={"mock": False})
    assert cfg.mock is False


def test_session_overrides_cli(tmp_path) -> None:
    cfg = resolve_config(
        project_root=str(tmp_path),
        cli_overrides={"mock": True},
        session_overrides={"mock": False},
    )
    assert cfg.mock is False
