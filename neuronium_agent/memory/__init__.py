"""Memory layer: GraphRAG-compatible models, pluggable backends."""

from neuronium_agent.memory.graphrag import (
    Entity,
    GraphRAG,
    MockGraphRAG,
    Relationship,
    RetrievalQuery,
    RetrievalResult,
)
from neuronium_agent.memory.artifact_graph import Artifact, ArtifactGraph
from neuronium_agent.memory.backend import (
    IngestDocument,
    MemoryBackend,
    MemoryConfig,
    build_backend,
    list_backends,
    register_backend,
)
from neuronium_agent.memory.raganything_backend import (
    RAGAnythingBackend,
    factory as _raganything_factory,
)


def _mock_factory(config: MemoryConfig) -> MockGraphRAG:
    return MockGraphRAG()


register_backend("mock", _mock_factory)
register_backend("raganything", _raganything_factory)


__all__ = [
    "Artifact",
    "ArtifactGraph",
    "Entity",
    "GraphRAG",
    "IngestDocument",
    "MemoryBackend",
    "MemoryConfig",
    "MockGraphRAG",
    "RAGAnythingBackend",
    "Relationship",
    "RetrievalQuery",
    "RetrievalResult",
    "build_backend",
    "list_backends",
    "register_backend",
]
