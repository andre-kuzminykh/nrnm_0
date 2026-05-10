"""Artifact graph: track artifacts produced/consumed by a run."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field


class Artifact(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: str
    kind: str
    name: str
    content: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class ArtifactGraph:
    def __init__(self) -> None:
        self._artifacts: Dict[str, Artifact] = {}

    def add(self, artifact: Artifact) -> None:
        self._artifacts[artifact.id] = artifact

    def get(self, artifact_id: str) -> Optional[Artifact]:
        return self._artifacts.get(artifact_id)

    def all(self) -> List[Artifact]:
        return list(self._artifacts.values())
