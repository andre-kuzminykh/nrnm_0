"""Objective Runner: orchestrates intake → plan → IR → compile → execute → outcome."""

from __future__ import annotations

import os
import uuid
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field

from neuronium_agent.agents.factory import AgentFactory
from neuronium_agent.agents.models import AgentInstance
from neuronium_agent.ir.compiler import compile_program
from neuronium_agent.ir.models import Program
from neuronium_agent.memory.backend import MemoryBackend, MemoryConfig, build_backend
from neuronium_agent.memory.graphrag import MockGraphRAG, RetrievalQuery
from neuronium_agent.packs.compiler import CompiledPack
from neuronium_agent.packs.registry import PackRegistry
from neuronium_agent.runtime.backend import Runtime, build_default_runtime
from neuronium_agent.runtime.events import EventBus
from neuronium_agent.runtime.state import Run, RunStatus
from neuronium_agent.tools.governance import PermissionDecision, PolicyEngine, ToolPolicyEntry
from neuronium_agent.trace.recorder import TraceRecorder


class RunResult(BaseModel):
    model_config = ConfigDict(extra="forbid")
    run: Run
    final_state: Dict[str, Any] = Field(default_factory=dict)
    events: List[Dict[str, Any]] = Field(default_factory=list)
    visited_nodes: List[str] = Field(default_factory=list)
    replans: int = 0
    final_report: str = ""


def _build_policy_engine(compiled: CompiledPack) -> PolicyEngine:
    entries: List[ToolPolicyEntry] = []
    for entry in compiled.tool_policy:
        try:
            mode = PermissionDecision(entry.mode)
        except ValueError:
            mode = PermissionDecision.ALLOW
        entries.append(
            ToolPolicyEntry(tool_ref=entry.tool_ref, agent_id=entry.agent_id, mode=mode)
        )
    return PolicyEngine(pack_entries=entries)


