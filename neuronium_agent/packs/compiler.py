"""Compile a WorkflowPack into runtime artifacts."""

from __future__ import annotations

from typing import Dict, List, Optional

from pydantic import BaseModel, ConfigDict

from neuronium_agent.agents.models import (
    AgentDefinition,
    AgentRole,
    OutputContract,
)
from neuronium_agent.ir.models import (
    AgentRef,
    CriticCheck,
    CriticNode,
    Edge,
    HumanGateNode,
    ModelNode,
    OperatorNode,
    Program,
    TerminalNode,
    ToolNode,
)
from neuronium_agent.packs.models import (
    PackHTNTask,
    PackTool,
    QualityGate,
    WorkflowPack,
    WorkflowPhase,
)
from neuronium_agent.packs.validator import validate_pack
from neuronium_agent.planning.models import HTNMethod, HTNTask, HierarchicalPlan, TaskKind
from neuronium_agent.planning.planner import (
    HTNPlanner,
    build_implicit_plan_from_phases,
)


class ToolPolicyEntry(BaseModel):
    model_config = ConfigDict(extra="forbid")
    tool_ref: str
    agent_id: Optional[str] = None
    mode: str  # allow | deny | require_approval


class CompiledPack(BaseModel):
    """Result of compiling a WorkflowPack."""

    model_config = ConfigDict(extra="forbid")
    pack: WorkflowPack
    agent_definitions: List[AgentDefinition]
    tool_policy: List[ToolPolicyEntry]
    tool_descriptors: Dict[str, PackTool]
    ir_templates: Dict[str, Program]
    plan_templates: Dict[str, HierarchicalPlan] = {}
    htn_tasks: Dict[str, HTNTask] = {}
    quality_gates: List[QualityGate]
    tests: List[Dict[str, object]]


def _agent_role(role: str) -> AgentRole:
    try:
        return AgentRole(role)
    except ValueError:
        return AgentRole.EXECUTOR


def _compile_agents(pack: WorkflowPack) -> List[AgentDefinition]:
    defs: List[AgentDefinition] = []
    for agent in pack.agents:
        contract = None
        if agent.output_contract is not None:
            contract = OutputContract(
                type=agent.output_contract.type,
                required=agent.output_contract.required,
                properties=agent.output_contract.properties,
            )
        defs.append(
            AgentDefinition(
                id=agent.id,
                role=_agent_role(agent.role),
                goal=agent.goal,
                prompt_ref=agent.prompt_ref,
                model=agent.model,
                tools=agent.tools,
                permissions=agent.permissions,
                skills=agent.skills,
                memory_scope=agent.memory_scope,
                context_budget_tokens=agent.context_budget_tokens,
                output_contract=contract,
                acceptance_criteria=agent.acceptance_criteria,
                pack_id=pack.id,
            )
        )
    return defs


def _compile_tool_policy(pack: WorkflowPack) -> List[ToolPolicyEntry]:
    entries: List[ToolPolicyEntry] = []
    by_ref = {t.ref: t for t in pack.tools}
    for tool in pack.tools:
        mode = (
            tool.default_permission.value
            if tool.default_permission is not None
            else ("require_approval" if tool.risk.value in {"high", "critical"} else "allow")
        )
        entries.append(ToolPolicyEntry(tool_ref=tool.ref, mode=mode))
    for agent in pack.agents:
        for tool_ref, mode in agent.permissions.items():
            if tool_ref == "*":
                continue
            entries.append(
                ToolPolicyEntry(tool_ref=tool_ref, agent_id=agent.id, mode=mode)
            )
    # Tools mentioned by agents but missing from `tools` keep their default.
    return entries


def _phase_kind(phase: WorkflowPhase, pack: WorkflowPack) -> str:
    if phase.kind != "model":
        return phase.kind
    if phase.tools:
        return "tool"
    agent = next((a for a in pack.agents if a.id == phase.agent), None)
    if agent and _agent_role(agent.role) == AgentRole.CRITIC:
        return "critic"
    return "model"


def _pack_task_to_htn(task: PackHTNTask) -> HTNTask:
    return HTNTask(
        id=task.id,
        kind=TaskKind(task.kind),
        description=task.description,
        phase_id=task.phase_id,
        methods=[
            HTNMethod(id=m.id, applies_when=m.applies_when, subtasks=m.subtasks)
            for m in task.methods
        ],
    )


def _plan_for_workflow(pack: WorkflowPack, workflow_id: str) -> HierarchicalPlan:
    workflow = next((w for w in pack.workflows if w.id == workflow_id), None)
    if workflow is None:
        raise KeyError(f"workflow {workflow_id} not found")
    if workflow.root_task and pack.tasks:
        htn_tasks = {t.id: _pack_task_to_htn(t) for t in pack.tasks}
        planner = HTNPlanner(htn_tasks)
        return planner.plan(workflow.root_task)
    return build_implicit_plan_from_phases(
        workflow.id, [p.id for p in workflow.phases]
    )


