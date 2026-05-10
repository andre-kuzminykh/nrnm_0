# Neuronium — Functional Requirements

## Agent system

- **NR-FR-300** The system shall define `AgentDefinition`.
- **NR-FR-301** The system shall define `AgentInstance`.
- **NR-FR-302** `AgentDefinition` shall include `id`, `role`, `goal`, `prompt_ref`, `model`, `tools`, `permissions`, `skills`, `memory_scope`, `context_budget`, `output_contract`, and `acceptance_criteria`.
- **NR-FR-303** The system shall create `AgentInstance` objects per run.
- **NR-FR-304** The system shall support task-specific agent creation through the Dynamic Agent Factory.
- **NR-FR-305** The system shall support agent-specific tools.
- **NR-FR-306** The system shall support agent-specific permissions.
- **NR-FR-307** The system shall support agent-specific memory scope.
- **NR-FR-308** The system shall support agent-specific context budget.
- **NR-FR-309** The system shall validate agent output contracts.
- **NR-FR-310** The system shall record `agent_created`, `agent_started`, `agent_completed`, `agent_failed`, and `agent_handoff` events.
- **NR-FR-311** The system shall support an agent handoff protocol.
- **NR-FR-312** The system shall represent agents in Workflow IR when they own nodes.

## Applied Workflow Packs

- **NR-FR-320** The system shall define a Workflow Pack DSL.
- **NR-FR-321** The system shall parse Workflow Pack YAML.
- **NR-FR-322** The system shall validate Workflow Pack structure.
- **NR-FR-323** The system shall compile pack definitions into agent definitions, tool policies, workflows, and tests.
- **NR-FR-324** The system shall register installed workflow packs.
- **NR-FR-325** The system shall select workflow packs by explicit `--pack` argument.
- **NR-FR-326** The system shall suggest workflow packs based on objective text.
- **NR-FR-327** The system shall support custom workflow packs.
- **NR-FR-328** The system shall generate a draft workflow pack from the simple markdown template.
- **NR-FR-329** The system shall test workflow packs with mock providers.
- **NR-FR-330** The system shall include the coding pack as the first implemented pack.
- **NR-FR-331** The system shall include marketing and HR pack fixtures.

## Pack versioning

- **NR-FR-PACK-040** The system shall validate workflow pack `schema_version`.
- **NR-FR-PACK-041** The system shall validate `compatible_neuronium` range.
- **NR-FR-PACK-042** The system shall support pack compatibility checks.
- **NR-FR-PACK-043** The system shall record pack version in trace.
- **NR-FR-PACK-044** The system shall support pack lock metadata for reproducible runs.

## Pack scaffolding and registry

- **NR-FR-PACK-050** The system shall scaffold a new workflow pack.
- **NR-FR-PACK-051** Scaffolds shall include agents, tools, workflows, quality gates, and tests.
- **NR-FR-PACK-052** Scaffolds shall include prompt-file placeholders.
- **NR-FR-PACK-053** Scaffolds shall include mock tests.
- **NR-FR-PACK-060** The system shall maintain an installed pack registry.
- **NR-FR-PACK-061** The system shall validate installed packs.
- **NR-FR-PACK-062** The system shall test installed packs in mock mode.
- **NR-FR-PACK-063** The system shall expose pack metadata through the CLI.
- **NR-FR-PACK-064** The system shall support built-in and user-installed packs.

## Interactive coding mode

- **NR-FR-CODE-001** The system shall inspect git status before file modifications.
- **NR-FR-CODE-002** The system shall create a snapshot before applying edits.
- **NR-FR-CODE-003** The system shall show a diff before applying high-risk edits.
- **NR-FR-CODE-004** The system shall support revert / unrevert for coding changes.
- **NR-FR-CODE-005** The system shall summarize git diff after a coding run.
- **NR-FR-CODE-006** The system shall detect common test commands.
- **NR-FR-CODE-007** The system shall deny destructive shell commands by default.
- **NR-FR-CODE-008** The system shall require approval for `shell.run` in coding pack.
- **NR-FR-CODE-009** The system shall warn on a dirty working tree.
- **NR-FR-CODE-010** The system shall record changed files in the final outcome.

## Security and redaction

- **NR-FR-SEC-001** The system shall redact API keys, tokens, passwords, and secrets from logs.
- **NR-FR-SEC-002** The system shall redact secrets from trace events.
- **NR-FR-SEC-003** The system shall redact secrets from exported replay bundles.
- **NR-FR-SEC-004** The system shall never store raw provider credentials in artifacts.
- **NR-FR-SEC-005** The system shall support secret-field detection by key name and pattern.
- **NR-FR-SEC-006** `doctor` shall warn if unsafe secret exposure is detected.

## MCP lifecycle

- **NR-FR-MCP-001** Support local stdio MCP servers.
- **NR-FR-MCP-002** Support remote HTTP MCP servers where possible.
- **NR-FR-MCP-003** Discover MCP tools and schemas.
- **NR-FR-MCP-004** Namespace MCP tools by server name.
- **NR-FR-MCP-005** Health-check MCP servers.
- **NR-FR-MCP-006** Support degraded MCP lifecycle state.
- **NR-FR-MCP-007** Continue startup if optional MCP servers fail.
- **NR-FR-MCP-008** Fail startup if required MCP servers fail.
- **NR-FR-MCP-009** Record MCP tool schema version in trace.

## GraphRAG evaluation

- **NR-FR-GRAG-001** Support golden GraphRAG retrieval fixtures.
- **NR-FR-GRAG-002** Evaluate retrieval precision in tests.
- **NR-FR-GRAG-003** Evaluate entity-linking quality.
- **NR-FR-GRAG-004** Evaluate artifact-reference preservation.
- **NR-FR-GRAG-005** Emit retrieval diagnostics.

## RAG-Anything integration

- **NR-FR-GRAG-010** Provide a pluggable `MemoryBackend` protocol with `retrieve`, `ingest`, `write_back`, `diagnostics`.
- **NR-FR-GRAG-011** Register `mock` and `raganything` backends by default.
- **NR-FR-GRAG-012** Continue to function (mock fallback) when `raganything` is not installed.
- **NR-FR-GRAG-013** Emit `memory.initialized`, `memory.retrieved`, `memory.retrieval_failed` events with `backend` and `ready` fields.
- **NR-FR-GRAG-014** Allow injecting a custom RAG-Anything client / client_factory for testing and deployment.
- **NR-FR-GRAG-015** Expose CLI commands `memory backends`, `memory diagnostics`, `memory ingest`, `memory query`.
- **NR-FR-GRAG-016** Accept memory backend selection via CLI on `objective run` and `code`.
- **NR-FR-GRAG-017** Report `raganything` install status from `doctor`.

## Configuration

- **NR-FR-CFG-001** Built-in defaults shall always be available.
- **NR-FR-CFG-002** Global config at `~/.neuronium/config.yaml` overrides defaults.
- **NR-FR-CFG-003** Project config `<project>/.neuronium/config.yaml` overrides global.
- **NR-FR-CFG-004** Local config `<project>/.neuronium/config.local.yaml` overrides project.
- **NR-FR-CFG-005** Environment variables `NEURONIUM_*` override local.
- **NR-FR-CFG-006** CLI flags override env vars.
- **NR-FR-CFG-007** Session overrides win.

## Non-functional pointers

See `requirements_non_functional.md`.
