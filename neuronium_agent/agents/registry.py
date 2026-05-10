"""In-memory registry of agent definitions, keyed by `pack_id.agent_id`."""

from __future__ import annotations

from typing import Dict, Iterable, List, Optional

from neuronium_agent.agents.models import AgentDefinition


class AgentRegistry:
    def __init__(self) -> None:
        self._by_key: Dict[str, AgentDefinition] = {}

    @staticmethod
    def _key(pack_id: Optional[str], agent_id: str) -> str:
        if pack_id:
            return f"{pack_id}.{agent_id}"
        return agent_id

    def register(self, definition: AgentDefinition) -> None:
        key = self._key(definition.pack_id, definition.id)
        self._by_key[key] = definition

    def register_many(self, definitions: Iterable[AgentDefinition]) -> None:
        for definition in definitions:
            self.register(definition)

    def get(self, agent_id: str, pack_id: Optional[str] = None) -> AgentDefinition:
        key = self._key(pack_id, agent_id)
        if key not in self._by_key:
            raise KeyError(f"agent '{key}' not registered")
        return self._by_key[key]

    def list_for_pack(self, pack_id: str) -> List[AgentDefinition]:
        return [d for d in self._by_key.values() if d.pack_id == pack_id]

    def all(self) -> List[AgentDefinition]:
        return list(self._by_key.values())
