"""Structural validation for Workflow IR programs."""

from __future__ import annotations

from typing import List

from neuronium_agent.ir.models import NodeKind, Program


class IRValidationError(ValueError):
    """Raised when a Workflow IR Program fails structural validation."""

    def __init__(self, errors: List[str]):
        super().__init__("; ".join(errors))
        self.errors = errors


def validate_program(program: Program) -> None:
    errors: List[str] = []

    node_ids = [n.id for n in program.nodes]
    if len(node_ids) != len(set(node_ids)):
        errors.append("duplicate node ids")

    id_set = set(node_ids)
    for edge in program.edges:
        if edge.from_id not in id_set:
            errors.append(f"edge.from_id refers to unknown node '{edge.from_id}'")
        if edge.to_id not in id_set:
            errors.append(f"edge.to_id refers to unknown node '{edge.to_id}'")

    agent_ids = {a.id for a in program.agents}
    for node in program.nodes:
        if node.kind in (NodeKind.MODEL, NodeKind.TOOL, NodeKind.CRITIC):
            agent_ref = getattr(node, "agent_ref", None)
            if agent_ref and agent_ref not in agent_ids:
                errors.append(
                    f"node '{node.id}' references unknown agent '{agent_ref}'"
                )

    terminals = [n for n in program.nodes if n.kind == NodeKind.TERMINAL]
    if not terminals:
        errors.append("program must contain at least one terminal node")

    if program.start:
        if program.start not in id_set:
            errors.append(f"start node '{program.start}' not found")
    else:
        starts = [
            n for n in program.nodes if not program.incoming(n.id)
        ]
        if len(starts) != 1:
            errors.append(
                "program must declare 'start' or have exactly one node with no "
                f"incoming edges (found {len(starts)})"
            )

    if errors:
        raise IRValidationError(errors)
