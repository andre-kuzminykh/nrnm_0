"""Unit tests for Workflow Pack DSL parsing, validation, compilation."""

from __future__ import annotations

import pytest

from neuronium_agent.packs.compiler import compile_pack
from neuronium_agent.packs.errors import PackValidationError
from neuronium_agent.packs.models import WorkflowPack
from neuronium_agent.packs.parser import parse_pack
from neuronium_agent.packs.validator import validate_pack
from neuronium_agent.packs.registry import PackRegistry


_VALID_PACK = {
    "pack": {
        "id": "test_pack",
        "name": "Test Pack",
        "version": "0.1.0",
        "schema_version": "0.1",
        "compatible_neuronium": ">=0.1.0",
        "domain": "testing",
        "description": "Pack for tests.",
    },
    "objectives": [
        {"id": "do_thing", "user_phrases": ["do the thing"]},
    ],
    "tools": [
        {"ref": "fs.read", "kind": "mcp", "risk": "low"},
    ],
    "agents": [
        {
            "id": "planner",
            "role": "planner",
            "tools": ["fs.read"],
            "permissions": {"fs.read": "allow"},
            "output_contract": {"type": "object", "required": ["plan"]},
        },
        {
            "id": "critic",
            "role": "critic",
            "tools": [],
            "permissions": {},
            "output_contract": {"type": "object", "required": ["verdict"]},
        },
    ],
    "workflows": [
        {
            "id": "do_thing_wf",
            "objective_match": "do_thing",
            "phases": [
                {"id": "plan", "agent": "planner", "outputs": ["plan"]},
                {"id": "review", "agent": "critic", "outputs": ["verdict"]},
            ],
        }
    ],
    "quality_gates": [
        {"id": "critic_passes", "condition": "verdict == 'PASS'", "on_fail": "replan"}
    ],
    "outputs": [{"id": "final", "type": "markdown", "includes": ["plan"]}],
    "tests": [{"id": "smoke", "objective": "do the thing", "expected": ["completes"]}],
}


# NR-UT-PACK-001
def test_pack_parser_accepts_valid_yaml() -> None:
    pack = parse_pack(_VALID_PACK)
    assert pack.id == "test_pack"
    assert len(pack.agents) == 2


# NR-UT-PACK-002
def test_pack_validator_rejects_unknown_tool_in_agent() -> None:
    bad = dict(_VALID_PACK)
    bad["agents"] = list(_VALID_PACK["agents"])
    bad["agents"][0] = {**_VALID_PACK["agents"][0], "tools": ["unknown.tool"]}
    pack = parse_pack(bad)
    with pytest.raises(PackValidationError):
        validate_pack(pack)


# NR-UT-PACK-003
def test_pack_compiler_emits_artifacts() -> None:
    pack = parse_pack(_VALID_PACK)
    compiled = compile_pack(pack)
    assert len(compiled.agent_definitions) == 2
    assert "do_thing" in compiled.ir_templates
    assert any(e.tool_ref == "fs.read" for e in compiled.tool_policy)


# NR-UT-PACK-004
def test_pack_schema_version_check() -> None:
    bad = {"pack": {**_VALID_PACK["pack"], "schema_version": "9.9"}}
    bad["agents"] = _VALID_PACK["agents"]
    bad["tools"] = _VALID_PACK["tools"]
    bad["objectives"] = _VALID_PACK["objectives"]
    bad["workflows"] = _VALID_PACK["workflows"]
    pack = parse_pack(bad)
    with pytest.raises(PackValidationError):
        validate_pack(pack)


def test_registry_discovers_builtin_packs() -> None:
    registry = PackRegistry()
    ids = registry.list_ids()
    assert "coding" in ids
    assert "marketing" in ids
    assert "hr" in ids


def test_coding_pack_compiles() -> None:
    registry = PackRegistry()
    compiled = registry.get_compiled("coding")
    agent_ids = {a.id for a in compiled.agent_definitions}
    assert {"code_planner", "code_researcher", "code_editor", "test_runner", "code_reviewer"} <= agent_ids
    assert "fix_bug" in compiled.ir_templates


def test_marketing_pack_validates() -> None:
    registry = PackRegistry()
    compiled = registry.get_compiled("marketing")
    assert {a.id for a in compiled.agent_definitions} >= {
        "audience_researcher",
        "campaign_planner",
        "copywriter",
        "performance_critic",
    }


def test_hr_pack_validates() -> None:
    registry = PackRegistry()
    compiled = registry.get_compiled("hr")
    assert {a.id for a in compiled.agent_definitions} >= {
        "recruiter",
        "candidate_screener",
        "interview_planner",
        "compliance_critic",
    }
