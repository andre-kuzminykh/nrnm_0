"""IR → CompiledGraph compiler.

In v0.1 the compiler builds an in-process executor with semantics compatible
with LangGraph (sequential nodes, conditional edges, single-state-dict). The
public interface is `CompiledGraph.run(state, runtime)` and the runtime owns
side effects (model calls, tools, traces).
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional

from neuronium_agent.ir.models import (
    CompiledGraph,
    CriticNode,
    Edge,
    HumanGateNode,
    ModelNode,
    Node,
    NodeKind,
    OperatorNode,
    Program,
    RecoveryNode,
    TerminalNode,
    ToolNode,
)
from neuronium_agent.ir.validator import validate_program


_VAR_PATTERN = re.compile(r"\$\{([a-zA-Z0-9_.]+)\}")


def _resolve_value(value: Any, state: Dict[str, Any]) -> Any:
    if isinstance(value, str):
        def replace(match: "re.Match[str]") -> str:
            key = match.group(1)
            return str(_lookup(state, key))

        if _VAR_PATTERN.fullmatch(value):
            key = _VAR_PATTERN.fullmatch(value).group(1)
            return _lookup(state, key)
        return _VAR_PATTERN.sub(replace, value)
    if isinstance(value, dict):
        return {k: _resolve_value(v, state) for k, v in value.items()}
    if isinstance(value, list):
        return [_resolve_value(v, state) for v in value]
    return value


def _lookup(state: Dict[str, Any], dotted: str) -> Any:
    parts = dotted.split(".")
    cur: Any = state
    for part in parts:
        if isinstance(cur, dict) and part in cur:
            cur = cur[part]
        else:
            return None
    return cur


def _eval_condition(expr: Optional[str], state: Dict[str, Any]) -> bool:
    if not expr:
        return True
    safe_locals = {"state": state, **state}
    try:
        return bool(eval(expr, {"__builtins__": {}}, safe_locals))
    except Exception:  # noqa: BLE001 — defensive in v0.1
        return False


def _find_start(program: Program) -> str:
    if program.start:
        return program.start
    for node in program.nodes:
        if not program.incoming(node.id):
            return node.id
    raise ValueError("program has no start node")


def _next_node(program: Program, current: str, state: Dict[str, Any]) -> Optional[str]:
    edges = program.outgoing(current)
    if not edges:
        return None
    # Conditional edges first; fall back to first unconditional.
    for edge in edges:
        if edge.condition and _eval_condition(edge.condition, state):
            return edge.to_id
    for edge in edges:
        if not edge.condition:
            return edge.to_id
    return None


def _execute_node(node: Node, state: Dict[str, Any], runtime: Any) -> Dict[str, Any]:
    runtime.events.emit("node.started", {"node_id": node.id, "kind": node.kind.value})
    try:
        if isinstance(node, ModelNode):
            result = runtime.run_model(node, state)
        elif isinstance(node, ToolNode):
            args = _resolve_value(node.args, state)
            result = runtime.run_tool(node, args, state)
        elif isinstance(node, OperatorNode):
            args = _resolve_value(node.args, state)
            result = runtime.run_operator(node, args, state)
        elif isinstance(node, HumanGateNode):
            result = runtime.run_human_gate(node, state)
        elif isinstance(node, CriticNode):
            result = runtime.run_critic(node, state)
        elif isinstance(node, RecoveryNode):
            result = runtime.run_recovery(node, state)
        elif isinstance(node, TerminalNode):
            result = runtime.run_terminal(node, state)
        else:  # pragma: no cover — exhaustive
            raise ValueError(f"unsupported node kind: {node.kind}")
    except Exception as exc:  # noqa: BLE001
        runtime.events.emit(
            "node.failed",
            {"node_id": node.id, "kind": node.kind.value, "error": str(exc)},
        )
        raise
    runtime.events.emit(
        "node.completed",
        {"node_id": node.id, "kind": node.kind.value, "outputs": list(result.keys())},
    )
    return result


def compile_program(program: Program) -> CompiledGraph:
    """Validate a Program and produce a CompiledGraph."""
    validate_program(program)

    def runner(state: Dict[str, Any], runtime: Any) -> Dict[str, Any]:
        current: Optional[str] = _find_start(program)
        visited: List[str] = []
        max_iters = 200
        iters = 0
        replan_count = 0
        max_replans = 3
        while current and iters < max_iters:
            node = program.node_by_id(current)
            if node is None:
                break
            visited.append(node.id)
            result = _execute_node(node, state, runtime)
            state.update(result)
            if isinstance(node, TerminalNode):
                break
            next_id = _next_node(program, current, state)
            if isinstance(node, CriticNode):
                verdict = state.get("verdict")
                if verdict == "FAIL" and replan_count < max_replans:
                    replan_count += 1
                    runtime.events.emit(
                        "replan.completed",
                        {"from_node": node.id, "count": replan_count},
                    )
                    # Reroute to start unless the IR provides an explicit FAIL
                    # edge (i.e. an outgoing edge whose condition references
                    # `verdict == 'FAIL'`).
                    fail_edge = next(
                        (
                            e
                            for e in program.outgoing(current)
                            if e.condition and "FAIL" in e.condition
                        ),
                        None,
                    )
                    next_id = fail_edge.to_id if fail_edge else _find_start(program)
                    # Clear the verdict so the next critic pass starts fresh.
                    state.pop("verdict", None)
            current = next_id
            iters += 1
        return {
            "final_state": state,
            "visited": visited,
            "replans": replan_count,
        }

    return CompiledGraph(program=program, runner=runner)
