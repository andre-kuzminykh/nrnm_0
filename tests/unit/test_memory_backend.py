"""Memory backend protocol and RAG-Anything adapter tests."""

from __future__ import annotations

from typing import Any, Dict, List

import pytest

import neuronium_agent.memory.raganything_backend as raganything_backend
from neuronium_agent.memory import (
    IngestDocument,
    MemoryBackend,
    MemoryConfig,
    MockGraphRAG,
    RAGAnythingBackend,
    RetrievalQuery,
    build_backend,
    list_backends,
)


# NR-UT-MEM-001
def test_registry_exposes_default_backends() -> None:
    names = list_backends()
    assert "mock" in names
    assert "raganything" in names


def test_mock_backend_satisfies_protocol() -> None:
    backend = build_backend(MemoryConfig(backend="mock"))
    assert isinstance(backend, MemoryBackend)
    assert backend.ready is True
    assert backend.name == "mock"


# NR-UT-MEM-005
def test_mock_ingest_then_retrieve(tmp_path) -> None:
    backend = MockGraphRAG()
    docs = [
        IngestDocument(id="d1", text="alpha quantum module description", pack_id="coding"),
        IngestDocument(id="d2", text="beta module about marketing", pack_id="coding"),
    ]
    result = backend.ingest(docs)
    assert result["total_documents"] == 2
    hits = backend.retrieve(RetrievalQuery(text="quantum", top_k=5), pack_id="coding")
    assert any(e.id == "ingested.d1" for e in hits.entities)


# NR-UT-MEM-002
def test_raganything_backend_fallback_when_not_installed(monkeypatch) -> None:
    monkeypatch.setattr(raganything_backend, "_try_import_raganything", lambda: None)
    backend = RAGAnythingBackend(MemoryConfig(backend="raganything"))
    assert backend.name == "raganything"
    assert backend.ready is False
    diag = backend.diagnostics()
    assert diag["raganything_installed"] is False
    assert "not installed" in (diag["init_error"] or "")
    result = backend.retrieve(RetrievalQuery(text="anything", top_k=3))
    assert result.entities == []
    assert result.snippets == []
    ingest_report = backend.ingest([IngestDocument(id="x", text="hello")])
    assert ingest_report["ready"] is False
    assert ingest_report["skipped"] == ["x"]


class _FakeRAGAnything:
    """Synchronous test double for the RAG-Anything client."""

    def __init__(self) -> None:
        self.processed: List[str] = []
        self.inserted: List[Dict[str, Any]] = []
        self.queries: List[str] = []
        self.return_value: Any = "result-snippet-1\nresult-snippet-2"

    def process_document_complete(self, path: str):  # noqa: D401
        self.processed.append(path)

        async def _noop() -> None:
            return None

        return _noop()

    def insert_content_list(self, payload: List[Dict[str, Any]]):
        self.inserted.append(payload)

        async def _noop() -> None:
            return None

        return _noop()

    def aquery(self, text: str, mode: str = "hybrid"):
        self.queries.append((text, mode))

        async def _result() -> Any:
            return self.return_value

        return _result()


# NR-UT-MEM-003
def test_raganything_dispatches_path_and_text(tmp_path) -> None:
    client = _FakeRAGAnything()
    backend = RAGAnythingBackend(MemoryConfig(backend="raganything"), client=client)
    assert backend.ready is True
    pdf = tmp_path / "doc.pdf"
    pdf.write_text("fake pdf")
    report = backend.ingest(
        [
            IngestDocument(id="pdf", path=str(pdf)),
            IngestDocument(id="text", text="hello world"),
        ]
    )
    assert report["ingested"] == ["pdf", "text"]
    assert client.processed == [str(pdf)]
    assert client.inserted[0][0]["id"] == "text"


# NR-UT-MEM-004
def test_raganything_retrieve_coerces_return_value() -> None:
    client = _FakeRAGAnything()
    client.return_value = "line1\nline2\nline3"
    backend = RAGAnythingBackend(MemoryConfig(backend="raganything"), client=client)
    result = backend.retrieve(RetrievalQuery(text="anything", top_k=2))
    assert result.snippets == ["line1", "line2"]

    client.return_value = {"answer": "from dict"}
    result = backend.retrieve(RetrievalQuery(text="anything", top_k=3))
    assert result.snippets == ["from dict"]

    client.return_value = None
    result = backend.retrieve(RetrievalQuery(text="anything", top_k=3))
    assert result.snippets == []


def test_raganything_retrieve_swallows_client_errors() -> None:
    class _BoomClient:
        async def aquery(self, text: str, mode: str = "hybrid"):
            raise RuntimeError("upstream down")

    backend = RAGAnythingBackend(MemoryConfig(backend="raganything"), client=_BoomClient())
    result = backend.retrieve(RetrievalQuery(text="anything"))
    assert any("retrieval error" in s for s in result.snippets)


def test_raganything_skips_invalid_document() -> None:
    client = _FakeRAGAnything()
    backend = RAGAnythingBackend(MemoryConfig(backend="raganything"), client=client)
    report = backend.ingest(
        [
            IngestDocument(id="ok", text="hello"),
            IngestDocument(id="bad"),
        ]
    )
    assert "ok" in report["ingested"]
    assert any(s.startswith("bad:") for s in report["skipped"])


def test_build_backend_with_unknown_name_errors() -> None:
    with pytest.raises(KeyError):
        build_backend(MemoryConfig(backend="does-not-exist"))


def test_raganything_default_client_requires_funcs(monkeypatch) -> None:
    # Pretend the package is importable so the adapter takes the default path.
    sentinel_module = type("M", (), {})
    sentinel_module.RAGAnything = lambda **kw: None  # type: ignore[attr-defined]
    sentinel_module.RAGAnythingConfig = lambda **kw: None  # type: ignore[attr-defined]
    monkeypatch.setattr(
        raganything_backend, "_try_import_raganything", lambda: sentinel_module
    )
    backend = RAGAnythingBackend(MemoryConfig(backend="raganything"))
    assert backend.ready is False
    assert "llm_model_func" in (backend.diagnostics()["init_error"] or "")
