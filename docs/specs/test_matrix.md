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

## Hierarchical planning

| ID | Subject | Requirement |
| --- | --- | --- |
| NR-UT-PLAN-001 | HTN planner expands compound into primitives | NR-FR-PLAN-001 |
| NR-UT-PLAN-002 | Recursive decomposition keeps order and depth | NR-FR-PLAN-001 |
| NR-UT-PLAN-003 | First applicable method wins | NR-FR-PLAN-003 |
| NR-UT-PLAN-004 | Cycle detection | NR-FR-PLAN-004 |
| NR-UT-PLAN-005 | Implicit plan from phases | NR-FR-PLAN-011 |
| NR-IT-PLAN-001 | plan.decomposed emitted with HTN payload | NR-FR-PLAN-009 |
| NR-IT-PLAN-002 | subplan.entered/completed balanced | NR-FR-PLAN-009 |
| NR-IT-PLAN-003 | Hierarchical replan picks sibling subplan | NR-FR-PLAN-010 |
| NR-IT-PLAN-004 | IR nodes carry task_path metadata | NR-FR-PLAN-008 |
| NR-IT-PLAN-005 | Implicit plan fallback | NR-FR-PLAN-011 |

## Anthropic provider

| ID | Subject | Requirement |
| --- | --- | --- |
| NR-UT-ANTH-001 | Provider not ready without anthropic; generate raises | NR-FR-PROV-011 |
| NR-UT-ANTH-002 | Request shape: model, no sampling, adaptive thinking + summarized, effort per role, cache_control | NR-FR-PROV-002..007 |
| NR-UT-ANTH-003 | Tool-use loop drives executor; tool_result round-trips | NR-FR-PROV-009 |
| NR-UT-ANTH-004 | Executor error → is_error tool_result | NR-FR-PROV-009 |
| NR-UT-ANTH-005 | Tool iteration cap | NR-FR-PROV-009 |
| NR-UT-ANTH-006 | Thinking blocks accumulate into thinking_summary | NR-FR-PROV-010 |
| NR-UT-ANTH-007 | JSON parser handles fenced / prose / fallback text | NR-FR-PROV-008 |
| NR-UT-ANTH-008 | Usage accumulates across iterations | NR-FR-PROV-010 |
| NR-IT-ANTH-001 | Coding pack runs end-to-end with injected anthropic fake | NR-FR-PROV-014, NR-FR-PROV-015 |

## Memory / RAG-Anything

| ID | Subject | Requirement |
| --- | --- | --- |
| NR-UT-MEM-001 | Backend registry exposes mock and raganything | NR-FR-GRAG-010, NR-FR-GRAG-011 |
| NR-UT-MEM-002 | Graceful fallback when raganything missing | NR-FR-GRAG-012 |
| NR-UT-MEM-003 | Adapter dispatches path → process_document_complete and text → insert_content_list | NR-FR-GRAG-014 |
| NR-UT-MEM-004 | Adapter retrieval coerces upstream str/dict/None | NR-FR-GRAG-014 |
| NR-UT-MEM-005 | MockGraphRAG ingest writes searchable entities | NR-F-089 |
| NR-IT-MEM-001 | Runtime selects memory backend from config and emits memory.initialized | NR-FR-GRAG-013, NR-FR-GRAG-016 |
| NR-IT-MEM-002 | Runtime emits memory.retrieval_failed when backend raises | NR-FR-GRAG-013 |
| NR-E2E-MEM-001 | CLI memory diagnostics returns JSON | NR-FR-GRAG-015 |
| NR-E2E-MEM-002 | CLI memory ingest + query roundtrip on mock backend | NR-FR-GRAG-015 |
