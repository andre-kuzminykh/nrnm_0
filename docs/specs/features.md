# Neuronium — Feature Catalog

Each feature has a stable ID, a name, description, primary users, and links to requirements/tests. Status reflects the v0.1 vertical slice.

Legend: **MVP** implemented in v0.1 (mock mode), **SPEC** specified only, **PLAN** deferred.

## Runtime core

| ID | Name | Status |
| --- | --- | --- |
| NR-F-001 | Workflow IR import | MVP |
| NR-F-002 | Workflow IR validation | MVP |
| NR-F-003 | LangGraph-compatible backend (with in-process fallback) | MVP |
| NR-F-004 | Workflow IR → graph compiler | MVP |
| NR-F-005 | Model node execution | MVP |
| NR-F-006 | Tool node execution | MVP |
| NR-F-007 | Operator node execution | MVP |
| NR-F-008 | Human gate / interrupt handling | MVP |
| NR-F-009 | Trace and audit recording | MVP |
| NR-F-010 | Replay support | SPEC |

## Super Agent intelligence

| ID | Name | Status |
| --- | --- | --- |
| NR-F-011 | Objective intake | MVP |
| NR-F-012 | Objective clarification | SPEC |
| NR-F-013 | GraphRAG context retrieval | MVP (mock) |
| NR-F-014 | Context budget manager | MVP |
| NR-F-015 | Planning service | MVP |
| NR-F-016 | Task decomposition | MVP |
| NR-F-017 | Dynamic Workflow IR builder | MVP |
| NR-F-018 | Dynamic Agent Factory | MVP |
| NR-F-019 | Task-specific subagents | MVP |
| NR-F-020 | MCP tool selection | MVP |
| NR-F-021 | Critic-based control | MVP |
| NR-F-022 | Commitment tracking | MVP |
| NR-F-023 | Adaptive replan | MVP |
| NR-F-024 | Failure classification | MVP |
| NR-F-025 | Recovery strategy selection | MVP |
| NR-F-026 | Final outcome synthesis | MVP |
| NR-F-027 | Evidence and artifact linking | MVP |

## Agent system

| ID | Name | Status |
| --- | --- | --- |
| NR-F-030 | Agent Definition | MVP |
| NR-F-031 | Agent Instance | MVP |
| NR-F-032 | Dynamic Agent Factory | MVP |
| NR-F-033 | Task-specific Agent Team | MVP |
| NR-F-034 | Agent-specific prompts | MVP |
| NR-F-035 | Agent-specific tools | MVP |
| NR-F-036 | Agent-specific permissions | MVP |
| NR-F-037 | Agent-specific memory scope | MVP |
| NR-F-038 | Agent-specific context budget | MVP |
| NR-F-039 | Agent output contracts | MVP |
| NR-F-040 | Agent handoff protocol | MVP |
| NR-F-041 | Agent trace events | MVP |
| NR-F-042 | Agent registry | MVP |
| NR-F-043 | Skill registry | SPEC |
| NR-F-044 | Effective prompt composition | MVP |
| NR-F-045 | Custom markdown agents | MVP |

## Applied workflow packs

| ID | Name | Status |
| --- | --- | --- |
| NR-F-050 | Applied Workflow Pack DSL | MVP |
| NR-F-051 | Workflow Pack Registry | MVP |
| NR-F-052 | Workflow Pack Generator (from markdown) | MVP |
| NR-F-053 | Workflow Pack Validator | MVP |
| NR-F-054 | Workflow Pack Installation | MVP |
| NR-F-055 | Workflow Pack Runtime Binding | MVP |
| NR-F-056 | Workflow Pack Test Harness | MVP |
| NR-F-057 | Coding Workflow Pack | MVP |
| NR-F-058 | Marketing Workflow Pack (fixture) | MVP |
| NR-F-059 | HR Workflow Pack (fixture) | MVP |
| NR-F-060 | Sales Workflow Pack | PLAN |
| NR-F-061 | Consulting Workflow Pack | PLAN |
| NR-F-062 | Custom Workflow Pack | MVP |

## Runtime governance

| ID | Name | Status |
| --- | --- | --- |
| NR-F-070 | Tool permission modes | MVP |
| NR-F-071 | Tool approval policies | MVP |
| NR-F-072 | Tool risk classes | MVP |
| NR-F-073 | Human control API | MVP |
| NR-F-074 | Policy explainability | MVP |
| NR-F-075 | Session-scoped permission overrides | MVP |
| NR-F-076 | Permission prompt UX contract | SPEC |

