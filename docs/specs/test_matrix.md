# Neuronium — Test Matrix

Every requirement maps to at least one test. Tests run in mock mode only.

## Unit tests

| ID | Subject | Requirement |
| --- | --- | --- |
| NR-UT-IR-001 | Program loads from YAML | NR-F-001 |
| NR-UT-IR-002 | Program rejects invalid node refs | NR-F-002 |
| NR-UT-IR-003 | Conditional edges parsed | NR-F-002 |
| NR-UT-AGENT-001 | AgentDefinition schema | NR-FR-300 |
| NR-UT-AGENT-002 | AgentInstance creation | NR-FR-301, NR-FR-303 |
| NR-UT-AGENT-003 | Agent-specific permission | NR-FR-306 |
| NR-UT-AGENT-004 | Agent-specific context budget | NR-FR-308 |
| NR-UT-AGENT-005 | Agent output contract validation | NR-FR-309 |
| NR-UT-PACK-001 | Pack DSL parser | NR-FR-321 |
| NR-UT-PACK-002 | Pack validator | NR-FR-322 |
| NR-UT-PACK-003 | Pack compiler | NR-FR-323 |
| NR-UT-PACK-004 | Pack version compatibility | NR-FR-PACK-040, NR-FR-PACK-041 |
| NR-UT-POLICY-001 | Tool permission resolution | NR-F-070 |
| NR-UT-POLICY-002 | Critical risk denial | NR-F-072 |
| NR-UT-TRACE-001 | Trace sequence increments | NR-F-093, NR-F-094 |
| NR-UT-TRACE-002 | Trace redacts secrets | NR-FR-SEC-002 |
| NR-UT-CFG-001 | Config hierarchy resolution | NR-FR-CFG-001..007 |
| NR-UT-GRAG-001 | Mock GraphRAG retrieval | NR-F-080, NR-FR-GRAG-001 |

## Integration tests

| ID | Subject | Requirement |
| --- | --- | --- |
| NR-IT-AGENT-001 | Dynamic factory creates task-specific agents | NR-FR-304 |
| NR-IT-AGENT-002 | Agent handoff recorded in trace | NR-FR-310, NR-FR-311 |
| NR-IT-PACK-001 | Coding pack compiles | NR-FR-323, NR-FR-330 |
| NR-IT-PACK-002 | Marketing pack validates | NR-FR-331 |
| NR-IT-PACK-003 | HR pack validates | NR-FR-331 |
| NR-IT-IR-001 | IR builder produces runnable graph | NR-F-004 |
| NR-IT-RUN-001 | Critic gate triggers replan | NR-F-021, NR-F-023 |
| NR-IT-RUN-002 | Human gate blocks until approval | NR-F-008 |

## End-to-end tests

| ID | Subject | Requirement |
| --- | --- | --- |
| NR-E2E-AGENT-001 | Complex objective uses planner, executor, critic, recovery | NR-F-032..033 |
| NR-E2E-PACK-001 | Coding objective end-to-end | NR-FR-330 |
| NR-E2E-PACK-002 | Pack generator from markdown | NR-FR-328 |

## GraphRAG eval

| ID | Subject |
| --- | --- |
| NR-GRAG-EVAL-001 | golden retrieval fixture |
| NR-GRAG-EVAL-002 | entity linking fixture |
| NR-GRAG-EVAL-003 | artifact preservation fixture |
