# Anthropic Provider — Claude Opus 4.7

## Goal

Implement a real `ModelProvider` that calls the Anthropic API so Neuronium can
serve as an Opus-4.7-powered alternative to coding-style assistants — with the
same governance (per-agent tools, permission policy, human gates), hierarchical
planning, RAG-Anything memory backend, trace and replay infrastructure.

## Defaults (set by the official Claude API skill)

| Aspect | Value | Why |
| --- | --- | --- |
| Model | `claude-opus-4-7` | The most capable Claude model; default per skill. |
| `thinking` | `{type: "adaptive", display: "summarized"}` | Adaptive is the only on-mode for Opus 4.7; `display: "summarized"` is required to surface reasoning into the trace (silent default is `"omitted"`). |
| Sampling | none | `temperature`, `top_p`, `top_k` are removed on Opus 4.7 (400). |
| `effort` | per role | Coding-agentic → `xhigh`; intelligence-sensitive → `high`; cost/latency → `medium`/`low`. |
| Streaming | always (under the hood) | Uses `client.messages.stream().get_final_message()` to avoid SDK HTTP timeouts on long thinking + tool-use loops. |
| Prompt caching | enabled | Top-level `cache_control: {type: "ephemeral"}` on the last system block. Stable prompt + agent goal/contract caches; volatile state lives in the user message after the breakpoint. |
| Output contract | `output_config.format = {type: "json_schema", schema: ...}` | When an agent declares an `OutputContract`, the provider converts it into a JSON schema for structured output. |
| Tool use | `tools` + executor closure | When `tool_use` is emitted the provider routes the call back to Neuronium's `PolicyEngine` + `ToolRegistry` and iterates until `end_turn`. |

## Requirements

- **NR-FR-PROV-001** Provide an `AnthropicProvider` implementing `ModelProvider`.
- **NR-FR-PROV-002** Default to `claude-opus-4-7`.
- **NR-FR-PROV-003** Send `thinking={type: "adaptive", display: "summarized"}` for all reasoning-eligible roles.
- **NR-FR-PROV-004** Never send `temperature`, `top_p`, `top_k`.
- **NR-FR-PROV-005** Route role → `effort` per the table above.
- **NR-FR-PROV-006** Stream every API call via `messages.stream().get_final_message()`.
- **NR-FR-PROV-007** Apply prompt caching by default via `cache_control: {type: "ephemeral"}` on the last system block.
- **NR-FR-PROV-008** Convert each agent's `OutputContract` into a JSON-schema and request it via `output_config.format`.
- **NR-FR-PROV-009** Run a tool-use loop with an injected executor; surface `tool_use_id` round-trip, `is_error` on executor exceptions, and a hard iteration cap.
- **NR-FR-PROV-010** Accumulate `usage` across iterations and expose `thinking_summary` in `ModelResponse`.
- **NR-FR-PROV-011** Be optional: when `anthropic` is not installed, the module remains importable and `ready=False`.
- **NR-FR-PROV-012** Accept a pre-built `client` (or `client_factory`) for test injection.
- **NR-FR-PROV-013** Surface installation status via `doctor`.
- **NR-FR-PROV-014** Expose provider selection through CLI: `--provider`, `--provider-model`, `--provider-max-tokens`.
- **NR-FR-PROV-015** Emit a `provider.selected` trace event with the resolved provider name and non-secret options.

## Runtime integration

`Runtime.run_model` now passes:

- `tools` — Anthropic-shaped specs built from the agent's allowed tools (each `<server>.<tool>` ref becomes `<server>__<tool>` because tool names use `[a-zA-Z0-9_-]` only).
- `tool_executor` — closure that, on each tool call from the model:
  1. Resolves `PolicyEngine.resolve(ref, agent_id)`.
  2. On `deny` → emits `tool.denied`, raises `PermissionError` (becomes `is_error` tool result).
  3. On `require_approval` → invokes the human gate (auto-approves in mock mode).
  4. On `allow`/approved → invokes `ToolRegistry.call(ref, **input)` and emits `tool.completed` with `via: "model_loop"`.
- `output_contract` — the agent's contract for JSON schema conversion.
- `trace_emit` — adapter that lets the provider stream `model.token` / `model.tool_call` events into the run trace.

This means the **same** governance, audit trail, and human-approval policy that applied to IR `ToolNode`s now applies to mid-reasoning tool calls.

## Architecture

```
ObjectiveRunner
   ↓
build_default_runtime(provider="anthropic", provider_options={...})
   ↓
default_registry → ModelRegistry
   ↓
AnthropicProvider (with client / client_factory / default-built client)
   ↓
client.messages.stream(...)  ← Anthropic SDK
   ↓
tool_use → Runtime tool_executor → PolicyEngine + HumanGate + ToolRegistry
   ↓
final JSON → AgentInstance.OutputContract validation → state update
```

## CLI

```bash
neuronium-agent doctor   # prints anthropic install + ANTHROPIC_API_KEY status

neuronium-agent objective run "<text>" \
    --pack coding \
    --provider anthropic \
    --provider-model claude-opus-4-7 \
    --provider-max-tokens 16000

neuronium-agent code "fix this bug" --provider anthropic
```

`ANTHROPIC_API_KEY` must be set unless a client is injected programmatically.

## Tests

- `tests/unit/test_anthropic_provider.py` (13 tests):
  - graceful fallback when `anthropic` is not installed
  - request shape: model, no sampling params, adaptive thinking with summarized display, `effort` per role, `cache_control` on last system block, state outside the cache
  - structured-output JSON schema derived from `OutputContract`
  - tool-use loop drives executor; second call carries the `tool_result`
  - executor errors propagate as `is_error: true`
  - tool-use without executor returns the original stop reason
  - iteration cap prevents infinite tool loops
  - thinking blocks accumulate into `ModelResponse.thinking_summary`
  - JSON parser handles fenced ` ```json `, prose with embedded JSON, and plain text
  - `usage` accumulates across loop iterations

- `tests/integration/test_anthropic_runner.py` (1 test):
  - Coding pack runs end-to-end with `--provider anthropic` using a per-agent
    scripted fake client; `provider.selected` event is emitted; full HTN +
    critic + replan path reaches `verdict: PASS`.

No test requires the `anthropic` package, an API key, or network access.

## Definition of Done

- ✅ Provider returns a structured `ModelResponse` for every Neuronium agent role.
- ✅ Trace records `provider.selected`; tokens / thinking / tool calls can stream.
- ✅ Tool-use loop respects per-agent permission policy + human gates.
- ✅ `OutputContract` enforced as JSON schema.
- ✅ Doctor surfaces installation state.
- ✅ Mock provider remains the default for CI and `--mock`.
