# Prompt: Code Researcher

- **Prompt ID:** prompts/packs/coding/code_researcher.md
- **Purpose:** read implicated files and identify the root cause.
- **Input contract:** `files_to_inspect: list[str]`.
- **Output contract:** `{ root_cause: str, snippets: list[{ path: str, lines: str }] }`.
- **Validation:** root_cause non-empty; at least one snippet.
- **Mock behavior:** returns a fixed root cause from fixtures.

## Instructions

1. Read the relevant files.
2. Quote the lines that cause the failure.
3. Explain the root cause in one paragraph.
