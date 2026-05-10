"""Mock MCP-style tool implementations used in `--mock` runs.

The names mirror Anthropic-MCP-style namespaced refs `<server>.<tool>`.
"""

from __future__ import annotations

from typing import Any, Callable, Dict

from neuronium_agent.tools.registry import ToolRegistry


class MockMCP:
    """Registers deterministic mock tools onto a ToolRegistry."""

    def __init__(self) -> None:
        self.audit_log: list[Dict[str, Any]] = []

    def register_default(self, registry: ToolRegistry) -> None:
        registry.register("fs.read", self.fs_read, risk="low")
        registry.register("fs.write", self.fs_write, risk="high")
        registry.register("fs.edit", self.fs_edit, risk="high")
        registry.register("patch.apply", self.patch_apply, risk="high")
        registry.register("grep.search", self.grep_search, risk="low")
        registry.register("glob.search", self.glob_search, risk="low")
        registry.register("git.status", self.git_status, risk="low")
        registry.register("git.diff", self.git_diff, risk="low")
        registry.register("git.branch", self.git_branch, risk="medium")
        registry.register("shell.run", self.shell_run, risk="critical")
        registry.register("test.run", self.test_run, risk="medium")
        # Marketing
        registry.register("web.search", self.web_search, risk="low")
        registry.register("analytics.read", self.analytics_read, risk="low")
        registry.register("crm.segment_read", self.crm_segment_read, risk="low")
        registry.register("doc.write", self.doc_write, risk="medium")
        registry.register("campaign.publish", self.campaign_publish, risk="critical")
        # HR
        registry.register("ats.search", self.ats_search, risk="low")
        registry.register("ats.read_candidate", self.ats_read_candidate, risk="low")
        registry.register("calendar.create", self.calendar_create, risk="medium")
        registry.register("email.draft", self.email_draft, risk="medium")
        registry.register("ats.update_status", self.ats_update_status, risk="critical")

    # --- coding tools ---

    def fs_read(self, **kwargs: Any) -> Dict[str, Any]:
        paths = kwargs.get("paths") or [kwargs.get("path")] or []
        snippets = []
        for path in paths:
            snippets.append({"path": path, "content": f"// mock content of {path}"})
        self.audit_log.append({"tool": "fs.read", "paths": paths})
        return {"snippets": snippets}

    def fs_write(self, **kwargs: Any) -> Dict[str, Any]:
        path = kwargs.get("path")
        self.audit_log.append({"tool": "fs.write", "path": path})
        return {"written": path}

    def fs_edit(self, **kwargs: Any) -> Dict[str, Any]:
        path = kwargs.get("path")
        self.audit_log.append({"tool": "fs.edit", "path": path})
        return {"edited": path}

    def patch_apply(self, **kwargs: Any) -> Dict[str, Any]:
        patch = kwargs.get("patch") or ""
        self.audit_log.append({"tool": "patch.apply"})
        return {"applied": True, "patch_chars": len(str(patch))}

    def grep_search(self, **kwargs: Any) -> Dict[str, Any]:
        pattern = kwargs.get("pattern")
        return {"matches": [], "pattern": pattern}

    def glob_search(self, **kwargs: Any) -> Dict[str, Any]:
        pattern = kwargs.get("pattern")
        return {"matches": [], "pattern": pattern}

    def git_status(self, **kwargs: Any) -> Dict[str, Any]:
        return {"clean": True, "changes": []}

    def git_diff(self, **kwargs: Any) -> Dict[str, Any]:
        return {"diff": "", "summary": "no changes"}

    def git_branch(self, **kwargs: Any) -> Dict[str, Any]:
        return {"branch": kwargs.get("name", "main")}

    def shell_run(self, **kwargs: Any) -> Dict[str, Any]:
        command = kwargs.get("command", "")
        # Refuse destructive shell commands by default.
        if any(bad in command for bad in ("rm -rf /", "mkfs", "shutdown")):
            return {"status": "denied", "reason": "destructive command"}
        return {"status": "ok", "stdout": "(mock)", "command": command}

    def test_run(self, **kwargs: Any) -> Dict[str, Any]:
        # In mock mode, the test_runner agent supplies test_result via the model.
        # This tool is kept for completeness.
        return {"status": "passed", "summary": "mock test runner"}

    # --- marketing tools ---

    def web_search(self, **kwargs: Any) -> Dict[str, Any]:
        return {"results": []}

    def analytics_read(self, **kwargs: Any) -> Dict[str, Any]:
        return {"metrics": {}}

    def crm_segment_read(self, **kwargs: Any) -> Dict[str, Any]:
        return {"segments": []}

    def doc_write(self, **kwargs: Any) -> Dict[str, Any]:
        return {"doc_id": "mock_doc_1"}

    def campaign_publish(self, **kwargs: Any) -> Dict[str, Any]:
        return {"published": False, "reason": "approval required"}

    # --- HR tools ---

    def ats_search(self, **kwargs: Any) -> Dict[str, Any]:
        return {"candidates": []}

    def ats_read_candidate(self, **kwargs: Any) -> Dict[str, Any]:
        return {"candidate": {"id": kwargs.get("id"), "skills": []}}

    def calendar_create(self, **kwargs: Any) -> Dict[str, Any]:
        return {"event_id": "mock_evt_1"}

    def email_draft(self, **kwargs: Any) -> Dict[str, Any]:
        return {"draft_id": "mock_email_1"}

    def ats_update_status(self, **kwargs: Any) -> Dict[str, Any]:
        return {"updated": False, "reason": "approval required"}
