"""Register real (non-mock) tool implementations onto a ToolRegistry."""

from __future__ import annotations

from pathlib import Path
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field

from neuronium_agent.tools.builtin.fs import RealFsTools
from neuronium_agent.tools.builtin.shell import RealShellTool
from neuronium_agent.tools.registry import ToolRegistry


class RealToolsConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")
    cwd: str
    allowed_roots: List[str] = Field(default_factory=list)
    timeout_s: int = 30
    max_output_bytes: int = 64 * 1024
    max_file_bytes: int = 1024 * 1024
    allow_destructive: bool = False


def register_real_tools(
    registry: ToolRegistry,
    config: Optional[RealToolsConfig] = None,
) -> RealToolsConfig:
    """Register real shell + fs tools under the same `<server>.<tool>` refs the
    mock registry uses, so packs and policies do not need to change.

    Defaults to `cwd = $HOME` and `allowed_roots = [$HOME]` when no config is
    given — but those defaults are intentionally conservative; production
    harnesses should pass their own scoped config.
    """
    if config is None:
        cwd = str(Path.home())
        config = RealToolsConfig(cwd=cwd, allowed_roots=[cwd])
    if not config.allowed_roots:
        config = config.model_copy(update={"allowed_roots": [config.cwd]})
    shell = RealShellTool(
        cwd=config.cwd,
        timeout_s=config.timeout_s,
        max_output_bytes=config.max_output_bytes,
        allow_destructive=config.allow_destructive,
    )
    fs = RealFsTools(
        allowed_roots=config.allowed_roots,
        max_file_bytes=config.max_file_bytes,
    )
    registry.register(
        "shell.run",
        shell.run,
        kind="builtin",
        risk="critical",
        description="Run a shell command (subprocess) with timeout, denylist and output cap.",
        input_schema={
            "type": "object",
            "properties": {"command": {"type": "string"}},
            "required": ["command"],
        },
    )
    registry.register(
        "fs.read",
        fs.read,
        kind="builtin",
        risk="low",
        description="Read text files from the sandbox.",
        input_schema={
            "type": "object",
            "properties": {
                "path": {"type": "string"},
                "paths": {"type": "array", "items": {"type": "string"}},
            },
        },
    )
    registry.register(
        "fs.write",
        fs.write,
        kind="builtin",
        risk="high",
        description="Write text content to a file in the sandbox.",
        input_schema={
            "type": "object",
            "properties": {"path": {"type": "string"}, "content": {"type": "string"}},
            "required": ["path", "content"],
        },
    )
    registry.register(
        "fs.edit",
        fs.edit,
        kind="builtin",
        risk="high",
        description="Replace `old` with `new` in a file (single occurrence).",
        input_schema={
            "type": "object",
            "properties": {
                "path": {"type": "string"},
                "old": {"type": "string"},
                "new": {"type": "string"},
            },
            "required": ["path", "old", "new"],
        },
    )
    registry.register(
        "patch.apply",
        fs.patch_apply,
        kind="builtin",
        risk="high",
        description="Apply a unified diff to files in the sandbox.",
        input_schema={
            "type": "object",
            "properties": {"patch": {"type": "string"}},
            "required": ["patch"],
        },
    )
    registry.register(
        "glob.search",
        fs.glob_search,
        kind="builtin",
        risk="low",
        description="Glob match within the sandbox.",
        input_schema={
            "type": "object",
            "properties": {"pattern": {"type": "string"}, "root": {"type": "string"}},
            "required": ["pattern"],
        },
    )
    registry.register(
        "grep.search",
        fs.grep_search,
        kind="builtin",
        risk="low",
        description="Regex line search within the sandbox.",
        input_schema={
            "type": "object",
            "properties": {"pattern": {"type": "string"}, "root": {"type": "string"}},
            "required": ["pattern"],
        },
    )
    registry.register(
        "git.status",
        fs.git_status,
        kind="builtin",
        risk="low",
        description="Read-only git status --porcelain.",
        input_schema={"type": "object", "properties": {}},
    )
    registry.register(
        "git.diff",
        fs.git_diff,
        kind="builtin",
        risk="low",
        description="Read-only git diff.",
        input_schema={"type": "object", "properties": {}},
    )
    return config
