# Neuronium — Product Overview

## Vision

Neuronium is a **Super Agent Platform**. It is not only a LangGraph wrapper, not only a coding agent, and not only a workflow executor. It is a runtime that accepts complex objectives, builds agent teams, plans, executes, controls and adapts work, and produces durable artifacts.

## Three layers

```
Layer 1 — Core Runtime
  Workflow IR | LangGraph backend | MCP tools | GraphRAG memory
  trace/replay/audit | human gates | policy engine | artifacts | context

Layer 2 — Super Agent Intelligence
  objective intake | clarification | dynamic agent team creation
  planning | graph building | control | adapt/replan | outcome synthesis

Layer 3 — Applied Workflow Packs
  coding | marketing | HR | sales | consulting | custom packs
```

## Key idea

> Neuronium creates specialized agents and graphs for different applied workflows.
> Coding is one workflow pack, not the whole product.

A user expresses an objective in natural language; the runtime selects (or generates) a Workflow Pack, instantiates an agent team, builds a Workflow IR, compiles it to a LangGraph execution, governs tools through MCP, and produces a verifiable outcome with full trace.

## Primary users

- AI engineers building domain workflows (coding, marketing, HR, ...).
- Operators running production agents with safety policies.
- Researchers replaying and comparing runs.
- Power users describing custom workflow packs in markdown.

## Product boundaries

Neuronium **owns**:

- Super Agent runtime, Objective runner, Dynamic Agent Factory.
- Workflow IR runtime and Applied Workflow Pack system.
- LangGraph backend, MCP tool registry/governance, GraphRAG memory.
- planning → execution → control → adapt lifecycle.
- human gates, critic and commitment checks.
- trace / audit / replay, artifacts.
- runtime server, CLI, Python API, OpenAPI spec.
- model registry, agent/skill/prompt composition.
- deterministic mock mode, compatibility harness, golden traces.

Neuronium **does not own** (may be added later as packs):

- Process Compiler, TO-BE/AS-IS document parsing.
- Business process diagnosis as core.
- Desktop app, IDE extension, GitHub PR bot.

## Success criteria for v0.1

1. A user can run `neuronium-agent objective run "Fix failing tests" --pack coding --mock` end-to-end without live LLM calls.
2. The runtime selects the coding pack, instantiates planner / researcher / editor / test runner / reviewer agents, builds a Workflow IR, executes it, runs critics, and emits a final outcome with a trace.
3. The user can describe a new workflow pack in a markdown template and generate a YAML pack that validates.
4. Tools requiring write access wait for approval according to permission policy.
5. All vertical-slice tests pass in mock mode without network or LLM access.
