# Neuronium — Non-Functional Requirements

- **NR-NFR-001 Reproducibility.** All MVP test paths run without network or live LLM calls. Mock provider outputs are deterministic given the same seed.
- **NR-NFR-002 Determinism in mock mode.** Re-running the same objective in mock mode produces identical Workflow IR and identical event sequences up to timestamps.
- **NR-NFR-003 Stable contracts.** Workflow IR is a stable public contract; LangGraph internals are not exposed.
- **NR-NFR-004 Safety by default.** Tools with `risk: high` or `risk: critical` default to `require_approval` or `deny`; destructive shell commands default to `deny`.
- **NR-NFR-005 Observability.** Every node execution and every tool call shall produce a trace event with `seq` monotonically increasing per run.
- **NR-NFR-006 Trace integrity.** Trace entries are append-only JSON-Lines.
- **NR-NFR-007 Secret hygiene.** Trace and artifact exports redact secrets before disk write.
- **NR-NFR-008 Test isolation.** Tests must not write outside `tmp_path`-style temp directories.
- **NR-NFR-009 Time-to-first-result.** A vertical-slice mock run completes in under 2 seconds on a modern laptop.
- **NR-NFR-010 Versioning.** Packs declare `schema_version` and `compatible_neuronium`; incompatible packs refuse to load with a clear error.
- **NR-NFR-011 Extensibility.** Adding a new applied workflow pack does not require modifying core runtime code.
- **NR-NFR-012 Packaging.** The library installs with `pip install -e .` and a single `neuronium-agent` console script entry point.
