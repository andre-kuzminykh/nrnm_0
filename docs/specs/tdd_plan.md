# TDD Plan

## v0.1 (this release)

The vertical slice was built test-first for each subsystem:

1. IR models + validator → unit tests in `tests/unit/test_ir.py`.
2. Agent definitions / factory → unit tests in `tests/unit/test_agents.py`.
3. Pack DSL parser / validator / compiler → unit tests in `tests/unit/test_packs.py`.
4. Policy engine → unit tests in `tests/unit/test_policy.py`.
5. Trace + redaction → unit tests in `tests/unit/test_trace.py`.
6. Config hierarchy → unit tests in `tests/unit/test_config.py`.
7. GraphRAG retrieval → unit tests in `tests/unit/test_graphrag.py`.
8. Pack generator → unit tests in `tests/unit/test_generator.py`.
9. Objective Runner / replan / secret redaction in trace → integration tests in `tests/integration/test_runner.py`.
10. Human gate denial → `tests/integration/test_human_gate.py`.
11. CLI commands → e2e tests in `tests/e2e/test_cli.py`.

## v0.2 plan

- Compatibility harness golden traces.
- Real LangGraph backend parity tests.
- Real MCP local-stdio adapter integration tests.
- Real GraphRAG retrieval evaluation suite.
