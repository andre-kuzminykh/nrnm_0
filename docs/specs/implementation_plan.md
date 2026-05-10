# Implementation Plan — v0.1

| # | Step | Module | Status |
| --- | --- | --- | --- |
| 1 | Workflow IR models | `neuronium_agent/ir/models.py` | done |
| 2 | IR validator | `neuronium_agent/ir/validator.py` | done |
| 3 | IR compiler (in-process LangGraph-compatible) | `neuronium_agent/ir/compiler.py` | done |
| 4 | Agent models + registry + factory + handoff + prompt composer | `neuronium_agent/agents/*` | done |
| 5 | Pack DSL models + parser + validator + compiler + registry + generator | `neuronium_agent/packs/*` | done |
| 6 | Built-in coding pack YAML | `neuronium_agent/packs/builtin/coding.yaml` | done |
| 7 | Built-in marketing/HR pack YAML | `neuronium_agent/packs/builtin/{marketing,hr}.yaml` | done |
| 8 | Pack template | `neuronium_agent/packs/templates/workflow_pack_template.md` | done |
| 9 | Mock model provider | `neuronium_agent/providers/mock.py` | done |
| 10 | Tool registry + governance + mock MCP | `neuronium_agent/tools/*` | done |
| 11 | GraphRAG mock + artifact graph | `neuronium_agent/memory/*` | done |
| 12 | Trace recorder + redaction | `neuronium_agent/trace/*` | done |
| 13 | Config hierarchy | `neuronium_agent/config/*` | done |
| 14 | Runtime backend, events, state, objective runner | `neuronium_agent/runtime/*` | done |
| 15 | Public API | `neuronium_agent/api.py` | done |
| 16 | CLI (`packs`, `objective`, `code`, `doctor`) | `neuronium_agent/cli/main.py` | done |
| 17 | Tests (unit / integration / e2e) | `tests/*` | done |
| 18 | README + docs/specs/* | `README.md` + `docs/specs/*.md` | done |
