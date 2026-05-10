"""GraphRAG models and a deterministic mock backend with golden fixtures."""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Protocol

from pydantic import BaseModel, ConfigDict, Field


class Entity(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: str
    type: str
    name: str
    aliases: List[str] = Field(default_factory=list)
    attrs: Dict[str, Any] = Field(default_factory=dict)


class Relationship(BaseModel):
    model_config = ConfigDict(extra="forbid")
    src: str
    dst: str
    kind: str


class RetrievalQuery(BaseModel):
    model_config = ConfigDict(extra="forbid")
    text: str
    top_k: int = 5
    types: List[str] = Field(default_factory=list)


class RetrievalResult(BaseModel):
    model_config = ConfigDict(extra="forbid")
    entities: List[Entity] = Field(default_factory=list)
    snippets: List[str] = Field(default_factory=list)
    artifacts: List[str] = Field(default_factory=list)


class GraphRAG(Protocol):
    def retrieve(self, query: RetrievalQuery) -> RetrievalResult: ...

    def write_back(self, entities: List[Entity], relationships: List[Relationship]) -> None: ...


_DEFAULT_GOLDEN = {
    "coding": [
        Entity(
            id="repo.calculator",
            type="module",
            name="calculator",
            aliases=["src/calculator.py"],
            attrs={"description": "A small calculator module"},
        ),
        Entity(
            id="repo.tests.test_calculator",
            type="test_file",
            name="test_calculator",
            aliases=["tests/test_calculator.py"],
            attrs={"description": "Tests for the calculator module"},
        ),
    ],
    "marketing": [
        Entity(
            id="customer.indie_dev",
            type="persona",
            name="Indie dev",
            attrs={"pain": "wants a quick coding agent"},
        ),
    ],
    "hr": [
        Entity(
            id="candidate.C-001",
            type="candidate",
            name="A. Doe",
            attrs={"skill_match": 0.92},
        ),
    ],
}


class MockGraphRAG:
    """Deterministic GraphRAG used for unit tests and `--mock` runs."""

    name = "mock"
    ready = True

    def __init__(self) -> None:
        self._entities: Dict[str, Entity] = {}
        self._relationships: List[Relationship] = []
        self._documents: List[Dict[str, Any]] = []
        # Load golden fixtures keyed by pack id.
        for pack_id, entities in _DEFAULT_GOLDEN.items():
            for entity in entities:
                key = f"{pack_id}/{entity.id}"
                self._entities[key] = entity

    def ingest(self, documents: List[Any]) -> Dict[str, Any]:
        """Append documents into the deterministic index.

        Accepts either `IngestDocument` instances or plain dicts. Tokens from
        each document become searchable via `retrieve`.
        """
        added: List[str] = []
        for doc in documents:
            data = doc.model_dump() if hasattr(doc, "model_dump") else dict(doc)
            doc_id = data.get("id") or f"doc-{len(self._documents) + 1}"
            text = data.get("text") or ""
            pack_id = data.get("pack_id") or "default"
            entity = Entity(
                id=f"ingested.{doc_id}",
                type="document",
                name=str(doc_id),
                aliases=[],
                attrs={"text": text, "metadata": data.get("metadata") or {}},
            )
            self._entities[f"{pack_id}/{entity.id}"] = entity
            self._documents.append({**data, "id": doc_id, "pack_id": pack_id})
            added.append(doc_id)
        return {"ingested": added, "total_documents": len(self._documents)}

    def retrieve(self, query: RetrievalQuery, *, pack_id: Optional[str] = None) -> RetrievalResult:
        text = query.text.lower()
        matched: List[Entity] = []
        snippets: List[str] = []
        for key, entity in self._entities.items():
            if pack_id and not key.startswith(f"{pack_id}/"):
                continue
            haystack = " ".join(
                [
                    entity.id,
                    entity.type,
                    entity.name,
                    *(entity.aliases or []),
                    str(entity.attrs.get("text", "")),
                ]
            ).lower()
            if any(token in haystack for token in text.split() if token):
                matched.append(entity)
                snippets.append(
                    f"{entity.name}: {entity.attrs.get('description') or entity.attrs.get('text', '')}"
                )
            if len(matched) >= query.top_k:
                break
        if not matched and pack_id:
            # Fall back to first few entities for that pack.
            for key, entity in self._entities.items():
                if key.startswith(f"{pack_id}/"):
                    matched.append(entity)
                    snippets.append(entity.name)
                if len(matched) >= query.top_k:
                    break
        return RetrievalResult(entities=matched, snippets=snippets)

    def write_back(
        self, entities: List[Entity], relationships: List[Relationship]
    ) -> None:
        for entity in entities:
            self._entities[entity.id] = entity
        self._relationships.extend(relationships)

    def diagnostics(self) -> Dict[str, Any]:
        return {
            "backend": self.name,
            "ready": self.ready,
            "entities": len(self._entities),
            "relationships": len(self._relationships),
            "documents": len(self._documents),
        }
