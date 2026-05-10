# Neuronium — Super Agent Platform with Applied Workflow Packs

Neuronium is a **Super Agent Platform**. It accepts complex objectives, builds a team of specialized agents, plans, executes, controls and adapts, and produces durable artifacts.

It is **not just a LangGraph wrapper**, **not just a coding agent**, and **not just a workflow executor**. Coding is one of the applied **Workflow Packs**, alongside marketing, HR, sales, consulting, and any custom pack you describe in a simple DSL or markdown template.

```
Neuronium Core
  ↓
Super Agent Runtime
  ↓
Applied Workflow Pack System
  ↓
Coding / Marketing / HR / Sales / Finance / Consulting / Custom Packs
  ↓
Super Interface: CLI today; API / Web / TUI later
```

> Source code inspiration: [dataism-lab/neuronium](https://github.com/dataism-lab/neuronium).

## Quick start

```bash
pip install -e .
neuronium-agent packs list
neuronium-agent objective run "Fix failing tests in this repository" --pack coding --mock
```

You should see:

```
pack: coding
status: succeeded
visited nodes: n_plan -> n_research -> n_edit -> n_edit_gate -> n_test -> n_review -> n_final
```

Run the test suite:

```bash
pytest -q
```

All tests run in mock mode and require no network or LLM keys.

## Layers

| Layer | What it provides |
| --- | --- |
| **Core Runtime** | Workflow IR, LangGraph-compatible backend, MCP tools, GraphRAG memory, trace, human gates, policy engine, artifacts, context budget. |
| **Super Agent Intelligence** | Objective intake, clarification, dynamic agent team creation, planning, graph building, control, adapt/replan, outcome synthesis. |
| **Applied Workflow Packs** | Coding pack (MVP), marketing pack (fixture), HR pack (fixture), custom packs from DSL/markdown. |

## CLI

```bash
neuronium-agent packs list                    # list installed packs
neuronium-agent packs show coding             # dump a pack as YAML
neuronium-agent packs validate <path|id>      # validate a pack
neuronium-agent packs install <path>          # install from a YAML file
neuronium-agent packs remove <id>             # remove an installed pack
neuronium-agent packs test <id>               # run a pack's mock tests
neuronium-agent packs init <name>             # scaffold a new pack
neuronium-agent packs generate <template.md> --out path/to/pack.yaml --id mypack

neuronium-agent memory backends               # list registered memory backends
neuronium-agent memory diagnostics --backend raganything
neuronium-agent memory ingest <path|text> --backend raganything --pack coding
neuronium-agent memory query "<text>" --backend mock --top-k 5

neuronium-agent objective run "<text>" [--pack <id>] [--mock] [--json] \
    [--memory-backend mock|raganything] [--memory-working-dir ./rag] \
    [--memory-parser mineru|docling|paddleocr] [--memory-query-mode hybrid]
neuronium-agent code "<text>"                 # coding-pack entry point
neuronium-agent doctor                        # preflight checks
```

## How a run works

1. The CLI invokes the **Objective Runner**.
2. The runner selects a **Workflow Pack** (explicit `--pack` or inferred from objective phrases).
3. The pack compiles into agent definitions, tool policies, and Workflow IR templates.
4. The **Dynamic Agent Factory** instantiates per-run agents.
5. **GraphRAG (mock)** retrieves context from golden fixtures.
6. **Workflow IR Builder** picks the right IR template; the **Compiler** produces a runnable graph.
7. The runtime executes nodes: model (mock), tool (mock MCP, governed), operator, human gate, critic, terminal.
8. Quality gates fire; failures trigger replan; final outcome is synthesized as markdown.
9. All events are recorded in JSONL trace with secrets redacted.

## Built-in packs

### Coding pack (`coding`)

Agents: `code_planner`, `code_researcher`, `code_editor`, `test_runner`, `code_reviewer`.

```bash
neuronium-agent objective run "Fix failing tests in this repository" --pack coding --mock
neuronium-agent code "fix this bug"
```

### Marketing pack (`marketing`)

Agents: `audience_researcher`, `campaign_planner`, `copywriter`, `performance_critic`.

```bash
neuronium-agent objective run "Create a marketing campaign for product launch" --pack marketing --mock
```

### HR pack (`hr`)

Agents: `recruiter`, `candidate_screener`, `interview_planner`, `compliance_critic`.

```bash
neuronium-agent objective run "Screen candidates for senior backend role" --pack hr --mock
```

## Authoring a custom pack

Two options:

1. **Scaffold** — `neuronium-agent packs init my_pack` produces a YAML stub you can edit.
2. **Markdown template** — fill `neuronium_agent/packs/templates/workflow_pack_template.md` and generate YAML:

```bash
neuronium-agent packs generate path/to/my_template.md --out packs/my_pack.yaml --id my_pack
neuronium-agent packs validate packs/my_pack.yaml
neuronium-agent packs install packs/my_pack.yaml
neuronium-agent objective run "<your phrase>" --pack my_pack --mock
```

The template has ten sections (domain, common user requests, agents, tools, risky actions, etc.) and the generator turns it into a valid pack.

## Specifications

Full specifications live in `docs/specs/`:

| File | Topic |
| --- | --- |
| `product_overview.md` | Vision and boundaries |
| `features.md` | Feature catalog with stable IDs |
| `architecture.md` | Layers, modules, data flow |
| `requirements_functional.md` | NR-FR-* requirements |
| `requirements_non_functional.md` | NR-NFR-* requirements |
| `workflow_ir_v0_1.md` | Workflow IR schema |
| `workflow_pack_dsl.md` | Pack DSL schema |
| `applied_workflow_packs.md` | Pack lifecycle and registry |
| `bdd_gherkin.md` | BDD scenarios |
| `test_matrix.md` | Test ↔ requirement matrix |
| `delivery_plan.md` | v0.1 and v0.2+ roadmap |

## Hierarchical planning (HTN)

Workflow packs can describe work as a tree of tasks instead of a flat phase list. The runtime decomposes a `compound` task via declared `methods` into `primitive` leaves, each mapped to a workflow phase. Every IR node carries a `task_path`, the runtime emits `plan.decomposed`, `subplan.entered/completed/failed`, and quality-gate failures replan the smallest sufficient subplan.

Coding pack example (excerpt):

```yaml
workflows:
  - id: fix_bug_workflow
    objective_match: fix_bug
    root_task: fix_bug_root

tasks:
  - id: fix_bug_root
    kind: compound
    methods:
      - id: standard
        subtasks: [understand_bug, edit_and_verify, review_outcome]
  - id: understand_bug
    kind: compound
    methods:
      - { id: plan_then_inspect, subtasks: [task_plan, task_research] }
  # ...
```

Packs without `tasks:` keep working — a depth-1 implicit plan is generated automatically. Full spec: `docs/specs/hierarchical_planning.md`.

## Memory backends (RAG)

The memory layer is pluggable. Two backends ship:

- `mock` — deterministic GraphRAG with golden fixtures (default, used in `--mock` runs and CI).
- `raganything` — adapter for [HKUDS/RAG-Anything](https://github.com/HKUDS/RAG-Anything), enabling real multimodal RAG over PDF / Office / image / text. Optional dependency: `pip install "neuronium-agent[raganything]"` (pulls in `lightrag`, `mineru` and friends).

Selection example:

```python
from neuronium_agent import run_objective
from neuronium_agent.memory import MemoryConfig

result = run_objective(
    "Summarize the design doc",
    pack="coding",
    memory_config=MemoryConfig(backend="raganything", working_dir="./rag",
                               parser="mineru", query_mode="hybrid"),
)
```

When `raganything` is not installed, the backend remains importable but reports `ready=False`; the run continues to work using the mock backend. `neuronium-agent doctor` reports the install status.

## Known limitations (v0.1)

- The LangGraph backend is an in-process executor with LangGraph-compatible semantics. v0.2 will swap in real LangGraph behind the same `CompiledGraph` interface.
- MCP integration is mocked; the lifecycle/spec is documented and ready for a real adapter.
- The mock GraphRAG uses golden fixtures. Real retrieval is available through the RAG-Anything backend when its optional dependencies are installed; CI exercises the adapter via injected fakes.
- HTTP server + SSE + OpenAPI are specified, not implemented.
- Replay is specified but not yet a `cli replay` command.

## Repository layout

```
neuronium_agent/
  ir/                # Workflow IR models, validator, compiler
  agents/            # Agent definitions, factory, registry, prompt composer
  packs/             # Pack DSL: parser, validator, compiler, registry, generator
    builtin/         # coding.yaml, marketing.yaml, hr.yaml
    templates/       # workflow_pack_template.md
  runtime/           # Backend, events, objective runner, state
  memory/            # GraphRAG mock, artifact graph
  tools/             # Tool registry, governance, mock MCP
  providers/         # Provider base, mock provider, model registry
  trace/             # JSONL recorder + secret redaction
  config/            # Config hierarchy
  cli/               # click entry points

prompts/             # Agent and operation prompts (markdown)
docs/specs/          # Specifications
tests/               # Unit / integration / e2e tests
```

## Definition of Done for v0.1

- ✅ Formal specs.
- ✅ Workflow IR + validator + compiler.
- ✅ Workflow Pack DSL: parser, validator, compiler, registry, generator, scaffolder.
- ✅ Agent system: definitions, instances, factory, registry, handoff, prompt composer.
- ✅ Built-in coding pack runs end-to-end in mock mode.
- ✅ Built-in marketing and HR packs validate and run in mock mode.
- ✅ Custom packs from markdown template.
- ✅ Trace records canonical events with secrets redacted.
- ✅ Tools governed by permission policy (allow / deny / require_approval).
- ✅ Critic-based control with replan.
- ✅ All vertical-slice tests pass without network or LLM access.
- ✅ CLI for `packs`, `objective run`, `code`, `doctor`.
