# RAG-Anything Integration

## Goal

Embed [HKUDS/RAG-Anything](https://github.com/HKUDS/RAG-Anything) as a
first-class **memory backend** of Neuronium so every RAG-needing surface
(planner context, researcher snippets, critic evidence, custom pack workflows)
can use multimodal retrieval over real documents (PDF, Office, images, text)
when the optional dependency is installed.

## Requirements

- **NR-FR-GRAG-010** The system shall provide a pluggable `MemoryBackend`
  protocol with `retrieve`, `ingest`, `write_back`, `diagnostics`.
- **NR-FR-GRAG-011** The system shall register `mock` and `raganything`
  backends by default.
- **NR-FR-GRAG-012** The system shall continue to function (mock backend,
  graceful fallback) when `raganything` is not installed.
- **NR-FR-GRAG-013** The system shall expose `memory.initialized`,
  `memory.retrieved`, `memory.retrieval_failed` events with `backend` and
  `ready` fields.
- **NR-FR-GRAG-014** The system shall allow injecting a custom RAG-Anything
  client (or client factory) for testing and deployment.
- **NR-FR-GRAG-015** The system shall expose CLI commands `memory backends`,
  `memory diagnostics`, `memory ingest`, `memory query`.
- **NR-FR-GRAG-016** The system shall accept memory backend selection via CLI
  (`--memory-backend`, `--memory-working-dir`, `--memory-parser`,
  `--memory-query-mode`) for `objective run` and `code`.
- **NR-FR-GRAG-017** The system shall report `raganything` install status from
  `doctor`.

## Architecture

```
                  ┌───────────────────────────┐
                  │   ObjectiveRunner.run     │
                  └────────────┬──────────────┘
                               │ build_backend(MemoryConfig)
                               ▼
        ┌──────────────────────────────────────────────┐
        │  Memory backend registry                     │
        │   - "mock"        → MockGraphRAG             │
        │   - "raganything" → RAGAnythingBackend       │
        │   - <custom>      → user-registered          │
        └──────────────────────────────────────────────┘
                               │
       ┌───────────────────────┴────────────────────────┐
       ▼                                                ▼
  MockGraphRAG                                  RAGAnythingBackend
  (golden fixtures)                             (adapter over RAG-Anything)
                                                ├─ client / client_factory
                                                ├─ async wrappers
                                                └─ graceful fallback
```

## Behavior matrix

| Situation | Behavior |
| --- | --- |
| `raganything` not installed, backend = `mock` | mock works normally |
| `raganything` not installed, backend = `raganything` | adapter loads, `ready=False`, retrieval returns empty, diagnostics report `raganything_installed=False` |
| `raganything` installed, no llm/embedding funcs supplied | adapter loads, `ready=False`, init_error explains the missing functions |
| Injected `client` (e.g. in tests) | adapter uses it directly; `ready=True` |
| `client_factory` returns valid client | adapter uses it; `ready=True` |

## Ingestion contract

```python
class IngestDocument(BaseModel):
    id: str
    path: str | None
    text: str | None
    pack_id: str | None
    metadata: dict
```

- File on disk → `process_document_complete(path)`
- Inline text → `insert_content_list([{id, content, metadata}])`

The result is `{ingested: [...], skipped: [...], ready: bool}`.

## CLI

```bash
neuronium-agent memory backends
neuronium-agent memory diagnostics --backend raganything --working-dir ./rag
neuronium-agent memory ingest ./docs/spec.pdf --backend raganything --pack coding
neuronium-agent memory query "what is the calculator module?" --backend mock --top-k 3
neuronium-agent objective run "..." --pack coding --mock --memory-backend mock
```

## Tests

- `tests/unit/test_memory_backend.py` covers:
  - protocol contract for both `mock` and `raganything`;
  - graceful fallback when `raganything` is not installed;
  - dispatch of `path` vs `text` documents to the right RAG-Anything method;
  - retrieval coercion of the upstream return value (`str` / `dict` / `None`).
- `tests/integration/test_runner.py` extends with the memory selection event
  and a parametrized run using an injected RAG-Anything fake.
- All tests remain CI-safe: `raganything` is not installed; we test the adapter
  exclusively with injected fakes.

## Definition of Done

- ✅ Protocol defined and shared.
- ✅ MockGraphRAG fulfills the protocol with `ingest`/`diagnostics`.
- ✅ RAGAnythingBackend importable without the dep; graceful fallback.
- ✅ Backend selection via Python API and CLI.
- ✅ Memory events in trace.
- ✅ Tests for protocol contract, adapter, and runtime integration.
- ✅ Doctor reports installation status.
