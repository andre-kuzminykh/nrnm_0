# GraphRAG Memory

## Models

- `Entity(id, type, name, aliases, attrs)`
- `Relationship(src, dst, kind)`
- `RetrievalQuery(text, top_k, types)`
- `RetrievalResult(entities, snippets, artifacts)`

## v0.1 — mock backend with golden fixtures

`MockGraphRAG` ships with built-in entities per pack (calculator module for
coding, an indie-dev persona for marketing, a sample candidate for HR). A
deterministic substring match returns `RetrievalResult`s. Tests use these as
golden retrieval fixtures (NR-GRAG-EVAL-001..003).

## v0.2 — real backend

A real backend will implement the same interface using a vector store and an
entity extractor over project artifacts (code, docs, CRM records, etc.). The
runtime never depends on the concrete backend.
