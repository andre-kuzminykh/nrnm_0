# Workflow IR v0.1

The Workflow Intermediate Representation (IR) is Neuronium's stable contract for executable agent workflows. Compilers in any backend (LangGraph today, others tomorrow) consume the same IR.

## Top-level: `Program`

```python
class Program(BaseModel):
    id: str
    version: str = "0.1"
    pack_id: Optional[str]
    objective: str
    inputs: dict[str, str]            # variable name -> type label
    outputs: dict[str, str]
    agents: list[AgentRef]            # agents owning nodes
    commitments: list[Commitment] = []
    nodes: list[Node]
    edges: list[Edge]
    metadata: dict[str, Any] = {}
```

## Nodes

A node is one of:

```python
class ModelNode(Node):
    kind: Literal["model"]
    agent_ref: str                    # AgentInstance id
    prompt_ref: str                   # path to markdown prompt
    inputs: list[str]
    outputs: list[str]

class ToolNode(Node):
    kind: Literal["tool"]
    agent_ref: str
    tool_ref: str                     # namespaced "<server>.<tool>"
    args: dict[str, Any]
    outputs: list[str]

class OperatorNode(Node):
    kind: Literal["operator"]
    op: Literal["assign", "merge", "select", "format"]
    args: dict[str, Any]
    outputs: list[str]

class HumanGateNode(Node):
    kind: Literal["human_gate"]
    purpose: Literal["approval", "input", "review"]
    message: str

class CriticNode(Node):
    kind: Literal["critic"]
    agent_ref: str
    checks: list[CriticCheck]
    outputs: list[str]

class RecoveryNode(Node):
    kind: Literal["recover"]
    strategy: Literal["retry", "replan", "abort"]
    classification: str

class TerminalNode(Node):
    kind: Literal["terminal"]
    outcome_template: Optional[str]
```

Every node has `id: str`, `name: str`, `description: Optional[str]`.

## Edges

```python
class Edge(BaseModel):
    from_id: str
    to_id: str
    condition: Optional[str]          # simple boolean expression on state
    label: Optional[str]
```

## Commitments

A `Commitment` is a statement that must hold for the run to be considered successful:

```python
class Commitment(BaseModel):
    id: str
    statement: str
    required_evidence: list[str]
```

## Validation rules

1. Node IDs are unique.
2. Every edge references existing nodes.
3. Exactly one node has no incoming edges (the start node) — or the IR declares an explicit `start` node id.
4. At least one `terminal` node is reachable.
5. Tool nodes reference tools declared in the pack/registry.
6. Model nodes reference agents declared in `agents[]`.
7. Critic nodes' `checks` reference resolvable predicates.
8. Conditional edges share the same source and cover the predicate space (or have a default).

## Compilation contract

The IR compiler produces an executable graph object exposing:

```python
class CompiledGraph:
    def run(self, state: dict, runtime: Runtime) -> dict: ...
```

The `Runtime` provides: model provider, tool registry, policy engine, trace recorder, artifact store, memory.

## Example: minimal coding fix-bug IR (excerpt)

```yaml
id: coding.fix_bug
version: "0.1"
pack_id: coding
objective: "Fix the failing test in this repository"
inputs: { repo_path: "string" }
outputs: { final_report: "markdown" }
agents:
  - { id: code_planner, role: planner }
  - { id: code_researcher, role: executor }
  - { id: code_editor, role: executor }
  - { id: test_runner, role: executor }
  - { id: code_reviewer, role: critic }
nodes:
  - { id: n_plan,     kind: model,  agent_ref: code_planner,    prompt_ref: prompts/packs/coding/coding_planner.md,  inputs: [repo_path], outputs: [plan, files_to_inspect] }
  - { id: n_inspect,  kind: tool,   agent_ref: code_researcher, tool_ref: fs.read, args: { paths: "${files_to_inspect}" }, outputs: [snippets] }
  - { id: n_edit,     kind: tool,   agent_ref: code_editor,     tool_ref: patch.apply, args: { patch: "${proposed_patch}" }, outputs: [edit_result] }
  - { id: n_gate,     kind: human_gate, purpose: approval, message: "Approve patch?" }
  - { id: n_test,     kind: tool,   agent_ref: test_runner,     tool_ref: test.run, args: {}, outputs: [test_result] }
  - { id: n_review,   kind: critic, agent_ref: code_reviewer,   checks: [{ id: tests_pass, condition: "test_result.status == 'passed'" }, { id: review_ok, condition: "review_verdict == 'PASS'" }], outputs: [verdict] }
  - { id: n_final,    kind: terminal, outcome_template: prompts/packs/coding/final_outcome.md }
edges:
  - { from_id: n_plan,    to_id: n_inspect }
  - { from_id: n_inspect, to_id: n_edit }
  - { from_id: n_edit,    to_id: n_gate }
  - { from_id: n_gate,    to_id: n_test }
  - { from_id: n_test,    to_id: n_review }
  - { from_id: n_review,  to_id: n_final,  condition: "verdict == 'PASS'" }
  - { from_id: n_review,  to_id: n_plan,   condition: "verdict == 'FAIL'", label: replan }
```
