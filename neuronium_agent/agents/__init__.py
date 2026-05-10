"""Agent system: definitions, instances, factory, registry, handoff."""

from neuronium_agent.agents.models import (
    AgentDefinition,
    AgentInstance,
    AgentRole,
    OutputContract,
)
from neuronium_agent.agents.registry import AgentRegistry
from neuronium_agent.agents.factory import AgentFactory
from neuronium_agent.agents.handoff import Handoff
from neuronium_agent.agents.prompt_composer import compose_prompt

__all__ = [
    "AgentDefinition",
    "AgentInstance",
    "AgentRole",
    "AgentRegistry",
    "AgentFactory",
    "Handoff",
    "OutputContract",
    "compose_prompt",
]
