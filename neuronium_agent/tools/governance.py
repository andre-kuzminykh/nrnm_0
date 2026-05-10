"""Tool permission policy."""

from __future__ import annotations

from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict


class PermissionDecision(str, Enum):
    ALLOW = "allow"
    DENY = "deny"
    REQUIRE_APPROVAL = "require_approval"


class ToolPolicyEntry(BaseModel):
    model_config = ConfigDict(extra="forbid")
    tool_ref: str
    agent_id: Optional[str] = None
    mode: PermissionDecision


class PolicyEngine:
    """Resolves permission mode for (tool, agent) given layered policy.

    Resolution order: session → run → pack → global default.
    """

    def __init__(
        self,
        defaults: Optional[Dict[str, PermissionDecision]] = None,
        pack_entries: Optional[List[ToolPolicyEntry]] = None,
    ) -> None:
        self.defaults: Dict[str, PermissionDecision] = dict(defaults or {})
        self.pack_entries: List[ToolPolicyEntry] = list(pack_entries or [])
        self.session_overrides: Dict[str, PermissionDecision] = {}
        self.run_overrides: Dict[str, PermissionDecision] = {}

    def set_session(self, tool_ref: str, decision: PermissionDecision) -> None:
        self.session_overrides[tool_ref] = decision

    def set_run(self, tool_ref: str, decision: PermissionDecision) -> None:
        self.run_overrides[tool_ref] = decision

    def from_pack_compiler(self, entries: List["ToolPolicyEntry"]) -> "PolicyEngine":
        # Accept the compiler's ToolPolicyEntry shape (string mode).
        coerced: List[ToolPolicyEntry] = []
        for entry in entries:
            mode = entry.mode if hasattr(entry, "mode") else "allow"
            if isinstance(mode, PermissionDecision):
                coerced.append(
                    ToolPolicyEntry(
                        tool_ref=entry.tool_ref, agent_id=entry.agent_id, mode=mode
                    )
                )
            else:
                coerced.append(
                    ToolPolicyEntry(
                        tool_ref=entry.tool_ref,
                        agent_id=entry.agent_id,
                        mode=PermissionDecision(mode),
                    )
                )
        return PolicyEngine(defaults=self.defaults, pack_entries=coerced)

    def resolve(self, tool_ref: str, agent_id: Optional[str] = None) -> PermissionDecision:
        if tool_ref in self.session_overrides:
            return self.session_overrides[tool_ref]
        if tool_ref in self.run_overrides:
            return self.run_overrides[tool_ref]
        # Agent-specific pack entry wins over tool-level pack entry.
        if agent_id:
            for entry in self.pack_entries:
                if entry.tool_ref == tool_ref and entry.agent_id == agent_id:
                    return entry.mode
        for entry in self.pack_entries:
            if entry.tool_ref == tool_ref and entry.agent_id is None:
                return entry.mode
        if tool_ref in self.defaults:
            return self.defaults[tool_ref]
        return PermissionDecision.ALLOW
