"""Real shell.run implementation backed by `subprocess`.

Gated by:
- `is_destructive()` denylist (rm -rf, mkfs, fork bombs, ...).
- Per-call timeout (default 30s).
- Output-byte cap so a `cat /huge/file` cannot fill the run trace.
- `cwd` constrained to a single directory at construction time.
- Permission policy is still applied upstream by `PolicyEngine`; this class is
  the executor of last resort.
"""

from __future__ import annotations

import os
import shlex
import subprocess
from pathlib import Path
from typing import Any, Dict, List, Optional

from neuronium_agent.tools.builtin.safety import is_destructive


class RealShellTool:
    def __init__(
        self,
        cwd: str,
        *,
        timeout_s: int = 30,
        max_output_bytes: int = 64 * 1024,
        env: Optional[Dict[str, str]] = None,
        allow_destructive: bool = False,
    ) -> None:
        self.cwd = str(Path(os.path.expanduser(cwd)).resolve())
        if not Path(self.cwd).is_dir():
            raise ValueError(f"shell cwd is not a directory: {self.cwd}")
        self.timeout_s = timeout_s
        self.max_output_bytes = max_output_bytes
        self.env = env
        self.allow_destructive = allow_destructive

    def run(self, **kwargs: Any) -> Dict[str, Any]:
        command = kwargs.get("command")
        if command is None and "args" in kwargs:
            command = " ".join(shlex.quote(str(a)) for a in kwargs["args"] or [])
        if not command:
            return {"status": "error", "reason": "missing 'command'"}
        if not self.allow_destructive:
            reason = is_destructive(command)
            if reason is not None:
                return {
                    "status": "denied",
                    "reason": reason.value,
                    "command": command,
                }
        env = dict(os.environ)
        if self.env:
            env.update(self.env)
        try:
            result = subprocess.run(
                command,
                shell=True,
                cwd=self.cwd,
                env=env,
                capture_output=True,
                text=True,
                timeout=self.timeout_s,
            )
        except subprocess.TimeoutExpired:
            return {
                "status": "timeout",
                "command": command,
                "timeout_s": self.timeout_s,
            }
        except Exception as exc:  # noqa: BLE001
            return {"status": "error", "reason": str(exc), "command": command}
        stdout = (result.stdout or "")[: self.max_output_bytes]
        stderr = (result.stderr or "")[: self.max_output_bytes]
        truncated = len(result.stdout or "") > self.max_output_bytes or len(
            result.stderr or ""
        ) > self.max_output_bytes
        return {
            "status": "ok" if result.returncode == 0 else "error",
            "return_code": result.returncode,
            "stdout": stdout,
            "stderr": stderr,
            "truncated": truncated,
            "command": command,
        }
