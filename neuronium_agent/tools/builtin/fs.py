"""Real filesystem tools, sandboxed to a list of allowed roots.

`safe_resolve()` enforces every path lies under one of the allowed roots.
"""

from __future__ import annotations

import difflib
import os
import re
from pathlib import Path
from typing import Any, Dict, List, Optional

from neuronium_agent.tools.builtin.safety import safe_resolve


class RealFsTools:
    def __init__(
        self,
        allowed_roots: List[str],
        *,
        max_file_bytes: int = 1024 * 1024,
        max_glob_matches: int = 2000,
        max_grep_matches: int = 500,
    ) -> None:
        if not allowed_roots:
            raise ValueError("RealFsTools requires at least one allowed root")
        self.allowed_roots = list(allowed_roots)
        self.max_file_bytes = max_file_bytes
        self.max_glob_matches = max_glob_matches
        self.max_grep_matches = max_grep_matches

    # ---- read ----

    def read(self, **kwargs: Any) -> Dict[str, Any]:
        paths = self._collect_paths(kwargs)
        snippets: List[Dict[str, Any]] = []
        errors: List[str] = []
        for raw in paths:
            resolved, deny = safe_resolve(raw, self.allowed_roots)
            if deny is not None or resolved is None:
                errors.append(f"{raw}: denied ({deny.value if deny else 'unknown'})")
                continue
            try:
                size = resolved.stat().st_size
                if size > self.max_file_bytes:
                    errors.append(
                        f"{raw}: file too large ({size} > {self.max_file_bytes})"
                    )
                    continue
                content = resolved.read_text(encoding="utf-8", errors="replace")
                snippets.append(
                    {"path": str(resolved), "content": content, "size": size}
                )
            except Exception as exc:  # noqa: BLE001
                errors.append(f"{raw}: {exc}")
        return {"snippets": snippets, "errors": errors}

    # ---- write ----

    def write(self, **kwargs: Any) -> Dict[str, Any]:
        path = kwargs.get("path")
        content = kwargs.get("content", "")
        if not path:
            return {"status": "error", "reason": "missing 'path'"}
        resolved, deny = safe_resolve(str(path), self.allowed_roots)
        if deny is not None or resolved is None:
            return {
                "status": "denied",
                "reason": deny.value if deny else "unknown",
                "path": str(path),
            }
        resolved.parent.mkdir(parents=True, exist_ok=True)
        resolved.write_text(str(content), encoding="utf-8")
        return {
            "status": "ok",
            "written": str(resolved),
            "bytes": len(str(content).encode("utf-8")),
        }

    # ---- edit (string replace) ----

    def edit(self, **kwargs: Any) -> Dict[str, Any]:
        path = kwargs.get("path")
        old = kwargs.get("old", "")
        new = kwargs.get("new", "")
        if not path:
            return {"status": "error", "reason": "missing 'path'"}
        resolved, deny = safe_resolve(str(path), self.allowed_roots)
        if deny is not None or resolved is None:
            return {"status": "denied", "reason": deny.value if deny else "unknown"}
        if not resolved.is_file():
            return {"status": "error", "reason": "file not found"}
        text = resolved.read_text(encoding="utf-8", errors="replace")
        if old not in text:
            return {"status": "error", "reason": "old string not found"}
        before = text
        after = text.replace(old, new, 1)
        resolved.write_text(after, encoding="utf-8")
        diff = "".join(
            difflib.unified_diff(
                before.splitlines(keepends=True),
                after.splitlines(keepends=True),
                fromfile=str(resolved),
                tofile=str(resolved),
            )
        )
        return {"status": "ok", "edited": str(resolved), "diff": diff}

    # ---- patch.apply (unified diff) ----

    def patch_apply(self, **kwargs: Any) -> Dict[str, Any]:
        patch = kwargs.get("patch", "") or ""
        if not patch:
            return {"status": "error", "reason": "missing 'patch'"}
        # Minimal unified-diff applier: parse hunks per file. Not as robust as
        # `patch(1)` but enough for small, well-formed diffs.
        files_changed = self._apply_unified_diff(patch)
        return {"status": "ok" if files_changed else "noop", "changed_files": files_changed}

    def _apply_unified_diff(self, patch: str) -> List[str]:
        changed: List[str] = []
        cur_path: Optional[Path] = None
        cur_lines: Optional[List[str]] = None
        offset = 0
        hunk_re = re.compile(r"^@@\s+-(\d+)(?:,(\d+))?\s+\+(\d+)(?:,(\d+))?\s+@@")
        for line in patch.splitlines():
            if line.startswith("+++ "):
                rel = line[4:].strip()
                if rel.startswith("b/"):
                    rel = rel[2:]
                resolved, deny = safe_resolve(rel, self.allowed_roots)
                if deny is not None or resolved is None:
                    cur_path = None
                    cur_lines = None
                    continue
                cur_path = resolved
                cur_path.parent.mkdir(parents=True, exist_ok=True)
                if cur_path.is_file():
                    cur_lines = cur_path.read_text(encoding="utf-8", errors="replace").splitlines(keepends=True)
                else:
                    cur_lines = []
                offset = 0
                continue
            if cur_path is None or cur_lines is None:
                continue
            m = hunk_re.match(line)
            if m:
                hunk_start = int(m.group(3)) - 1 + offset
                continue
            if line.startswith("+") and not line.startswith("+++"):
                if cur_lines is not None:
                    insert_at = max(0, hunk_start)
                    cur_lines.insert(insert_at, line[1:] + ("\n" if not line.endswith("\n") else ""))
                    hunk_start += 1
                    offset += 1
            elif line.startswith("-") and not line.startswith("---"):
                if cur_lines and 0 <= hunk_start < len(cur_lines):
                    del cur_lines[hunk_start]
                    offset -= 1
            elif line.startswith(" "):
                hunk_start += 1
            else:
                continue
            cur_path.write_text("".join(cur_lines), encoding="utf-8")
            if str(cur_path) not in changed:
                changed.append(str(cur_path))
        return changed

    # ---- glob ----

    def glob_search(self, **kwargs: Any) -> Dict[str, Any]:
        pattern = kwargs.get("pattern") or "*"
        root = kwargs.get("root") or self.allowed_roots[0]
        resolved_root, deny = safe_resolve(root, self.allowed_roots)
        if deny is not None or resolved_root is None:
            return {"matches": [], "deny": deny.value if deny else None}
        matches: List[str] = []
        for p in resolved_root.rglob(pattern):
            try:
                p.relative_to(resolved_root)
            except ValueError:
                continue
            matches.append(str(p))
            if len(matches) >= self.max_glob_matches:
                break
        return {"matches": matches, "pattern": pattern, "root": str(resolved_root)}

    # ---- grep ----

    def grep_search(self, **kwargs: Any) -> Dict[str, Any]:
        pattern = kwargs.get("pattern")
        root = kwargs.get("root") or self.allowed_roots[0]
        if not pattern:
            return {"status": "error", "reason": "missing 'pattern'"}
        resolved_root, deny = safe_resolve(root, self.allowed_roots)
        if deny is not None or resolved_root is None:
            return {"matches": [], "deny": deny.value if deny else None}
        try:
            regex = re.compile(pattern)
        except re.error as exc:
            return {"matches": [], "error": str(exc)}
        matches: List[Dict[str, Any]] = []
        for path in resolved_root.rglob("*"):
            if not path.is_file():
                continue
            try:
                with path.open("r", encoding="utf-8", errors="replace") as fh:
                    for lineno, line in enumerate(fh, start=1):
                        if regex.search(line):
                            matches.append(
                                {
                                    "path": str(path),
                                    "line": lineno,
                                    "text": line.rstrip("\n"),
                                }
                            )
                            if len(matches) >= self.max_grep_matches:
                                return {"matches": matches, "pattern": pattern}
            except Exception:  # noqa: BLE001
                continue
        return {"matches": matches, "pattern": pattern}

    # ---- git status / diff (best-effort, read-only) ----

    def git_status(self, **kwargs: Any) -> Dict[str, Any]:
        import subprocess

        root = self.allowed_roots[0]
        try:
            result = subprocess.run(
                ["git", "-C", root, "status", "--porcelain"],
                capture_output=True,
                text=True,
                timeout=10,
            )
            return {
                "clean": not result.stdout.strip(),
                "changes": result.stdout.splitlines(),
            }
        except Exception as exc:  # noqa: BLE001
            return {"clean": True, "error": str(exc)}

    def git_diff(self, **kwargs: Any) -> Dict[str, Any]:
        import subprocess

        root = self.allowed_roots[0]
        try:
            result = subprocess.run(
                ["git", "-C", root, "diff"],
                capture_output=True,
                text=True,
                timeout=10,
            )
            text = result.stdout[: self.max_file_bytes]
            return {"diff": text, "summary": f"{len(text.splitlines())} lines"}
        except Exception as exc:  # noqa: BLE001
            return {"diff": "", "summary": str(exc)}

    # ---- helpers ----

    def _collect_paths(self, kwargs: Dict[str, Any]) -> List[str]:
        paths = kwargs.get("paths")
        if isinstance(paths, list):
            return [str(p) for p in paths]
        single = kwargs.get("path")
        if single:
            return [str(single)]
        return []
