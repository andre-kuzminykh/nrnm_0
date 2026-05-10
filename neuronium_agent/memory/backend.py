"""Memory backend protocol.

Neuronium decouples its memory layer from any specific implementation. Built-in
backends are `mock` (deterministic, used in tests/`--mock`) and `raganything`
(adapter over HKUDS/RAG-Anything). Custom backends register themselves through
`register_backend(name, factory)`.
"""

from __future__ import annotations

from typing import (
    Any,
    Callable,
    Dict,
    List,
    Optional,
    Protocol,
    runtime_checkable,
)

from pydantic import BaseModel, ConfigDict, Field

from neuronium_agent.memory.graphrag import (
    Entity,
    Relationship,
    RetrievalQuery,
    RetrievalResult,
)


class IngestDocument(BaseModel):
    """A document fed to a memory backend for indexing."""

    model_config = ConfigDict(extra="forbid")
    id: str
    path: Optional[str] = None
    text: Optional[str] = None
    pack_id: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


@runtime_checkable
class MemoryBackend(Protocol):
    """Pluggable retrieval/index backend."""

    name: str
    ready: bool

    def retrieve(
        self, query: RetrievalQuery, *, pack_id: Optional[str] = None
    ) -> RetrievalResult: ...

    def ingest(self, documents: List[IngestDocument]) -> Dict[str, Any]: ...

    def write_back(
        self,
        entities: List[Entity],
        relationships: List[Relationship],
    ) -> None: ...

    def diagnostics(self) -> Dict[str, Any]: ...


BackendFactory = Callable[["MemoryConfig"], MemoryBackend]


class MemoryConfig(BaseModel):
    """Configuration for the memory layer."""

    model_config = ConfigDict(extra="allow")
    backend: str = "mock"
    working_dir: Optional[str] = None
    parser: str = "mineru"
    parse_method: str = "auto"
    enable_image_processing: bool = False
    enable_table_processing: bool = True
    enable_equation_processing: bool = True
    llm_provider: Optional[str] = None
    embedding_provider: Optional[str] = None
    embedding_dim: int = 1024
    query_mode: str = "hybrid"
    # The factory will materialize callable functions for llm/embedding/vision
    # via the model provider registry when available.


_REGISTRY: Dict[str, BackendFactory] = {}


def register_backend(name: str, factory: BackendFactory) -> None:
    _REGISTRY[name] = factory


def list_backends() -> List[str]:
    return sorted(_REGISTRY.keys())


def build_backend(config: MemoryConfig) -> MemoryBackend:
    name = config.backend
    if name not in _REGISTRY:
        raise KeyError(
            f"unknown memory backend '{name}'; registered: {list_backends()}"
        )
    return _REGISTRY[name](config)
