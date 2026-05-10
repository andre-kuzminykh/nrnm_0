"""Unit tests for the agent system."""

from __future__ import annotations

import pytest

from neuronium_agent.agents.factory import AgentFactory
from neuronium_agent.agents.models import (
    AgentDefinition,
    AgentRole,
    OutputContract,
)
from neuronium_agent.agents.registry import AgentRegistry


class CaptureEvents:
    def __init__(self):
        self.events = []

    def emit(self, kind, payload=None):
        self.events.append((kind, payload or {}))


# NR-UT-AGENT-001
def test_agent_definition_schema() -> None:
    d = AgentDefinition(id="p", role=AgentRole.PLANNER, tools=["a", "b"], permissions={"a": "allow"})
    assert d.role == AgentRole.PLANNER
    assert d.tools == ["a", "b"]


# NR-UT-AGENT-002
def test_agent_instance_creation_emits_event() -> None:
    events = CaptureEvents()
    factory = AgentFactory("run-1", events=events)
    instance = factory.instantiate(AgentDefinition(id="p", role=AgentRole.PLANNER))
    assert instance.run_id == "run-1"
    assert any(k == "agent.created" for k, _ in events.events)


# NR-UT-AGENT-003
def test_agent_permission_is_agent_specific() -> None:
    d = AgentDefinition(
        id="x",
        role=AgentRole.EXECUTOR,
        permissions={"fs.edit": "require_approval", "fs.read": "allow"},
    )
    assert d.permissions["fs.edit"] == "require_approval"
    assert d.permissions["fs.read"] == "allow"


# NR-UT-AGENT-004
def test_agent_context_budget_is_per_agent() -> None:
    d = AgentDefinition(id="x", role=AgentRole.PLANNER, context_budget_tokens=4242)
    assert d.context_budget_tokens == 4242


# NR-UT-AGENT-005
def test_agent_output_contract_validation() -> None:
    contract = OutputContract(type="object", required=["plan"])
    assert contract.validate_payload({"plan": []}) == []
    errors = contract.validate_payload({})
    assert errors == ["missing required field 'plan'"]


def test_agent_registry_keys_by_pack() -> None:
    registry = AgentRegistry()
    registry.register(AgentDefinition(id="p", role=AgentRole.PLANNER, pack_id="coding"))
    registry.register(AgentDefinition(id="p", role=AgentRole.PLANNER, pack_id="hr"))
    assert registry.get("p", pack_id="coding").pack_id == "coding"
    assert registry.get("p", pack_id="hr").pack_id == "hr"
    assert len(registry.list_for_pack("coding")) == 1


def test_dynamic_synthesize() -> None:
    events = CaptureEvents()
    factory = AgentFactory("run-2", events=events)
    instance = factory.synthesize(
        agent_id="researcher_one",
        role=AgentRole.RESEARCHER,
        tools=["web.search"],
        permissions={"web.search": "allow"},
        context_budget_tokens=2000,
    )
    assert instance.definition.tools == ["web.search"]
    assert instance.definition.context_budget_tokens == 2000
