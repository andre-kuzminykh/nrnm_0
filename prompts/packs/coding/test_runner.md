# Prompt: Test Runner

- **Prompt ID:** prompts/packs/coding/test_runner.md
- **Purpose:** run the relevant tests and capture the result.
- **Input contract:** `repo_path: str`, `changed_files: list[str]`.
- **Output contract:** `{ test_result: { status: passed|failed, summary: str } }`.
- **Validation:** status is `passed` or `failed`.
- **Mock behavior:** returns `passed` for the first attempt unless fixtures override.

## Instructions

1. Decide which test command to run.
2. Run it via the test.run tool.
3. Capture pass/fail and a one-line summary.
