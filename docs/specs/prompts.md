# Prompts

All prompts live as standalone markdown files under `prompts/`. Each has:

- **Prompt ID** — `prompts/...` relative path used as the stable reference.
- **Purpose** — one-line summary.
- **Input contract** — what state keys the prompt reads.
- **Output contract** — what JSON shape the agent must return.
- **Validation rules** — at minimum the output contract `required` fields.
- **Mock behavior** — what the deterministic mock provider returns.
- **Related requirements** — NR-FR-* and NR-F-* IDs.
- **Related tests** — NR-UT/IT/E2E-* IDs.

Index:

| Prompt | Path |
| --- | --- |
| Objective Intake | `prompts/objective_intake.md` |
| Workflow IR Builder | `prompts/workflow_ir_builder.md` |
| Final Outcome | `prompts/final_outcome.md` |
| Generic Planner | `prompts/agents/planner.md` |
| Generic Executor | `prompts/agents/executor.md` |
| Generic Critic | `prompts/agents/critic.md` |
| Recovery Agent | `prompts/agents/recovery_agent.md` |
| Coding Planner | `prompts/packs/coding/coding_planner.md` |
| Code Researcher | `prompts/packs/coding/code_researcher.md` |
| Code Editor | `prompts/packs/coding/code_editor.md` |
| Test Runner | `prompts/packs/coding/test_runner.md` |
| Code Reviewer | `prompts/packs/coding/code_reviewer.md` |
| Marketing prompts | `prompts/packs/marketing/*.md` |
| HR prompts | `prompts/packs/hr/*.md` |
