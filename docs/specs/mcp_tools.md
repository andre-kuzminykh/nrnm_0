# MCP Tools

## v0.1 — mock MCP

`MockMCP` registers a deterministic set of namespaced tools onto the tool
registry: `fs.read`, `fs.write`, `fs.edit`, `patch.apply`, `grep.search`,
`glob.search`, `git.status`, `git.diff`, `git.branch`, `shell.run`, `test.run`
(coding), plus marketing and HR analogs. All tools return predictable shapes.

## v0.2 — real MCP lifecycle

- **Local stdio servers.** Spawn child processes; capture tool schemas; namespace by server name.
- **Remote HTTP servers.** Discover schemas via JSON-RPC over HTTP.
- **Health checks.** Periodic ping; degraded state if a non-required server fails.
- **Required vs optional.** Required servers fail startup; optional servers are reported degraded but allow runs to continue.
- **Schema version tracking.** Each tool call's trace includes `tool_schema_version`.

## Governance contract (already in v0.1)

Every tool call is gated by `PolicyEngine.resolve(tool_ref, agent_id)`:

| Decision | Behavior |
| --- | --- |
| `allow` | call proceeds; `tool.completed` event |
| `deny` | call refused; `tool.denied` event; `PermissionError` |
| `require_approval` | gate triggers; if approved, `tool.approved` event; else `tool.denied`. |

In `--mock` mode, the gate auto-approves to keep tests deterministic.
