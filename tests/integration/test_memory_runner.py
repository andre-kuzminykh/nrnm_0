"""Memory backend integration with the Objective Runner."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional

import pytest

from neuronium_agent import run_objective
from neuronium_agent.memory import (
    IngestDocument,
    MemoryConfig,
    MockGraphRAG,
    RetrievalQuery,
)
from neuronium_agent.memory.graphrag import Entity, RetrievalResult


class _RecordingBackend:
    name = "recording"
    ready = True

    def __init__(self) -> None:
        self.queries: List[str] = []

    def retrieve(self, query: RetrievalQuery, *, pack_id: Optional[str] = None) -> RetrievalResult:
        self.queries.append(query.text)
        entity = Entity(id="recorded.1", type="hit", name="recorded")
        return RetrievalResult(entities=[entity], snippets=["recorded snippet"])

    def ingest(self, documents):
        return {"ingested": [], "ready": True}

    def write_back(self, entities, relationships) -> None:
        return None

    def diagnostics(self) -> Dict[str, Any]:
        return {"backend": self.name, "ready": True, "queries": len(self.queries)}


class _FailingBackend:
    name = "failing"
    ready = True

    def retrieve(self, query, *, pack_id=None):
        raise RuntimeError("oops")

    def ingest(self, documents):
        return {"ingested": [], "ready": True}

    def write_back(self, entities, relationships):
        return None

    def diagnostics(self):
        return {"backend": self.name, "ready": True}


# NR-IT-MEM-001
def test_memory_initialized_event_fires(tmp_path: Path) -> None:
    result = run_objective(
        "Fix failing tests",
        pack="coding",
        mock=True,
        trace_dir=str(tmp_path / "traces"),
    )
    kinds = [e["kind"] for e in result.events]
    assert "memory.initialized" in kinds
    init_events = [e for e in result.events if e["kind"] == "memory.initialized"]
    assert init_events[0]["payload"]["backend"] == "mock"
    assert init_events[0]["payload"]["ready"] is True


def test_injected_backend_used_for_retrieval(tmp_path: Path) -> None:
    backend = _RecordingBackend()
    result = run_objective(
        "Fix failing tests",
        pack="coding",
        mock=True,
        trace_dir=str(tmp_path / "traces"),
        memory=backend,
    )
    assert backend.queries, "objective runner should query the injected backend"
    retrieved = [e for e in result.events if e["kind"] == "memory.retrieved"]
    assert retrieved
    assert retrieved[0]["payload"]["backend"] == "recording"


# NR-IT-MEM-002
def test_failing_backend_emits_event(tmp_path: Path) -> None:
    result = run_objective(
        "Fix failing tests",
        pack="coding",
        mock=True,
        trace_dir=str(tmp_path / "traces"),
        memory=_FailingBackend(),
    )
    kinds = [e["kind"] for e in result.events]
    assert "memory.retrieval_failed" in kinds
    failure = [e for e in result.events if e["kind"] == "memory.retrieval_failed"][0]
    assert failure["payload"]["backend"] == "failing"


def test_memory_config_selects_named_backend(tmp_path: Path) -> None:
    result = run_objective(
        "Fix failing tests",
        pack="coding",
        mock=True,
        trace_dir=str(tmp_path / "traces"),
        memory_config=MemoryConfig(backend="mock"),
    )
    init = [e for e in result.events if e["kind"] == "memory.initialized"][0]
    assert init["payload"]["backend"] == "mock"


def test_memory_config_with_unknown_backend_falls_back_to_mock(tmp_path: Path) -> None:
    result = run_objective(
        "Fix failing tests",
        pack="coding",
        mock=True,
        trace_dir=str(tmp_path / "traces"),
        memory_config=MemoryConfig(backend="missing-backend"),
    )
    init = [e for e in result.events if e["kind"] == "memory.initialized"][0]
    assert init["payload"]["backend"] == "mock"
