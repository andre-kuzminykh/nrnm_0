"""Unit tests for Workflow IR models, validator, compiler."""

from __future__ import annotations

import pytest

from neuronium_agent.ir.models import (
    AgentRef,
    CriticCheck,
    CriticNode,
    Edge,
    ModelNode,
    Program,
    TerminalNode,
)
from neuronium_agent.ir.validator import IRValidationError, validate_program
from neuronium_agent.ir.compiler import compile_program


def _minimal_program() -> Program:
    return Program(
        id="t.minimal",
        objective="Test",
        agents=[AgentRef(id="a1", role="executor")],
        nodes=[
            ModelNode(id="n1", name="n1", agent_ref="a1", prompt_ref="p"),
            TerminalNode(id="t1", name="end"),
        ],
        edges=[Edge(from_id="n1", to_id="t1")],
    )


# NR-UT-IR-001
def test_program_loads_from_yaml(tmp_path) -> None:
    program = _minimal_program()
    assert program.nodes[0].id == "n1"
    assert program.nodes[1].kind.value == "terminal"


# NR-UT-IR-002
def test_program_rejects_unknown_edge_target() -> None:
    program = _minimal_program()
    program.edges.append(Edge(from_id="n1", to_id="missing"))
    with pytest.raises(IRValidationError):
        validate_program(program)


def test_program_rejects_duplicate_node_ids() -> None:
    program = _minimal_program()
    program.nodes.append(ModelNode(id="n1", name="dup", agent_ref="a1", prompt_ref="p"))
    with pytest.raises(IRValidationError):
        validate_program(program)


def test_program_requires_terminal_node() -> None:
    program = Program(
        id="t.no_terminal",
        objective="Test",
        agents=[AgentRef(id="a1", role="executor")],
        nodes=[ModelNode(id="n1", name="n1", agent_ref="a1", prompt_ref="p")],
    )
    with pytest.raises(IRValidationError):
        validate_program(program)


# NR-UT-IR-003
def test_conditional_edges_parse() -> None:
    program = Program(
        id="t.cond",
        objective="Test",
        agents=[AgentRef(id="a1", role="critic")],
        nodes=[
            CriticNode(id="c1", name="c1", agent_ref="a1", checks=[CriticCheck(id="x", condition="True")]),
            TerminalNode(id="t1", name="end"),
        ],
        edges=[Edge(from_id="c1", to_id="t1", condition="verdict == 'PASS'")],
    )
    validate_program(program)
    assert program.edges[0].condition == "verdict == 'PASS'"


def test_compile_minimal_program_runs() -> None:
    program = _minimal_program()
    graph = compile_program(program)

    class FakeEvents:
        def __init__(self):
            self.entries = []

        def emit(self, kind, payload=None):
            self.entries.append((kind, payload or {}))

    class FakeRuntime:
        def __init__(self):
            self.events = FakeEvents()

        def run_model(self, node, state):
            return {"result": "ok"}

        def run_terminal(self, node, state):
            return {"final_report": "done"}

    runtime = FakeRuntime()
    out = graph.run({}, runtime)
    assert out["visited"] == ["n1", "t1"]
    assert out["final_state"]["final_report"] == "done"
