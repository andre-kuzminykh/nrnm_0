# User Flows

## Flow 1 — Run a coding objective

```
user
  │
  │ neuronium-agent objective run "Fix failing tests" --pack coding --mock
  ▼
CLI parses args
  │
  ▼
Objective Runner
  ├─ select pack: coding
  ├─ compile pack (cached)
  ├─ instantiate agent team (5 agents)
  ├─ retrieve GraphRAG context
  ├─ pick IR template for objective
  ├─ compile IR
  ├─ execute graph
  │   ├─ plan → research → edit → human_gate (auto-approve in mock) → test → critic
  │   └─ critic FAIL → replan → loop
  ├─ produce final outcome (markdown)
  └─ emit trace events
```

## Flow 2 — Create a custom pack

```
user fills neuronium_agent/packs/templates/workflow_pack_template.md
  ▼
neuronium-agent packs generate template.md --out packs/my.yaml --id my
  ▼
neuronium-agent packs validate packs/my.yaml
  ▼
neuronium-agent packs install packs/my.yaml
  ▼
neuronium-agent objective run "<phrase>" --pack my --mock
```

## Flow 3 — Inspect a pack

```
neuronium-agent packs list      → table
neuronium-agent packs show <id> → YAML dump
```
