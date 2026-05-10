# AI Services

| AI service | Module | Provider | Output |
| --- | --- | --- | --- |
| Planner | model node + `prompts/agents/planner.md` (or pack-specific) | role `smart` → mock | `{ plan, files_to_inspect, risks }` |
| Researcher | model node + pack-specific prompt | role `smart` → mock | `{ root_cause, snippets }` |
| Editor | model node + pack-specific prompt | role `smart` → mock | `{ patch_summary, changed_files, proposed_patch }` |
| Test runner | model node | role `fast` → mock | `{ test_result }` |
| Critic | critic node + pack-specific prompt | role `critic` → mock | `{ verdict, reasons }` |
| Marketing agents | model nodes | role `smart` → mock | per-agent contracts |
| HR agents | model nodes | role `smart` → mock | per-agent contracts |

All AI calls in v0.1 go through the mock provider for deterministic CI. Swapping in a real provider (e.g. Anthropic, OpenAI) is done by registering a new `ModelProvider` on the `ModelRegistry` and re-aliasing roles.
