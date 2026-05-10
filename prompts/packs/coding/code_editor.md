# Prompt: Code Editor

- **Prompt ID:** prompts/packs/coding/code_editor.md
- **Purpose:** propose a minimal patch that addresses the root cause.
- **Input contract:** `root_cause: str`, `snippets: list`, `files_to_inspect: list[str]`.
- **Output contract:** `{ patch_summary: str, changed_files: list[str], proposed_patch: str }`.
- **Validation:** changed_files non-empty.
- **Mock behavior:** returns a fixed patch summary.

## Instructions

1. Edit only the smallest set of lines needed.
2. Do not introduce new dependencies.
3. Output the unified diff plus a short summary.
