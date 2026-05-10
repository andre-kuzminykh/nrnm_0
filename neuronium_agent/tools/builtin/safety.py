"""Safety primitives for real tools: denylist + safe path resolution."""

from __future__ import annotations

import os
import re
from enum import Enum
from pathlib import Path
from typing import List, Optional, Tuple


class DenyReason(str, Enum):
    DESTRUCTIVE = "destructive"
    OUTSIDE_ROOTS = "outside_allowed_roots"
    SYMLINK_ESCAPE = "symlink_escape"
    HIDDEN = "hidden_path"


# Patterns for shell commands that we refuse outright. Conservative — every
# entry is a clearly destructive or system-altering operation.
_DENY_PATTERNS: List[re.Pattern[str]] = [
    re.compile(r"(?:^|[\s;&|])rm\s+(-[a-zA-Z]*r[a-zA-Z]*f|--recursive\s+--force)\b"),
    re.compile(r"\bmkfs\b"),
    re.compile(r"(?:^|[\s;&|])dd\s+.*\bof=/dev/"),
    re.compile(r":\s*\(\s*\)\s*\{\s*:\s*\|\s*:\s*&\s*\}\s*;\s*:"),  # fork bomb
    re.compile(r"\b(shutdown|halt|reboot|poweroff)\b"),
    re.compile(r">\s*/dev/(sd|nvme|hd|disk|null)?[a-z0-9]*\b"),
    re.compile(r"\bchmod\s+(-R\s+)?[0-7]*[7-9]{3,}\s+/"),
    re.compile(r"\bchown\s+-R\s+\S+\s+/"),
    re.compile(r"(?:curl|wget)\s+[^|]*\|\s*(?:bash|sh|zsh|fish)"),
    re.compile(r"\beval\s+[\"\']?\$\("),
    re.compile(r"\bnc\s+-l"),
]


def is_destructive(command: str) -> Optional[DenyReason]:
    """Return a deny reason if the command matches a destructive pattern."""
    for pattern in _DENY_PATTERNS:
        if pattern.search(command):
            return DenyReason.DESTRUCTIVE
    return None


def safe_resolve(
    path: str,
    allowed_roots: List[str],
    *,
    must_exist: bool = False,
    allow_hidden: bool = True,
) -> Tuple[Optional[Path], Optional[DenyReason]]:
    """Resolve a path and ensure it lies under one of the allowed roots.

    Returns `(resolved_path, None)` on success or `(None, reason)` when the
    path escapes the allowed sandbox.
    """
    raw = Path(os.path.expanduser(str(path)))
    try:
        resolved = raw.resolve(strict=must_exist)
    except FileNotFoundError:
        # When must_exist=False, fall back to the absolute (un-canonicalized) path.
        resolved = raw.absolute()
    if not allow_hidden:
        for part in resolved.parts:
            if part.startswith("."):
                if part in {".", ".."}:
                    continue
                return None, DenyReason.HIDDEN
    if not allowed_roots:
        return resolved, None
    for root in allowed_roots:
        try:
            root_resolved = Path(os.path.expanduser(root)).resolve(strict=False)
        except Exception:  # noqa: BLE001
            continue
        try:
            resolved.relative_to(root_resolved)
            return resolved, None
        except ValueError:
            continue
    return None, DenyReason.OUTSIDE_ROOTS
