# LangGraph Backend

Neuronium uses an in-process LangGraph-compatible backend in v0.1. The same
`CompiledGraph` interface will be backed by real LangGraph in v0.2 without
changing public contracts.

## Compatibility contract

A `CompiledGraph` exposes `run(state, runtime)` and returns `{final_state, visited, replans}`.

Runtime callbacks the graph requires (the same shape any LangGraph compiler must produce):

```python
runtime.run_model(node, state)        -> dict
runtime.run_tool(node, args, state)   -> dict
runtime.run_operator(node, args, state) -> dict
runtime.run_human_gate(node, state)   -> dict
runtime.run_critic(node, state)       -> dict
runtime.run_recovery(node, state)     -> dict
runtime.run_terminal(node, state)     -> dict
runtime.events.emit(kind, payload)    -> None
```

## Conditional edges

The IR's `Edge.condition` is a simple boolean expression evaluated over `state` with `eval` and an empty `__builtins__`. Backends should reproduce equivalent semantics.

## Replan reroute

If a CriticNode produces `verdict == 'FAIL'`, the backend reroutes execution:

- to the first outgoing edge whose condition contains `'FAIL'`, if any;
- else to the program start node (in-process backend) or to a designated `replan` node (future LangGraph backend).

## Trace mapping

Every node produces `node.started`, `node.completed`, `node.failed`, plus the
agent / tool / critic / human / outcome events listed in `architecture.md`.
The contract is stable; only the underlying executor changes between backends.
