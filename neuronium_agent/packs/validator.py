"""Workflow Pack validator: cross-field checks."""

from __future__ import annotations

import re
from typing import List

from neuronium_agent.packs.errors import PackValidationError
from neuronium_agent.packs.models import WorkflowPack


_SCHEMA_SUPPORTED = {"0.1"}
_VERSION_RANGE = re.compile(r"^(>=|>|==|<=|<)\s*([0-9.]+)$")


def _range_matches(spec: str, current: str = "0.1.0") -> bool:
    match = _VERSION_RANGE.match(spec.strip())
    if not match:
        return False
    op, ver = match.group(1), match.group(2)

    def _parts(v: str):
        return [int(x) for x in v.split(".") if x.isdigit()]

    cur = _parts(current)
    target = _parts(ver)
    if op == ">=":
        return cur >= target
    if op == ">":
        return cur > target
    if op == "==":
        return cur == target
    if op == "<=":
        return cur <= target
    if op == "<":
        return cur < target
    return False


def validate_pack(pack: WorkflowPack) -> None:
    errors: List[str] = []

    if pack.pack.schema_version not in _SCHEMA_SUPPORTED:
        errors.append(
            f"unsupported schema_version '{pack.pack.schema_version}' "
            f"(supported: {sorted(_SCHEMA_SUPPORTED)})"
        )

    if not _range_matches(pack.pack.compatible_neuronium):
        errors.append(
            f"compatible_neuronium range '{pack.pack.compatible_neuronium}' "
            "does not match current Neuronium 0.1.0"
        )

    if not re.match(r"^[a-z][a-z0-9_]*$", pack.pack.id):
        errors.append(f"pack id '{pack.pack.id}' must match ^[a-z][a-z0-9_]*$")

    agent_ids = {a.id for a in pack.agents}
    tool_refs = {t.ref for t in pack.tools}
    objective_ids = {o.id for o in pack.objectives}

    for agent in pack.agents:
        for tool in agent.tools:
            if tool not in tool_refs:
                errors.append(
                    f"agent '{agent.id}' references unknown tool '{tool}'"
                )
        for tool, mode in agent.permissions.items():
            if tool != "*" and tool not in tool_refs:
                errors.append(
                    f"agent '{agent.id}' permission references unknown tool '{tool}'"
                )
            if mode not in {"allow", "deny", "require_approval"}:
                errors.append(
                    f"agent '{agent.id}' invalid permission mode '{mode}' for '{tool}'"
                )

    task_ids = {t.id for t in pack.tasks}
    for task in pack.tasks:
        if task.kind == "primitive":
            if not task.phase_id:
                errors.append(
                    f"primitive HTN task '{task.id}' must declare phase_id"
                )
            if task.methods:
                errors.append(
                    f"primitive HTN task '{task.id}' must not declare methods"
                )
        else:
            if not task.methods:
                errors.append(
                    f"compound HTN task '{task.id}' must declare at least one method"
                )
            for method in task.methods:
                for sub in method.subtasks:
                    if sub not in task_ids:
                        errors.append(
                            f"HTN method '{task.id}.{method.id}' references unknown task '{sub}'"
                        )

    for workflow in pack.workflows:
        if workflow.objective_match not in objective_ids:
            errors.append(
                f"workflow '{workflow.id}' references unknown objective "
                f"'{workflow.objective_match}'"
            )
        phase_ids = {p.id for p in workflow.phases}
        if workflow.root_task is not None:
            if workflow.root_task not in task_ids:
                errors.append(
                    f"workflow '{workflow.id}' root_task '{workflow.root_task}' is not declared in tasks"
                )
            for task in pack.tasks:
                if task.kind == "primitive" and task.phase_id and task.phase_id not in phase_ids:
                    errors.append(
                        f"HTN primitive task '{task.id}' references phase '{task.phase_id}' "
                        f"not in workflow '{workflow.id}'"
                    )
        for phase in workflow.phases:
            if phase.agent not in agent_ids:
                errors.append(
                    f"workflow '{workflow.id}' phase '{phase.id}' references unknown "
                    f"agent '{phase.agent}'"
                )
            for tool in phase.tools:
                if tool not in tool_refs:
                    errors.append(
                        f"workflow '{workflow.id}' phase '{phase.id}' references "
                        f"unknown tool '{tool}'"
                    )

    for gate in pack.quality_gates:
        if gate.on_fail not in {"retry", "replan", "abort"}:
            errors.append(
                f"quality gate '{gate.id}' invalid on_fail '{gate.on_fail}'"
            )

    if errors:
        raise PackValidationError(errors)
