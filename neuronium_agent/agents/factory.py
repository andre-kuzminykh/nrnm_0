"""Dynamic Agent Factory: builds per-run AgentInstance objects."""

from __future__ import annotations

import uuid
from typing import Dict, Iterable, List, Optional

from neuronium_agent.agents.models import AgentDefinition, AgentInstance, AgentRole


class AgentFactory:
    def __init__(self, run_id: str, events: Optional[object] = None) -> None:
        self.run_id = run_id
        self.events = events

    def _emit(self, kind: str, payload: dict) -> None:
        if self.events is not None:
            self.events.emit(kind, payload)

    def instantiate(self, definition: AgentDefinition) -> AgentInstance:
        instance = AgentInstance(
            instance_id=f"{definition.id}-{uuid.uuid4().hex[:8]}",
            definition=definition,
            run_id=self.run_id,
        )
        self._emit(
            "agent.created",
            {
                "instance_id": instance.instance_id,
                "agent_id": definition.id,
                "role": definition.role.value,
                "pack_id": definition.pack_id,
                "tools": definition.tools,
                "context_budget_tokens": definition.context_budget_tokens,
                "memory_scope": definition.memory_scope,
            },
        )
        return instance

    def instantiate_team(
        self, definitions: Iterable[AgentDefinition]
    ) -> Dict[str, AgentInstance]:
        team: Dict[str, AgentInstance] = {}
        for definition in definitions:
            team[definition.id] = self.instantiate(definition)
        return team

    def synthesize(
        self,
        agent_id: str,
        role: AgentRole,
        tools: Optional[List[str]] = None,
        permissions: Optional[Dict[str, str]] = None,
        prompt_ref: Optional[str] = None,
        context_budget_tokens: int = 8000,
    ) -> AgentInstance:
        """Build a task-specific agent on the fly (Dynamic Agent Factory)."""
        definition = AgentDefinition(
            id=agent_id,
            role=role,
            tools=tools or [],
            permissions=permissions or {},
            prompt_ref=prompt_ref,
            context_budget_tokens=context_budget_tokens,
        )
        return self.instantiate(definition)
