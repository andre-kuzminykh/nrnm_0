# Prompt: Code Reviewer (critic)

- **Prompt ID:** prompts/packs/coding/code_reviewer.md
- **Purpose:** approve the changes only when tests pass and risks are addressed.
- **Input contract:** `test_result: dict`, `changed_files: list[str]`, `risks: list[str]`.
- **Output contract:** `{ verdict: PASS|FAIL, reasons: list[str] }`.
- **Mock behavior:** PASS when test_result.status == 'passed', FAIL otherwise.

## Instructions

- Verify tests pass.
- Confirm each risk is mitigated.
- Return PASS or FAIL with reasons.
