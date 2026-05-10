# Neuronium — Architecture

## Layered overview

```
+----------------------------------------------------------------------------+
|  Super Interface (CLI today; HTTP+SSE+Web specified)                        |
+----------------------------------------------------------------------------+
|  Objective Runner                                                           |
|     intake → clarify → plan → build IR → compile → execute → control →      |
|     adapt → final outcome                                                   |
+----------------------------------------------------------------------------+
|  Applied Workflow Pack Layer                                                |
|     Pack Registry • Pack DSL Parser/Validator/Compiler • Pack Generator     |
+----------------------------------------------------------------------------+
|  Super Agent Intelligence                                                   |
|     Dynamic Agent Factory • Agent Registry • Planner • Critic • Recovery    |
+----------------------------------------------------------------------------+
|  Workflow Runtime                                                           |
|     Workflow IR Builder/Validator/Compiler • LangGraph (in-proc) backend    |
+----------------------------------------------------------------------------+
|  Foundations                                                                |
|     MCP Tool Registry • Policy Engine • GraphRAG Memory • Trace/Audit       |
|     Model/Provider Registry • Artifact Store • Config Hierarchy             |
+----------------------------------------------------------------------------+
```

## Applied Workflow Layer flow

```
Workflow Pack Markdown / YAML
       │
       ▼
Workflow Pack DSL Parser
       │
       ▼
Workflow Pack Validator
       │
       ▼
Workflow Pack Compiler ──► Agent Definitions
                       └► Tool Policies
                       └► Workflow Templates
                       └► Quality Gates
                       └► Output Templates
                       │
                       ▼
              Dynamic Agent Factory
                       │
                       ▼
                Objective Runner
                       │
                       ▼
              Workflow IR Builder
                       │
                       ▼
            LangGraph-compatible runtime
```

## Module map (Python)

```
neuronium_agent/
  __init__.py
  api.py                       # public Python facade
  ir/                          # Workflow IR
    __init__.py
    models.py                  # IR nodes/edges/program
    validator.py               # structural validation
    compiler.py                # IR → execution graph
  runtime/
    __init__.py
    backend.py                 # in-process LangGraph-compatible backend
    objective_runner.py        # plan → build → compile → execute → adapt
    events.py                  # canonical event schema
    policy.py                  # tool permission policy
    artifacts.py               # artifact store
    state.py                   # run/session model
  agents/
    __init__.py
    models.py                  # AgentDefinition, AgentInstance, contracts
    registry.py                # agent registry
    factory.py                 # dynamic factory
    instances.py               # per-run agent instances
    handoff.py                 # handoff protocol
    prompt_composer.py         # effective prompt composition
  packs/
    __init__.py
    models.py                  # WorkflowPack, Objective, Workflow, Phase
    parser.py                  # YAML → pydantic
    validator.py
    compiler.py                # pack → agents+tools+IR template
    registry.py
    generator.py               # markdown template → YAML draft
    errors.py
    builtin/
      coding.yaml
      marketing.yaml
      hr.yaml
    templates/
      workflow_pack_template.md
  memory/
    __init__.py
    graphrag.py                # mock GraphRAG, golden fixtures
    artifact_graph.py
  tools/
    __init__.py
    registry.py                # tool descriptors
    mock_mcp.py                # deterministic mock MCP servers
    governance.py              # risk + permission resolution
  trace/
    __init__.py
    recorder.py                # trace file (JSON Lines) writer
    redact.py                  # secret redaction
  providers/
    __init__.py
    base.py
    mock.py                    # deterministic mock model provider
    registry.py                # model aliases (fast/smart/cheap/critic)
  config/
    __init__.py
    hierarchy.py               # built-in → global → project → local → env → CLI → session
  cli/
    __init__.py
    main.py                    # click entry point
    packs_cmd.py
    objective_cmd.py
    code_cmd.py
    doctor_cmd.py
```

## Data flow for a run

```
1. CLI receives "neuronium-agent objective run '<objective>' --pack coding --mock"
2. Config hierarchy resolves effective settings.
3. Pack Registry loads coding pack (builtin or installed).
4. Objective Runner records run/session, opens trace, attaches input.
5. Agent Factory builds agent instances from the pack's AgentDefinitions.
6. GraphRAG (mock) retrieves context from fixtures.
7. Planner produces task decomposition.
8. Workflow IR Builder produces IR from the pack workflow + task decomposition.
9. IR Validator checks shape and contracts.
10. IR Compiler produces a runnable graph.
11. Runtime executes nodes: model (mock), tool (mock MCP), operator, human gate.
12. Policy engine evaluates each tool call vs permission policy. High-risk tools
    request approval; in mock mode, auto-approval is configurable.
13. Critic node evaluates outputs against quality gates.
14. If a gate fails, Recovery selects strategy (retry / replan / abort).
15. Final Outcome Synthesizer composes a markdown report with evidence and
    artifact references.
16. Trace recorder writes ordered events to JSONL with secrets redacted.
```

## Workflow IR

A typed program of nodes and edges:

- `model` — calls a provider+role (mock in v0.1).
- `tool` — calls an MCP tool through governance.
- `operator` — pure transformation in-process.
- `human_gate` — pause point for approval or input.
- `critic` — quality check node.
- `recover` — selects recovery strategy.
- `terminal` — final outcome node.

Edges may be unconditional, conditional (predicate on state), or fallback.

A program declares input variables, output variables, and metadata (`pack_id`, `objective`, `agents[]`, `commitments[]`).

## Events

Canonical event types:

```
run.started, run.completed, run.failed
objective.intake, objective.clarified
pack.selected, pack.compiled
agent.created, agent.started, agent.completed, agent.failed, agent.handoff
ir.built, ir.validated, ir.compiled
node.started, node.completed, node.failed
tool.requested, tool.approved, tool.denied, tool.completed
critic.started, critic.completed
gate.failed
recovery.selected, replan.completed
human.requested, human.responded
outcome.produced
trace.exported
```

All events share envelope: `run_id`, `seq`, `ts`, `kind`, `payload`.

## Tool governance

Risk classes: `low | medium | high | critical`. Permission modes: `allow | deny | require_approval`. Resolution order: session → run → pack → global. Critical actions are denied unless explicitly enabled.

## Memory

The GraphRAG layer is mockable but typed: `Entity`, `Relationship`, `Artifact`, `RetrievalQuery`, `RetrievalResult`. Golden fixtures enable eval tests for retrieval precision and artifact preservation.

## Configuration hierarchy

```
built-in defaults
  global ~/.neuronium/config.yaml
    project <repo>/.neuronium/config.yaml
      local <repo>/.neuronium/config.local.yaml
        env vars (NEURONIUM_*)
          CLI flags
            session overrides
```

Project beats global, local beats project, env beats local, CLI beats env, session beats CLI.

## Secrets

The trace recorder applies a redaction pass before persistence; field keys matching `api_key`, `token`, `password`, `secret`, `authorization`, and bearer-style patterns are replaced with `***REDACTED***`.

## Deterministic mock mode

`--mock` forces:

- mock model provider with seedable outputs;
- mock MCP servers responding from fixtures;
- mock GraphRAG with golden fixture corpus;
- auto-approval of `require_approval` tools (configurable).

This is the path used by unit/integration/e2e tests in CI.
