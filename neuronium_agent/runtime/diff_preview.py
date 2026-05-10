"""Render a unified diff for a proposed file edit before approval."""

from __future__ import annotations

import difflib
import os
from pathlib import Path
from typing import Optional


def render_edit_diff(path: str, old: str, new: str, *, context: int = 3) -> str:
    """Diff between current file content and the post-edit content.

    Returns a unified-diff string suitable for printing to the operator before
    approval. When `path` does not exist on disk the diff is computed from the
    empty string.
    """
    p = Path(os.path.expanduser(path))
    before = ""
    if p.is_file():
        try:
            before = p.read_text(encoding="utf-8", errors="replace")
        except Exception:  # noqa: BLE001
            before = ""
    if old not in before:
        return "(no changes)"
    after = before.replace(old, new, 1)
    diff = "".join(
        difflib.unified_diff(
            before.splitlines(keepends=True),
            after.splitlines(keepends=True),
            fromfile=str(p),
            tofile=str(p),
            n=context,
        )
    )
    return diff or "(no changes)"


def render_patch_diff(patch: str) -> str:
    """Pretty-print a unified diff blob (truncates very large patches)."""
    if not patch:
        return "(empty patch)"
    if len(patch) > 16 * 1024:
        head = patch[: 16 * 1024]
        return head + "\n... (truncated) ..."
    return patch


def render_write_preview(path: str, content: str, *, max_chars: int = 4000) -> str:
    """Show what the file will become; truncates content for display."""
    p = Path(os.path.expanduser(path))
    exists = p.is_file()
    body = content if len(content) <= max_chars else content[:max_chars] + "\n... (truncated) ..."
    header = f"# {'overwrite' if exists else 'create'}: {p}\n"
    return header + body
