"""Mock GraphRAG retrieval tests."""

from __future__ import annotations

from neuronium_agent.memory.graphrag import MockGraphRAG, RetrievalQuery


def test_retrieval_returns_entities_for_known_pack() -> None:
    rag = MockGraphRAG()
    result = rag.retrieve(RetrievalQuery(text="calculator", top_k=3), pack_id="coding")
    names = {e.name for e in result.entities}
    assert "calculator" in names or any("calculator" in (a or "") for a in names)


def test_retrieval_falls_back_to_pack_entries() -> None:
    rag = MockGraphRAG()
    result = rag.retrieve(RetrievalQuery(text="nothing-matches", top_k=2), pack_id="hr")
    assert result.entities
