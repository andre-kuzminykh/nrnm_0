"""Resolve effective configuration from layered sources.

Resolution order (lowest to highest):
1. Built-in defaults
2. Global ~/.neuronium/config.yaml
3. Project <project>/.neuronium/config.yaml
4. Local <project>/.neuronium/config.local.yaml
5. Env vars NEURONIUM_*
6. CLI flags
7. Session overrides
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Dict, Optional

import yaml
from pydantic import BaseModel, ConfigDict, Field


_BUILTIN_DEFAULTS: Dict[str, Any] = {
    "mock": False,
    "auto_approve": False,
    "model_aliases": {
        "fast": "mock",
        "smart": "mock",
        "cheap": "mock",
        "critic": "mock",
    },
    "trace_dir": ".neuronium/traces",
}


class EffectiveConfig(BaseModel):
    model_config = ConfigDict(extra="allow")
    mock: bool = False
    auto_approve: bool = False
    model_aliases: Dict[str, str] = Field(default_factory=dict)
    trace_dir: str = ".neuronium/traces"
    sources: Dict[str, str] = Field(default_factory=dict)


def _read_yaml(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {}
    with open(path, "r", encoding="utf-8") as fh:
        data = yaml.safe_load(fh) or {}
    if not isinstance(data, dict):
        return {}
    return data


def _deep_update(base: Dict[str, Any], overlay: Dict[str, Any], source: str, sources: Dict[str, str]) -> None:
    for key, value in overlay.items():
        if isinstance(value, dict) and isinstance(base.get(key), dict):
            _deep_update(base[key], value, source, sources)
        else:
            base[key] = value
            sources[key] = source


def _env_overrides() -> Dict[str, Any]:
    out: Dict[str, Any] = {}
    for key, value in os.environ.items():
        if not key.startswith("NEURONIUM_"):
            continue
        norm = key[len("NEURONIUM_") :].lower()
        if value.lower() in {"true", "false"}:
            out[norm] = value.lower() == "true"
        else:
            out[norm] = value
    return out


def resolve_config(
    project_root: Optional[str] = None,
    cli_overrides: Optional[Dict[str, Any]] = None,
    session_overrides: Optional[Dict[str, Any]] = None,
) -> EffectiveConfig:
    root = Path(project_root) if project_root else Path.cwd()
    accumulated: Dict[str, Any] = {}
    sources: Dict[str, str] = {}
    _deep_update(accumulated, _BUILTIN_DEFAULTS, "builtin", sources)
    home_config = Path.home() / ".neuronium" / "config.yaml"
    _deep_update(accumulated, _read_yaml(home_config), "global", sources)
    project_config = root / ".neuronium" / "config.yaml"
    _deep_update(accumulated, _read_yaml(project_config), "project", sources)
    local_config = root / ".neuronium" / "config.local.yaml"
    _deep_update(accumulated, _read_yaml(local_config), "local", sources)
    _deep_update(accumulated, _env_overrides(), "env", sources)
    if cli_overrides:
        _deep_update(accumulated, cli_overrides, "cli", sources)
    if session_overrides:
        _deep_update(accumulated, session_overrides, "session", sources)
    accumulated["sources"] = sources
    return EffectiveConfig.model_validate(accumulated)
