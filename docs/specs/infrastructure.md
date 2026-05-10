# Infrastructure

## v0.1 (this release)

- Python ≥ 3.10.
- Dependencies: `pydantic`, `pyyaml`, `click`, `rich`.
- Optional dev: `pytest`.
- No persistent storage by default. Trace files are written to `<trace_dir>/<run_id>.jsonl` (default `.neuronium/traces/`).
- No network calls. All providers are mocked.
- No external secrets required.

## v0.2 (planned)

- Optional vector store for GraphRAG (e.g. SQLite + FTS5 or pgvector).
- Optional MCP runtime (`stdio` or HTTP) for real tools.
- Optional headless HTTP server (`uvicorn` or `starlette`) exposing SSE event stream.
- Optional providers: Anthropic, OpenAI, local models via vLLM/Ollama.

## File layout in a project using Neuronium

```
<project>/
  .neuronium/
    config.yaml             # project-level config (model aliases, packs path, etc.)
    config.local.yaml       # gitignored local overrides
    packs/                  # user-installed packs
    traces/                 # JSONL run traces
```