def _build_ir_for_workflow(
    pack: WorkflowPack, workflow_id: str
) -> tuple[Program, HierarchicalPlan]:
    workflow = next((w for w in pack.workflows if w.id == workflow_id), None)
    if workflow is None:
        raise KeyError(f"workflow {workflow_id} not found")

    objective = next(
        (o for o in pack.objectives if o.id == workflow.objective_match), None
    )
    objective_text = objective.id if objective else workflow_id
    plan = _plan_for_workflow(pack, workflow_id)
    phase_index = {p.id: p for p in workflow.phases}

    agent_refs = [
        AgentRef(id=a.id, role=a.role, pack_agent_id=a.id) for a in pack.agents
    ]

    nodes = []
    edges = []
    prev_id: Optional[str] = None
    critic_in_workflow = False

    for leaf in plan.leaves:
        if leaf.phase_id is None:
            continue
        phase = phase_index.get(leaf.phase_id)
        if phase is None:
            # Plan referenced a phase that does not exist in this workflow.
            continue
        task_path = list(leaf.task_path)
        kind = _phase_kind(phase, pack)
        node_id = f"n_{phase.id}"
        if kind == "tool":
            tool_ref = phase.tools[0] if phase.tools else "mock.noop"
            nodes.append(
                ToolNode(
                    id=node_id,
                    name=phase.id,
                    agent_ref=phase.agent,
                    tool_ref=tool_ref,
                    args={},
                    outputs=phase.outputs,
                    task_path=task_path,
                    task_id=leaf.task_id,
                )
            )
        elif kind == "critic":
            critic_in_workflow = True
            checks = [
                CriticCheck(id=g.id, condition=g.condition, on_fail=g.on_fail)
                for g in pack.quality_gates
            ]
            nodes.append(
                CriticNode(
                    id=node_id,
                    name=phase.id,
                    agent_ref=phase.agent,
                    checks=checks,
                    outputs=phase.outputs or ["verdict"],
                    task_path=task_path,
                    task_id=leaf.task_id,
                )
            )
        elif kind == "operator":
            nodes.append(
                OperatorNode(
                    id=node_id,
                    name=phase.id,
                    op="assign",
                    args={},
                    outputs=phase.outputs,
                    task_path=task_path,
                    task_id=leaf.task_id,
                )
            )
        else:
            prompt_ref = phase.prompt_ref or _find_agent_prompt(pack, phase.agent)
            nodes.append(
                ModelNode(
                    id=node_id,
                    name=phase.id,
                    agent_ref=phase.agent,
                    prompt_ref=prompt_ref or "",
                    inputs=[],
                    outputs=phase.outputs,
                    task_path=task_path,
                    task_id=leaf.task_id,
                )
            )

        if prev_id is not None:
            edges.append(Edge(from_id=prev_id, to_id=node_id))
        prev_id = node_id

        if phase.requires_approval:
            gate_id = f"n_{phase.id}_gate"
            nodes.append(
                HumanGateNode(
                    id=gate_id,
                    name=f"approve_{phase.id}",
                    purpose="approval",
                    message=f"Approve phase '{phase.id}'?",
                    task_path=task_path,
                    task_id=leaf.task_id,
                )
            )
            edges.append(Edge(from_id=prev_id, to_id=gate_id))
            prev_id = gate_id

    # Add critic node if pack has quality gates but no critic agent in workflow.
    if pack.quality_gates and not critic_in_workflow:
        critic_agent = next(
            (a for a in pack.agents if _agent_role(a.role) == AgentRole.CRITIC),
            None,
        )
        agent_id = critic_agent.id if critic_agent else (
            pack.agents[0].id if pack.agents else "default"
        )
        critic_id = "n_critic_auto"
        nodes.append(
            CriticNode(
                id=critic_id,
                name="critic_auto",
                agent_ref=agent_id,
                checks=[
                    CriticCheck(id=g.id, condition=g.condition, on_fail=g.on_fail)
                    for g in pack.quality_gates
                ],
                outputs=["verdict"],
                task_path=[plan.root.task_id],
                task_id=f"{plan.root.task_id}.critic",
            )
        )
        if prev_id is not None:
            edges.append(Edge(from_id=prev_id, to_id=critic_id))
        prev_id = critic_id

    final_id = "n_final"
    template = pack.outputs[0].id if pack.outputs else None
    nodes.append(
        TerminalNode(
            id=final_id,
            name="final_outcome",
            outcome_template=template,
            task_path=[plan.root.task_id],
            task_id=f"{plan.root.task_id}.terminal",
        )
    )
    if prev_id is not None:
        edges.append(Edge(from_id=prev_id, to_id=final_id))

    inputs = {"objective": "string"}
    outputs = {"final_report": "markdown"}

    program = Program(
        id=f"{pack.id}.{workflow.id}",
        version="0.1",
        pack_id=pack.id,
        objective=objective_text,
        inputs=inputs,
        outputs=outputs,
        agents=agent_refs,
        nodes=nodes,
        edges=edges,
        metadata={
            "workflow_id": workflow.id,
            "plan_depth": plan.depth(),
            "plan_method_choices": dict(plan.method_choices),
        },
    )
    return program, plan


def _find_agent_prompt(pack: WorkflowPack, agent_id: str) -> Optional[str]:
    for a in pack.agents:
        if a.id == agent_id:
            return a.prompt_ref
    return None


def compile_pack(pack: WorkflowPack) -> CompiledPack:
    validate_pack(pack)
    agent_defs = _compile_agents(pack)
    tool_policy = _compile_tool_policy(pack)
    tool_descriptors = {t.ref: t for t in pack.tools}
    ir_templates: Dict[str, Program] = {}
    plan_templates: Dict[str, HierarchicalPlan] = {}
    for workflow in pack.workflows:
        program, plan = _build_ir_for_workflow(pack, workflow.id)
        ir_templates[workflow.objective_match] = program
        plan_templates[workflow.objective_match] = plan
    htn_tasks = {t.id: _pack_task_to_htn(t) for t in pack.tasks}
    tests = [t.model_dump() for t in pack.tests]
    return CompiledPack(
        pack=pack,
        agent_definitions=agent_defs,
        tool_policy=tool_policy,
        tool_descriptors=tool_descriptors,
        ir_templates=ir_templates,
        plan_templates=plan_templates,
        htn_tasks=htn_tasks,
        quality_gates=pack.quality_gates,
        tests=tests,
    )
