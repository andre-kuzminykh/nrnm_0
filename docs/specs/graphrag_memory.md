# GraphRAG / Memory

Neuronium's memory layer is **pluggable** behind a single `MemoryBackend`
protocol. Built-in backends:

| Backend | Purpose | Dependencies |
| --- | --- | --- |
| `mock` | Deterministic GraphRAG with golden fixtures. Default for tests and `--mock` runs. | none |
| `raganything` | Adapter over [HKUDS/RAG-Anything](https://github.com/HKUDS/RAG-Anything): multimodal RAG over PDFs / Office / images / text. | `raganything[all]`, `lightrag`, `mineru` (optional), `paddleocr` (optional), `LibreOffice` (optional) |

Custom backends register via `register_backend(name, factory)`.

## Common contract

All backends implement:

```python
class MemoryBackend(Protocol):
    name: str
    ready: bool
    def retrieve(self, query: RetrievalQuery, *, pack_id: str | None = None) -> RetrievalResult: ...
    def ingest(self, documents: list[IngestDocument]) -> dict: ...
    def write_back(self, entities: list[Entity], relationships: list[Relationship]) -> None: ...
    def diagnostics(self) -> dict: ...
```

Shared data models (in `neuronium_agent.memory`):

- `Entity(id, type, name, aliases, attrs)`
- `Relationship(src, dst, kind)`
- `RetrievalQuery(text, top_k, types)`
- `RetrievalResult(entities, snippets, artifacts)`
- `IngestDocument(id, path?, text?, pack_id?, metadata)`
- `MemoryConfig(backend, working_dir, parser, parse_method, enable_*_processing, llm_provider, embedding_provider, embedding_dim, query_mode)`

## Selecting a backend

- **Python API.** Pass `memory_config=MemoryConfig(backend="raganything", ...)` to `run_objective` or `ObjectiveRunner`. Alternatively, pass a pre-built `memory=<MemoryBackend>` instance (this is how tests inject fakes).
- **CLI.** `--memory-backend raganything --memory-working-dir ./rag --memory-parser mineru --memory-query-mode hybrid` on `objective run` / `code`. Standalone management via `neuronium-agent memory ...`.
- **Config file.** `MemoryConfig` accepts arbitrary extra fields, so `.neuronium/config.yaml` can persist these values.

## Runtime events

The Objective Runner emits:

- `memory.initialized` — `{backend, ready}`
- `memory.retrieved` — `{backend, entities, snippets}`
- `memory.retrieval_failed` — `{backend, error}` (when a backend raises)

## RAG-Anything adapter

`neuronium_agent.memory.raganything_backend.RAGAnythingBackend` wraps the
upstream library:

- **Construction.**
  - Inject a pre-built `client` (used in tests).
  - Provide `client_factory(config)`.
  - Or let the adapter call `raganything.RAGAnything(...)` after you supply
    `llm_model_func` and `embedding_func` (and optionally `vision_model_func`)
    via `extra_funcs`.
- **Optionality.** If `raganything` is not importable, the backend remains
  importable but reports `ready = False` and `retrieve` returns an empty
  result. CLI doctor and `memory diagnostics` surface that state clearly so
  CI can keep running without the heavy dependency stack.
- **Async bridging.** RAG-Anything's `aquery` and `process_document_complete`
  are wrapped via `asyncio.run` for synchronous call sites.
- **Query mode.** Defaults to `hybrid`; configurable via `MemoryConfig.query_mode`
  or `--memory-query-mode`.
- **Ingestion.**
  - Documents with a `path` are forwarded to `process_document_complete`.
  - Documents with inline `text` are forwarded to `insert_content_list`.
  - Errors are collected per-document and reported in the result, never
    interrupt the whole batch.

## Evaluation hooks (golden fixtures)

`MockGraphRAG` ships built-in entities per pack so the GraphRAG evaluation
tests (NR-GRAG-EVAL-001..003) remain deterministic. The RAG-Anything backend is
covered by its own unit tests that inject a fake client — no network or LLM
call is made in CI.

## Roadmap

- v0.2 — wire the RAG-Anything backend into the model registry so its
  `llm_model_func` / `embedding_func` are resolved via Neuronium providers.
- v0.2 — add per-pack default ingestion lists in the Pack DSL (`memory.documents`).
- v0.3 — additional adaptors (`llamaindex`, `chroma`, native pgvector).
