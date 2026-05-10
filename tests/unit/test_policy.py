"""Unit tests for the tool permission policy engine."""

from __future__ import annotations

from neuronium_agent.tools.governance import (
    PermissionDecision,
    PolicyEngine,
    ToolPolicyEntry,
)


def test_default_policy_is_allow() -> None:
    engine = PolicyEngine()
    assert engine.resolve("fs.read") == PermissionDecision.ALLOW


def test_pack_entry_overrides_default() -> None:
    engine = PolicyEngine(
        pack_entries=[
            ToolPolicyEntry(tool_ref="fs.edit", mode=PermissionDecision.REQUIRE_APPROVAL)
        ]
    )
    assert engine.resolve("fs.edit") == PermissionDecision.REQUIRE_APPROVAL


def test_agent_specific_pack_entry_wins() -> None:
    engine = PolicyEngine(
        pack_entries=[
            ToolPolicyEntry(tool_ref="fs.edit", mode=PermissionDecision.REQUIRE_APPROVAL),
            ToolPolicyEntry(
                tool_ref="fs.edit",
                agent_id="trusted",
                mode=PermissionDecision.ALLOW,
            ),
        ]
    )
    assert engine.resolve("fs.edit", agent_id="trusted") == PermissionDecision.ALLOW
    assert engine.resolve("fs.edit", agent_id="other") == PermissionDecision.REQUIRE_APPROVAL


def test_session_overrides_win() -> None:
    engine = PolicyEngine(
        pack_entries=[
            ToolPolicyEntry(tool_ref="fs.edit", mode=PermissionDecision.REQUIRE_APPROVAL)
        ]
    )
    engine.set_session("fs.edit", PermissionDecision.DENY)
    assert engine.resolve("fs.edit") == PermissionDecision.DENY


def test_critical_default_for_pack_with_high_risk() -> None:
    # Direct test: the pack compiler sets mode for high-risk tools to require_approval.
    from neuronium_agent.packs.registry import PackRegistry

    registry = PackRegistry()
    compiled = registry.get_compiled("coding")
    entries = {e.tool_ref: e.mode for e in compiled.tool_policy if e.agent_id is None}
    assert entries["fs.edit"] == "require_approval"
    assert entries["shell.run"] == "require_approval"