## Memory and context

| ID | Name | Status |
| --- | --- | --- |
| NR-F-080 | GraphRAG memory store | MVP (mock + RAG-Anything adapter) |
| NR-F-081 | Entity and relationship extraction | SPEC |
| NR-F-082 | Artifact graph | MVP |
| NR-F-083 | Prior run retrieval | MVP |
| NR-F-084 | Memory write-back | MVP |
| NR-F-085 | Context compaction | MVP |
| NR-F-086 | Trace-aware summarization | SPEC |
| NR-F-087 | Artifact-preserving summaries | SPEC |
| NR-F-088 | Pluggable memory backend protocol (mock / raganything / custom) | MVP |
| NR-F-089 | Document ingestion API (file + inline text) | MVP |

## Operational discipline

| ID | Name | Status |
| --- | --- | --- |
| NR-F-090 | Runtime lifecycle diagnostics | MVP |
| NR-F-091 | Preflight checks | MVP |
| NR-F-092 | Machine-readable status reports | MVP |
| NR-F-093 | Canonical runtime event schema | MVP |
| NR-F-094 | Event ordering and deduplication | MVP |
| NR-F-095 | Audience-specific event projections | SPEC |
| NR-F-096 | Compatibility harness | MVP |
| NR-F-097 | Golden trace fixtures | MVP |
| NR-F-098 | Mock provider parity tests | MVP |

## Models and providers

| ID | Name | Status |
| --- | --- | --- |
| NR-F-100 | Multi-provider model registry | MVP |
| NR-F-101 | Model aliases | MVP |
| NR-F-102 | Provider routing | MVP |
| NR-F-103 | Model roles: fast, smart, cheap, critic | MVP |

## MCP tools

| ID | Name | Status |
| --- | --- | --- |
| NR-F-110 | MCP-first tool registry | MVP |
| NR-F-111 | Tool / plugin lifecycle | MVP |
| NR-F-112 | Partial-success tool loading | MVP |
| NR-F-113 | Tool health checks | MVP |
| NR-F-114 | MCP tool execution governance | MVP |
| NR-F-115 | Mock MCP tools | MVP |

## Server and API

| ID | Name | Status |
| --- | --- | --- |
| NR-F-120 | Headless runtime server | SPEC |
| NR-F-121 | HTTP runtime API | SPEC |
| NR-F-122 | SSE event streaming | SPEC |
| NR-F-123 | OpenAPI specification | SPEC |
| NR-F-124 | SDK generation readiness | SPEC |
| NR-F-125 | Run / session model | MVP |
| NR-F-126 | Run / session list and inspect | MVP |
| NR-F-127 | Resume latest | SPEC |
| NR-F-128 | Run snapshot and revert | SPEC |
| NR-F-129 | Read-only shareable run view | SPEC |

## Input and artifacts

| ID | Name | Status |
| --- | --- | --- |
| NR-F-130 | Run input attachments | MVP |
| NR-F-131 | Artifact attachment references | MVP |
| NR-F-132 | Artifact store | MVP |
| NR-F-133 | Artifact rendering metadata | SPEC |

## Super Interface

| ID | Name | Status |
| --- | --- | --- |
| NR-F-140 | Super Interface specification | SPEC |
| NR-F-141 | Run monitor | SPEC |
| NR-F-142 | Agent graph viewer | SPEC |
| NR-F-143 | Human approval queue | SPEC |
| NR-F-144 | Trace viewer | SPEC |
| NR-F-145 | Artifact viewer | SPEC |
| NR-F-146 | Memory viewer | SPEC |
| NR-F-147 | Workflow Pack manager | SPEC |

## Coding pack features

| ID | Name | Status |
| --- | --- | --- |
| NR-CODE-F-001 | Repository analysis | MVP (mock) |
| NR-CODE-F-002 | File read / search | MVP |
| NR-CODE-F-003 | Safe file edit / patch apply | MVP (with approval) |
| NR-CODE-F-004 | Shell command execution through policy | MVP (with approval) |
| NR-CODE-F-005 | Test execution | MVP (mock runner) |
| NR-CODE-F-006 | Code review critic | MVP |
| NR-CODE-F-007 | Git status / diff summary | MVP |
| NR-CODE-F-008 | Context compaction for large repos | SPEC |
| NR-CODE-F-009 | Coding agent team | MVP |
| NR-CODE-F-010 | Coding final outcome | MVP |
