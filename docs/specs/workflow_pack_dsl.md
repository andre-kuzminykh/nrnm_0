# Workflow Pack DSL v0.1

A Workflow Pack is a YAML document describing the agents, tools, workflows, and quality gates of an applied workflow domain. The DSL compiles into runtime artifacts: agent definitions, tool policies, Workflow IR templates, and tests.

## Top-level shape

```yaml
pack:
  id: coding
  name: Coding Workflow Pack
  version: "0.1.0"
  schema_version: "0.1"
  compatible_neuronium: ">=0.1.0"
  domain: software_engineering
  description: Helps analyze, edit, test and review code repositories.

objectives: [...]
agents: [...]
tools: [...]
workflows: [...]
quality_gates: [...]
outputs: [...]
tests: [...]
```

## Required fields

- `pack.id`: stable identifier, lowercase, `^[a-z][a-z0-9_]*$`.
- `pack.name`: human-readable name.
- `pack.version`: semantic version of the pack.
- `pack.schema_version`: DSL schema version; v0.1 only supports `"0.1"`.
- `pack.compatible_neuronium`: PEP-440-like range, e.g. `>=0.1.0`.
- `pack.domain`: free-form domain tag.
- `pack.description`: one paragraph describing the pack.

## Objective

```yaml
objectives:
  - id: fix_bug
    user_phrases:
      - "fix this bug"
      - "tests are failing"
    expected_outcomes:
      - bug root cause identified
      - minimal code patch created
      - tests pass
      - summary produced
```

`user_phrases` is used by the suggestion engine to match a free-text objective to packs.

## Agent

```yaml
agents:
  - id: code_planner
    role: planner            # planner | executor | critic | researcher | recovery | curator | designer
    model: smart             # alias resolved by Model Registry
    prompt_ref: prompts/packs/coding/coding_planner.md
    tools: [fs.read, grep.search, git.status]
    permissions:
      "*": deny
      "fs.read": allow
      "grep.search": allow
      "git.status": allow
    memory_scope: project
    context_budget_tokens: 12000
    output_contract:
      type: object
      required: [plan, files_to_inspect, risks]
```

## Tool reference

```yaml
tools:
  - ref: fs.read
    kind: mcp
    risk: low
  - ref: fs.edit
    kind: mcp
    risk: high
  - ref: shell.run
    kind: mcp
    risk: critical
    default_permission: require_approval
```

`kind` ∈ `mcp | builtin | mock`. Risk classes: `low | medium | high | critical`.

## Workflow

```yaml
workflows:
  - id: fix_bug_workflow
    objective_match: fix_bug
    phases:
      - id: understand
        agent: code_planner
        outputs: [plan, files_to_inspect]
      - id: inspect
        agent: code_researcher
        outputs: [root_cause]
      - id: edit
        agent: code_editor
        requires_approval: true
        outputs: [patch_summary, changed_files]
      - id: test
        agent: test_runner
        tools: [shell.run, test.run]
        outputs: [test_result]
      - id: review
        agent: code_reviewer
        outputs: [critic_verdict]
```

The compiler produces one IR node per phase by default. Authors may extend with explicit IR nodes when needed.

## Quality gates

```yaml
quality_gates:
  - id: tests_must_pass
    condition: "test_result.status == 'passed'"
    on_fail: replan          # retry | replan | abort
  - id: review_must_pass
    condition: "critic_verdict == 'PASS'"
    on_fail: replan
```

## Outputs

```yaml
outputs:
  - id: final_summary
    type: markdown            # markdown | json | table
    includes: [changed_files, tests, risks, next_steps]
```

## Tests

```yaml
tests:
  - id: coding_pack_fix_bug_e2e
    objective: "Fix failing test in sample project"
    expected:
      - Workflow reaches test phase
      - Critic phase runs
      - Final outcome is produced
```

These are consumed by the pack test harness in mock mode.

## Compilation outcomes

When a pack compiles successfully the runtime obtains:

- **Agent definitions** keyed by `pack_id.agent_id`.
- **Tool policy** describing allowed/denied/approval-required tools per agent.
- **Workflow IR templates** keyed by objective.
- **Quality gates** attached to relevant critic nodes.
- **Output templates** used for terminal node rendering.
- **Pack metadata** stored in the registry and embedded in the trace.

## Validation rules

1. `pack.schema_version` must equal `"0.1"`.
2. Agent IDs are unique within the pack.
3. Tool refs used by agents must appear in the `tools` section.
4. Workflow `agent` references must exist.
5. `objective_match` references an existing objective ID.
6. Quality gate `on_fail` must be one of `retry | replan | abort`.
7. Output `includes` must reference variables produced by the workflow.
