# Hierarchical Planning (HTN)

Neuronium plans work as a tree of tasks instead of a flat phase list. The
**HTN planner** expands a root *compound* task into *primitive* tasks using
*methods* declared in a workflow pack. Each primitive maps to a workflow phase
that emits exactly one IR node. The IR compiler preserves the hierarchy as
`task_path` metadata on every node, the runtime emits subplan-level events,
and quality-gate failures replan the smallest sufficient subplan instead of
the whole workflow.

## Concepts

- **Compound task** — high-level task that decomposes via one of its `methods`.
- **Primitive task** — leaf that references a workflow phase by `phase_id` and
  emits one IR node.
- **HTN method** — an ordered decomposition `subtasks: [task_id, ...]` with an
  optional `applies_when` predicate evaluated against the run state. The first
  applicable method wins.
- **Hierarchical plan** — tree of `PlanNode`s rooted at the chosen
  workflow's `root_task`.
- **task_path** — every IR node carries the list of compound ancestors of its
  primitive task (e.g. `[fix_bug_root, edit_and_verify, task_edit]`).

## Pack DSL surface

A workflow pack can optionally declare `tasks:` and reference one with
`workflows[].root_task:`.

```yaml
workflows:
  - id: fix_bug_workflow
    objective_match: fix_bug
    root_task: fix_bug_root
    phases:
      - { id: plan,     agent: code_planner,    outputs: [plan, files_to_inspect, risks] }
      - { id: research, agent: code_researcher, outputs: [root_cause, snippets] }
      - { id: edit,     agent: code_editor, requires_approval: true, outputs: [patch_summary, changed_files] }
      - { id: test,     agent: test_runner,     outputs: [test_result] }
      - { id: review,   agent: code_reviewer,   outputs: [verdict, reasons] }

tasks:
  - id: fix_bug_root
    kind: compound
    methods:
      - id: standard
        subtasks: [understand_bug, edit_and_verify, review_outcome]
  - id: understand_bug
    kind: compound
    methods:
      - id: plan_then_inspect
        subtasks: [task_plan, task_research]
  - id: edit_and_verify
    kind: compound
    methods:
      - id: edit_then_test
        subtasks: [task_edit, task_test]
  - id: review_outcome
    kind: compound
    methods:
      - id: single_review
        subtasks: [task_review]
  - { id: task_plan,     kind: primitive, phase_id: plan }
  - { id: task_research, kind: primitive, phase_id: research }
  - { id: task_edit,     kind: primitive, phase_id: edit }
  - { id: task_test,     kind: primitive, phase_id: test }
  - { id: task_review,   kind: primitive, phase_id: review }
```

If `tasks` is omitted (or `root_task` is unset) the runtime falls back to an
**implicit plan**: one root node whose method is `implicit_sequence` and whose
children are the workflow phases in order. Every existing pack keeps working.

## Validation rules (added)

- A primitive task must declare `phase_id` and must not declare `methods`.
- A compound task must declare at least one method.
- All `subtasks` references must resolve to declared task ids.
- `workflow.root_task` must reference a declared task id.
- Every primitive task's `phase_id` must exist in the workflow's `phases`.

## Planning algorithm

`HTNPlanner.plan(root_id, state)`:

1. Look up the task; abort if missing.
2. Primitive → emit a leaf `PlanNode`.
3. Compound → iterate `methods`; pick the first whose `applies_when` evaluates
   truthy against `state` (empty / `"true"` is always applicable).
4. Recursively expand subtasks; preserve order; record `method_choices`.
5. Track `task_path` (ancestor stack) per node and detect cycles.
6. Refuse plans deeper than `MAX_DEPTH = 32`.

`build_implicit_plan_from_phases(workflow_id, phase_ids)` returns the fallback.

## IR compilation

For each workflow the pack compiler:

1. Resolves the workflow's hierarchical plan (HTN or implicit).
2. Walks the plan leaves in order; emits a `ModelNode` / `ToolNode` /
   `CriticNode` / `OperatorNode` / `HumanGateNode` per leaf depending on phase
   shape.
3. Tags every emitted IR node with `task_path` and `task_id` matching the
   primitive plan leaf.
4. Records `plan_depth` and `plan_method_choices` in `Program.metadata`.

Compiler output is `(Program, HierarchicalPlan)`; `CompiledPack` exposes both
`ir_templates` and `plan_templates` keyed by objective id.

## Runtime events

- `plan.decomposed` — fired once per run with
  `{root, depth, leaves, method_choices, htn}`.
- `subplan.entered` / `subplan.completed` — paired around every compound
  ancestor as execution enters / leaves it; nested subplans nest naturally.
- `subplan.failed` — emitted when a quality gate fails inside a subplan;
  payload includes `subplan`, `from_node`, `task_path`, `checks`.
- `replan.completed` — payload includes `subplan` (the chosen replan scope)
  and `scope: "subplan" | "program"`.

## Replan scope selection

Heuristic in the IR executor:

1. If the failing node sits at depth ≥ 3 (e.g. a critic inside a sub-subplan),
   target the **previous top-level sibling subplan**. This matches the typical
   case where a review subplan fails on an artifact produced by the
   immediately preceding subplan (e.g. `review_outcome` → re-run
   `edit_and_verify`).
2. Otherwise, replan the immediate compound parent.
3. Fall back to the program root.

`max_replans = 3` by default. Once selected, the executor reroutes to the
first IR node whose `task_path` contains the replan scope.

## Backward compatibility

Packs without `tasks:` still compile and run. `plan.decomposed.htn = False`
signals the implicit case. CLI / API surface is unchanged.

## Requirements

| ID | Requirement |
| --- | --- |
| NR-FR-PLAN-001 | The system shall provide an HTN planner with `compound` / `primitive` tasks. |
| NR-FR-PLAN-002 | Compound tasks shall declare one or more methods; methods shall be ordered, may declare `applies_when`. |
| NR-FR-PLAN-003 | The planner shall pick the first applicable method. |
| NR-FR-PLAN-004 | The planner shall detect cycles and abort with a clear error. |
| NR-FR-PLAN-005 | The planner shall validate that referenced subtasks exist. |
| NR-FR-PLAN-006 | The pack DSL shall accept an optional `tasks:` block and `workflows[].root_task`. |
| NR-FR-PLAN-007 | The pack validator shall enforce per-task structural rules. |
| NR-FR-PLAN-008 | The compiler shall record `task_path` and `task_id` on every IR node. |
| NR-FR-PLAN-009 | The runtime shall emit `plan.decomposed`, `subplan.entered`, `subplan.completed`, `subplan.failed`. |
| NR-FR-PLAN-010 | The runtime shall replan the smallest sufficient subplan on quality-gate failure. |
| NR-FR-PLAN-011 | Packs without HTN tasks shall use an implicit depth-1 plan derived from phases. |