class ObjectiveRunner:
    def __init__(
        self,
        registry: Optional[PackRegistry] = None,
        trace_dir: Optional[str] = None,
        auto_approve: bool = True,
        force_failure_first: bool = False,
        memory: Optional[MemoryBackend] = None,
        memory_config: Optional[MemoryConfig] = None,
    ) -> None:
        self.registry = registry or PackRegistry()
        self.trace_dir = trace_dir
        self.auto_approve = auto_approve
        self.force_failure_first = force_failure_first
        self.memory = memory
        self.memory_config = memory_config or MemoryConfig()

    def _select_pack(self, objective: str, pack_id: Optional[str]) -> CompiledPack:
        if pack_id:
            return self.registry.get_compiled(pack_id)
        suggested = self.registry.suggest_for_objective(objective)
        if suggested is None:
            raise ValueError(
                "could not infer a pack from the objective; pass --pack <id>"
            )
        return self.registry.get_compiled(suggested.id)

    def _select_program(self, compiled: CompiledPack, objective: str) -> Program:
        if not compiled.ir_templates:
            raise ValueError(f"pack '{compiled.pack.id}' has no compiled workflows")
        # Try to match user phrase to objective; otherwise pick first.
        matched_objective = compiled.pack.get_objective_by_phrase(objective)
        if matched_objective and matched_objective.id in compiled.ir_templates:
            program = compiled.ir_templates[matched_objective.id]
        else:
            program = next(iter(compiled.ir_templates.values()))
        # Stamp the runtime objective for trace clarity.
        return program.model_copy(update={"objective": objective})

    def run(
        self,
        objective: str,
        pack_id: Optional[str] = None,
        *,
        inputs: Optional[Dict[str, Any]] = None,
        attachments: Optional[List[str]] = None,
    ) -> RunResult:
        compiled = self._select_pack(objective, pack_id)
        run = Run(
            id=f"run-{uuid.uuid4().hex[:10]}",
            objective=objective,
            pack_id=compiled.pack.id,
            status=RunStatus.RUNNING,
            inputs=dict(inputs or {}),
            attachments=list(attachments or []),
        )
        trace_path = None
        if self.trace_dir:
            os.makedirs(self.trace_dir, exist_ok=True)
            trace_path = os.path.join(self.trace_dir, f"{run.id}.jsonl")
            run.trace_path = trace_path
        recorder = TraceRecorder(run_id=run.id, path=trace_path)
        events = EventBus(recorder)
        events.emit(
            "run.started",
            {
                "run_id": run.id,
                "objective": objective,
                "pack_id": compiled.pack.id,
                "pack_version": compiled.pack.pack.version,
                "schema_version": compiled.pack.pack.schema_version,
            },
        )
        events.emit("objective.intake", {"objective": objective})
        events.emit(
            "pack.selected",
            {"pack_id": compiled.pack.id, "agents": [a.id for a in compiled.agent_definitions]},
        )
        events.emit(
            "pack.compiled",
            {
                "pack_id": compiled.pack.id,
                "workflows": list(compiled.ir_templates.keys()),
            },
        )
        # Memory: select backend (explicit > config > mock fallback).
        memory: MemoryBackend
        if self.memory is not None:
            memory = self.memory
        else:
            try:
                memory = build_backend(self.memory_config)
            except Exception:  # noqa: BLE001
                memory = MockGraphRAG()
        events.emit(
            "memory.initialized",
            {
                "backend": getattr(memory, "name", "unknown"),
                "ready": getattr(memory, "ready", True),
            },
        )
        try:
            result = memory.retrieve(
                RetrievalQuery(text=objective, top_k=5), pack_id=compiled.pack.id
            )
            events.emit(
                "memory.retrieved",
                {
                    "entities": [e.id for e in result.entities],
                    "snippets": len(result.snippets),
                    "backend": getattr(memory, "name", "unknown"),
                },
            )
        except Exception as exc:  # noqa: BLE001
            events.emit(
                "memory.retrieval_failed",
                {"error": str(exc), "backend": getattr(memory, "name", "unknown")},
            )

        # Build agent team and policy
        factory = AgentFactory(run_id=run.id, events=events)
        agent_instances: Dict[str, AgentInstance] = factory.instantiate_team(
            compiled.agent_definitions
        )

        policy = _build_policy_engine(compiled)

        runtime = build_default_runtime(
            run_id=run.id,
            pack_id=compiled.pack.id,
            events=events,
            policy=policy,
            agent_instances=agent_instances,
            factory=factory,
            auto_approve=self.auto_approve,
            force_failure_first=self.force_failure_first,
            memory=memory,
            memory_config=self.memory_config,
        )

        # Select & compile IR
        program = self._select_program(compiled, objective)
        # Emit hierarchical plan diagnostics when present.
        plan = None
        for obj_id, candidate in compiled.plan_templates.items():
            if candidate.root.task_id == program.metadata.get("workflow_id") or obj_id == program.metadata.get("workflow_id"):
                plan = candidate
                break
        if plan is None and compiled.plan_templates:
            plan = next(iter(compiled.plan_templates.values()))
        if plan is not None:
            events.emit(
                "plan.decomposed",
                {
                    "root": plan.root.task_id,
                    "depth": plan.depth(),
                    "leaves": [leaf.task_id for leaf in plan.leaves],
                    "method_choices": dict(plan.method_choices),
                    "htn": bool(compiled.htn_tasks),
                },
            )
        events.emit(
            "ir.built",
            {"program_id": program.id, "nodes": len(program.nodes), "edges": len(program.edges)},
        )
        graph = compile_program(program)
        events.emit("ir.compiled", {"program_id": program.id})

        # Initial state
        state: Dict[str, Any] = {
            "objective": objective,
            **(inputs or {}),
        }
        try:
            output = graph.run(state, runtime)
            run.outputs = output.get("final_state", {})
            run.status = RunStatus.SUCCEEDED
            events.emit("run.completed", {"run_id": run.id})
            visited = output.get("visited", [])
            replans = output.get("replans", 0)
            final_state = output.get("final_state", {})
        except PermissionError as exc:
            run.status = RunStatus.AWAITING_APPROVAL
            events.emit("run.failed", {"run_id": run.id, "reason": str(exc)})
            raise
        except Exception as exc:
            run.status = RunStatus.FAILED
            events.emit("run.failed", {"run_id": run.id, "reason": str(exc)})
            raise
        final_report = final_state.get("final_report", "")
        return RunResult(
            run=run,
            final_state=final_state,
            events=events.events,
            visited_nodes=visited,
            replans=replans,
            final_report=final_report,
        )
