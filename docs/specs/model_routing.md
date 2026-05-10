# Model Routing

Neuronium ships three real providers plus the deterministic mock used in CI:

| Provider | Default model | Best for | Optional dep | Env var |
| --- | --- | --- | --- | --- |
| `mock` | — | tests, `--mock` runs, deterministic CI | none | — |
| `anthropic` | `claude-opus-4-7` | hard reasoning, coding/agentic, critic, planner, vision (high-res) | `pip install 'neuronium-agent[anthropic]'` | `ANTHROPIC_API_KEY` |
| `openai` | `gpt-4o` | structured extraction, function-calling-heavy work, vision, cheap mass volume | `pip install 'neuronium-agent[openai]'` | `OPENAI_API_KEY` |
| `gemini` | `gemini-2.5-pro` | very long context (1M+ tokens), multimodal video / audio, retrieval over big repos | `pip install 'neuronium-agent[gemini]'` | `GEMINI_API_KEY` |

## Picking a provider per agent

Two surfaces:

### 1. Pack DSL — per-agent `model: <provider>:<model_id>`

```yaml
agents:
  - id: code_planner
    role: planner
    model: anthropic:claude-opus-4-7    # hard reasoning + adaptive thinking

  - id: long_context_reader
    role: researcher
    model: gemini:2.5-pro               # 1M-token reads of the whole repo

  - id: copywriter
    role: executor
    model: openai:gpt-4o-mini           # cheap text

  - id: vision_critic
    role: critic
    model: openai:gpt-4o                # OCR + screenshots

  - id: code_reviewer
    role: critic
    model: anthropic:claude-opus-4-7
```

The `ModelRegistry` parses `<provider>:<model_id>` and routes the call to the
right provider, temporarily overriding its `model_id` for the duration of the
call. Plain alias strings (`smart`, `fast`, `critic`, `vision`,
`long_context`) still work — they go through the alias map.

### 2. CLI — pick a single provider for the whole run

```bash
neuronium-agent objective run "..." --provider anthropic
neuronium-agent objective run "..." --provider openai --provider-model gpt-4o
neuronium-agent objective run "..." --provider gemini --provider-model gemini-2.5-flash
```

For mixed-provider runs use `--provider multi` and let the pack drive routing
through `model: provider:id` per agent.

## Role-to-effort map (Anthropic)

The Anthropic provider routes role → `output_config.effort` per the official
Claude API skill:

| Role | Effort | Why |
| --- | --- | --- |
| `planner`, `critic`, `researcher`, `designer` | `xhigh` | Coding/agentic and intelligence-sensitive — `xhigh` is the default in Claude Code. |
| `executor`, `recovery`, `curator` | `high` | Recommended minimum for most intelligence-sensitive work. |
| `fast` | `low` | Latency-sensitive paths; thinking disabled. |

OpenAI and Gemini don't expose `effort` directly, so role → max output tokens
or temperature can be overridden via `provider_options`.

## When to pick what (model card)

- **Hard coding / agentic loops / large refactors** → `anthropic:claude-opus-4-7` (xhigh effort, adaptive thinking).
- **Cheap, high-volume classification or text generation** → `openai:gpt-4o-mini`.
- **Long-context reading (whole repo, big PDFs, books)** → `gemini:2.5-pro` (1M context).
- **Multimodal video / audio** → `gemini:2.5-pro`.
- **Vision OCR / screenshots / charts** → `openai:gpt-4o` or `anthropic:claude-opus-4-7` (Opus 4.7 has high-res vision up to 2576px long edge).
- **Strict JSON extraction at scale** → `openai:gpt-4o` with `response_format: json_schema`.
- **Reasoning-heavy critic / second-opinion** → `anthropic:claude-opus-4-7`.

## Credential-less development (`mock_mode`)

While developing flows, packs, or provider routing without real API keys,
every real provider accepts `mock_mode=True`:

- Construction succeeds with no `*_API_KEY` env var.
- `provider.ready` is `True`.
- `generate()` delegates to `MockModelProvider`, returning the same
  deterministic agent-keyed outputs the test suite uses.
- Trace still records the chosen provider name (`anthropic` / `openai` /
  `gemini`) and the simulated model id, so multi-provider routing,
  per-agent `model:` overrides, and `provider.selected` events all behave
  identically — they just run against the simulator.

CLI:

```bash
neuronium-agent objective run "..." --provider anthropic --provider-mock
neuronium-agent code "..." --repl --provider openai --provider-mock
```

Drop `--provider-mock` once a real key arrives — the rest of the call is the
same.

## Configuration discovery

```bash
neuronium-agent doctor              # which providers are installed + key status
neuronium-agent providers list      # available + which alias maps to which
```

## Definition of Done

- ✅ `<provider>:<model_id>` parsing in `ModelRegistry`.
- ✅ `OpenAIProvider`, `GeminiProvider` adapters with optional deps + injected-client tests.
- ✅ Aliases `vision` and `long_context` registered alongside `fast`/`smart`/`cheap`/`critic`.
- ✅ `default_registry(provider="multi")` constructs all installed providers.
- ✅ Doctor reports installation + API-key state for each provider.
