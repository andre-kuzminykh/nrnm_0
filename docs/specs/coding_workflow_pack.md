# Coding Workflow Pack

The Coding Pack is the first applied workflow pack. It demonstrates how the
platform reproduces the value of Claude-Code / OpenCode while keeping coding as
**one pack** among others (marketing, HR, ...).

## Agents

| ID | Role | Tools | Required output |
| --- | --- | --- | --- |
| `code_planner` | planner | fs.read, grep.search, glob.search, git.status | plan, files_to_inspect, risks |
| `code_researcher` | researcher | fs.read, grep.search, glob.search, git.diff | root_cause, snippets |
| `code_editor` | executor | fs.read, fs.edit, patch.apply | patch_summary, changed_files |
| `test_runner` | executor | shell.run, test.run, fs.read | test_result |
| `code_reviewer` | critic | fs.read, git.diff | verdict, reasons |

## Workflows

- `fix_bug_workflow` (objective `fix_bug`): plan → research → edit (approval) → test → critic.
- `review_workflow` (objective `review_changes`): collect_diff → critic.

## Quality gates

- `tests_must_pass`: `test_result.status == 'passed'` → `replan` on fail.
- `review_must_pass`: `verdict == 'PASS'` → `replan` on fail.

## Permissions (defaults)

| Tool | Default mode |
| --- | --- |
| `fs.read`, `grep.search`, `glob.search`, `git.status`, `git.diff` | allow |
| `fs.edit`, `patch.apply`, `fs.write` | require_approval |
| `shell.run` | require_approval (critical risk) |
| `test.run`, `git.branch` | require_approval |

## CLI

```bash
neuronium-agent objective run "Fix failing tests" --pack coding --mock
neuronium-agent code "fix this bug"
neuronium-agent packs test coding
```
