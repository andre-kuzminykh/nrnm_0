# Test Strategy

## Principles

1. **Mock-only in CI.** No test relies on network or LLM. The deterministic mock provider and mock MCP cover every path needed for green CI.
2. **Requirement traceability.** Every NR-FR-* requirement maps to at least one test ID in `test_matrix.md`.
3. **Golden fixtures.** GraphRAG retrieval and pack DSL parsing rely on fixed inputs for stable assertions.
4. **Layered testing.** Unit tests for pure logic (IR, packs, policy, trace); integration tests for the runtime (gates, replan); e2e tests for the CLI.
5. **Determinism.** Mock-mode runs must produce identical IR and event sequences modulo timestamps.

## Test layout

```
tests/
  conftest.py
  unit/
    test_ir.py
    test_agents.py
    test_packs.py
    test_policy.py
    test_trace.py
    test_config.py
    test_graphrag.py
    test_generator.py
  integration/
    test_runner.py
    test_human_gate.py
  e2e/
    test_cli.py
```

## Definition of done for a feature

- Spec entry + requirement ID.
- Tests (unit + integration where applicable).
- Implementation passing those tests.
- README touch-points if user-facing.
