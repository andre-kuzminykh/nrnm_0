# Delivery Plan

## v0.1 — Vertical Slice (this release)

1. Workflow IR models + validator.
2. Workflow Pack DSL: models, parser, validator, compiler, registry, generator.
3. Built-in coding pack (full mock e2e).
4. Built-in marketing and HR packs (mock validate + test).
5. Agent system: definitions, instances, factory, handoff, registry, prompt composer.
6. In-process LangGraph-compatible backend.
7. Mock providers (model, MCP, GraphRAG).
8. Trace recorder with secret redaction.
9. CLI: `objective run`, `packs list/show/validate/install/init/generate/test`, `code`, `doctor`.
10. Tests (unit + integration + e2e) all passing in mock mode.
11. README updated.

## v0.2 — Roadmap

- LangGraph as actual backend behind the same `CompiledGraph` interface.
- Real MCP integration (stdio + HTTP), lifecycle, schema discovery.
- Real GraphRAG implementation with vector store + entity extraction.
- Headless HTTP server with SSE event stream and OpenAPI.
- Super Interface (web) v0.

## v0.3 — Roadmap

- Sales / consulting / finance packs.
- Replay with persisted snapshots.
- IDE integrations and GitHub PR bot as integration packs (not core).
