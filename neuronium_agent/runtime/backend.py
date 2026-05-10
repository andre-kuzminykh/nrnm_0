"""Runtime container: holds providers, tools, policy, memory, events, agents.

This is the LangGraph-compatible backend in v0.1: each compiled graph drives
nodes via methods on this Runtime, identical to what a LangGraph compiler would
call. v0.2 swaps the in-process executor for actual LangGraph while keeping
this surface stable.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict

from neuronium_agent.agents.factory import AgentFactory
from neuronium_agent.agents.models import AgentInstance
from neuronium_agent.agents.prompt_composer import compose_prompt
from neuronium_agent.ir.models import (
    CriticNode,
    HumanGateNode,
    ModelNode,
    OperatorNode,
    RecoveryNode,
    TerminalNode,
    ToolNode,
)
from neuronium_agent.memory.artifact_graph import Artifact, ArtifactGraph
from neuronium_agent.memory.backend import MemoryBackend, MemoryConfig, build_backend
from neuronium_agent.memory.graphrag import MockGraphRAG, RetrievalQuery
from neuronium_agent.providers.base import ModelRequest
from neuronium_agent.providers.registry import ModelRegistry, default_registry  # noqa: F401
from neuronium_agent.runtime.events import EventBus
from neuronium_agent.tools.governance import PermissionDecision, PolicyEngine
from neuronium_agent.tools.registry import ToolRegistry
from neuronium_agent.tools.mock_mcp import MockMCP
from neuronium_agent.tools.real import RealToolsConfig, register_real_tools
from neuronium_agent.runtime.diff_preview import (
    render_edit_diff,
    render_patch_diff,
    render_write_preview,
)


def _diff_preview_for(tool_ref: str, args: Dict[str, Any]) -> Optional[str]:
    """Build a human-readable preview for risky tool calls."""
    if tool_ref == "fs.edit":
        path = args.get("path") or "<unknown>"
        return render_edit_diff(path, args.get("old", ""), args.get("new", ""))
    if tool_ref == "fs.write":
        return render_write_preview(args.get("path", "<unknown>"), args.get("content", ""))
    if tool_ref == "patch.apply":
        return render_patch_diff(args.get("patch", ""))
    if tool_ref == "shell.run":
        return f"$ {args.get('command', '')}"
    return None


class HumanGateController:
    """Pluggable approval gate. Mock mode auto-approves; CLI prompts the user."""

    def __init__(self, auto_approve: bool = True) -> None:
        self.auto_approve = auto_approve
        self.pending: List[Dict[str, Any]] = []
        self.last_decision: Optional[bool] = None

    def request(
        self,
        *,
        tool_ref: Optional[str],
        agent_id: Optional[str],
        message: str,
        diff_preview: Optional[str] = None,
    ) -> bool:
        request = {
            "tool_ref": tool_ref,
            "agent_id": agent_id,
            "message": message,
            "diff_preview": diff_preview,
        }
        self.pending.append(request)
        if self.auto_approve:
            self.last_decision = True
            return True
        # Interactive prompt; in tests this branch is patched.
        if diff_preview:
            print("\n--- proposed change ---")
            print(diff_preview)
            print("--- end of preview ---\n")
        try:
            answer = input(f"[approval] {message} [y/N] ").strip().lower()
        except EOFError:
            answer = "n"
        decision = answer in {"y", "yes"}
        self.last_decision = decision
        return decision


class Runtime(BaseModel):
    model_config = ConfigDict(extra="forbid", arbitrary_types_allowed=True)

    run_id: str
    pack_id: Optional[str] = None
    events: EventBus
    models: ModelRegistry
    tools: ToolRegistry
    policy: PolicyEngine
    memory: Any  # MemoryBackend protocol (mock | raganything | custom)
    artifacts: ArtifactGraph
    agents: Dict[str, AgentInstance]
    factory: AgentFactory
    gate: HumanGateController

    # --- node executors ---

    def run_model(self, node: ModelNode, state: Dict[str, Any]) -> Dict[str, Any]:
        instance = self.agents.get(node.agent_ref)
        if instance is None:
            raise KeyError(f"agent '{node.agent_ref}' not instantiated")
        self.events.emit(
            "agent.started",
            {
                "instance_id": instance.instance_id,
                "agent_id": instance.definition.id,
                "node_id": node.id,
            },
        )
        prompt_text = compose_prompt(instance, state)
        agent_tools = self._build_provider_tools_for_agent(instance.definition)
        request = ModelRequest(
            role=instance.definition.role.value,
            agent_id=instance.definition.id,
            prompt=prompt_text,
            state=dict(state),
            expected_keys=node.outputs,
            tools=agent_tools,
            tool_executor=self._make_agent_tool_executor(instance.definition, node),
            output_contract=instance.definition.output_contract,
            trace_emit=self._trace_emit,
        )
        response = self.models.generate(instance.definition.model, request)
        output = response.output
        # Validate against agent output contract if declared.
        contract = instance.definition.output_contract
        if contract:
            errors = contract.validate_payload(output)
            if errors:
                self.events.emit(
                    "agent.failed",
                    {
                        "instance_id": instance.instance_id,
                        "agent_id": instance.definition.id,
                        "errors": errors,
                    },
                )
                raise ValueError(f"agent '{instance.definition.id}' output invalid: {errors}")
        self.events.emit(
            "agent.completed",
            {
                "instance_id": instance.instance_id,
                "agent_id": instance.definition.id,
                "node_id": node.id,
                "outputs": list(output.keys()),
            },
        )
        return output

    def run_tool(self, node: ToolNode, args: Dict[str, Any], state: Dict[str, Any]) -> Dict[str, Any]:
        decision = self.policy.resolve(node.tool_ref, agent_id=node.agent_ref)
        self.events.emit(
            "tool.requested",
            {
                "tool_ref": node.tool_ref,
                "agent_id": node.agent_ref,
                "node_id": node.id,
                "decision": decision.value,
            },
        )
        if decision == PermissionDecision.DENY:
            self.events.emit(
                "tool.denied",
                {"tool_ref": node.tool_ref, "agent_id": node.agent_ref},
            )
            raise PermissionError(f"tool '{node.tool_ref}' denied by policy")
        if decision == PermissionDecision.REQUIRE_APPROVAL:
            approved = self.gate.request(
                tool_ref=node.tool_ref,
                agent_id=node.agent_ref,
                message=f"Approve use of tool '{node.tool_ref}' by agent '{node.agent_ref}'?",
                diff_preview=_diff_preview_for(node.tool_ref, args),
            )
            if not approved:
                self.events.emit(
                    "tool.denied",
                    {"tool_ref": node.tool_ref, "agent_id": node.agent_ref},
                )
                raise PermissionError(f"tool '{node.tool_ref}' not approved")
            self.events.emit(
                "tool.approved",
                {"tool_ref": node.tool_ref, "agent_id": node.agent_ref},
            )
        if not self.tools.has(node.tool_ref):
            raise KeyError(f"tool '{node.tool_ref}' not registered")
        result = self.tools.call(node.tool_ref, **args)
        self.events.emit(
            "tool.completed",
            {"tool_ref": node.tool_ref, "node_id": node.id, "keys": list(result.keys()) if isinstance(result, dict) else []},
        )
        if isinstance(result, dict):
            # Project tool result into declared outputs when names match.
            projected = {}
            for key in node.outputs:
                if key in result:
                    projected[key] = result[key]
            if not projected:
                # Otherwise expose under a single key named after the tool ref.
                projected = {node.outputs[0] if node.outputs else node.tool_ref: result}
            return projected
        return {node.outputs[0] if node.outputs else node.tool_ref: result}

    def run_operator(self, node: OperatorNode, args: Dict[str, Any], state: Dict[str, Any]) -> Dict[str, Any]:
        if node.op == "assign":
            return {k: args.get(k) for k in node.outputs} if node.outputs else dict(args)
        if node.op == "merge":
            base = state.get(node.outputs[0] or "merged", {}) if node.outputs else {}
            base.update(args)
            return {node.outputs[0] if node.outputs else "merged": base}
        if node.op == "select":
            key = args.get("key")
            value = state.get(key)
            return {node.outputs[0] if node.outputs else key: value}
        if node.op == "format":
            template = args.get("template", "")
            text = template.format(**state) if isinstance(template, str) else str(template)
            return {node.outputs[0] if node.outputs else "text": text}
        return {}

    def run_human_gate(self, node: HumanGateNode, state: Dict[str, Any]) -> Dict[str, Any]:
        self.events.emit(
            "human.requested",
            {"node_id": node.id, "purpose": node.purpose, "message": node.message},
        )
        approved = self.gate.request(
            tool_ref=None, agent_id=None, message=node.message
        )
        self.events.emit(
            "human.responded",
            {"node_id": node.id, "approved": approved},
        )
        if not approved:
            raise PermissionError("human gate denied")
        return {"approved": True}

    def run_critic(self, node: CriticNode, state: Dict[str, Any]) -> Dict[str, Any]:
        self.events.emit("critic.started", {"node_id": node.id})
        # Pre-checks: gates that do not reference the LLM verdict.
        verdict = "PASS"
        failures: List[str] = []
        safe_locals = {**state}
        pre_checks = [c for c in node.checks if "verdict" not in c.condition]
        post_checks = [c for c in node.checks if "verdict" in c.condition]
        for check in pre_checks:
            try:
                ok = bool(eval(check.condition, {"__builtins__": {}}, safe_locals))
            except Exception:
                ok = False
            if not ok:
                failures.append(check.id)
                verdict = "FAIL"
                self.events.emit(
                    "gate.failed",
                    {"node_id": node.id, "check_id": check.id, "on_fail": check.on_fail},
                )
        # Allow the critic agent to enrich reasons / override verdict when no gate failed.
        instance = self.agents.get(node.agent_ref)
        reasons: List[str] = []
        if instance is not None:
            prompt_text = compose_prompt(instance, state)
            request = ModelRequest(
                role=instance.definition.role.value,
                agent_id=instance.definition.id,
                prompt=prompt_text,
                state=dict(state),
                expected_keys=["verdict", "reasons"],
            )
            response = self.models.generate(instance.definition.model, request)
            reasons = response.output.get("reasons", []) or []
            if verdict == "PASS":
                verdict = response.output.get("verdict", verdict)
        # Post-checks now have access to the resolved verdict.
        meta_locals = {**state, "verdict": verdict}
        for check in post_checks:
            try:
                ok = bool(eval(check.condition, {"__builtins__": {}}, meta_locals))
            except Exception:
                ok = False
            if not ok:
                failures.append(check.id)
                verdict = "FAIL"
                self.events.emit(
                    "gate.failed",
                    {"node_id": node.id, "check_id": check.id, "on_fail": check.on_fail},
                )
        self.events.emit("critic.completed", {"node_id": node.id, "verdict": verdict})
        return {"verdict": verdict, "reasons": reasons, "critic_failures": failures}

    def run_recovery(self, node: RecoveryNode, state: Dict[str, Any]) -> Dict[str, Any]:
        self.events.emit(
            "recovery.selected",
            {"node_id": node.id, "strategy": node.strategy, "classification": node.classification},
        )
        return {"recovery_strategy": node.strategy}

    # ---- provider integration helpers ----

    def _trace_emit(self, kind: str, payload: Dict[str, Any]) -> None:
        """Trace adapter passed to providers for token / tool / thinking events."""
        try:
            self.events.emit(kind, payload)
        except Exception:  # noqa: BLE001
            pass

    def _build_provider_tools_for_agent(self, definition: Any) -> List[Dict[str, Any]]:
        """Translate the agent's declared tools into Anthropic-compatible specs.

        Each tool ref `<server>.<tool>` becomes `{name, description, input_schema}`.
        Tools with explicit `input_schema` on their `ToolDescriptor` use that; the
        rest get a permissive open-object schema.
        """
        specs: List[Dict[str, Any]] = []
        for tool_ref in getattr(definition, "tools", []) or []:
            if not self.tools.has(tool_ref):
                continue
            descriptor = self.tools.descriptor(tool_ref)
            schema = getattr(descriptor, "input_schema", None) or {
                "type": "object",
                "properties": {},
                "additionalProperties": True,
            }
            name = tool_ref.replace(".", "__")
            specs.append(
                {
                    "name": name,
                    "description": getattr(descriptor, "description", "") or tool_ref,
                    "input_schema": schema,
                }
            )
        return specs

    def _make_agent_tool_executor(
        self, definition: Any, node: ModelNode
    ) -> Any:
        """Return a synchronous tool executor closure used by the model provider.

        Translates the Anthropic-namespaced tool name back into the Neuronium
        `<server>.<tool>` ref, resolves the policy (with human gate for
        `require_approval`), and invokes the tool through the registry.
        """
        agent_id = definition.id

        def _executor(tool_name: str, tool_input: Dict[str, Any]) -> Any:
            ref = tool_name.replace("__", ".")
            decision = self.policy.resolve(ref, agent_id=agent_id)
            self.events.emit(
                "tool.requested",
                {
                    "tool_ref": ref,
                    "agent_id": agent_id,
                    "node_id": node.id,
                    "decision": decision.value,
                    "via": "model_loop",
                },
            )
            if decision == PermissionDecision.DENY:
                self.events.emit("tool.denied", {"tool_ref": ref, "agent_id": agent_id})
                raise PermissionError(f"tool '{ref}' denied by policy")
            if decision == PermissionDecision.REQUIRE_APPROVAL:
                preview = _diff_preview_for(ref, tool_input)
                approved = self.gate.request(
                    tool_ref=ref,
                    agent_id=agent_id,
                    message=(
                        f"Approve use of tool '{ref}' by agent '{agent_id}' "
                        "(requested by the model)?"
                    ),
                    diff_preview=preview,
                )
                if not approved:
                    self.events.emit(
                        "tool.denied",
                        {"tool_ref": ref, "agent_id": agent_id, "by": "human"},
                    )
                    raise PermissionError(f"tool '{ref}' not approved")
                self.events.emit(
                    "tool.approved", {"tool_ref": ref, "agent_id": agent_id}
                )
            if not self.tools.has(ref):
                raise KeyError(f"tool '{ref}' not registered")
            result = self.tools.call(ref, **tool_input)
            self.events.emit(
                "tool.completed",
                {
                    "tool_ref": ref,
                    "via": "model_loop",
                    "agent_id": agent_id,
                    "keys": list(result.keys()) if isinstance(result, dict) else [],
                },
            )
            return result

        return _executor

    def run_terminal(self, node: TerminalNode, state: Dict[str, Any]) -> Dict[str, Any]:
        report = render_final_outcome(state, template_id=node.outcome_template)
        artifact = Artifact(
            id=f"final_report:{node.id}",
            kind="report",
            name="final_report.md",
            content=report,
        )
        self.artifacts.add(artifact)
        self.events.emit(
            "outcome.produced",
            {"node_id": node.id, "artifact_id": artifact.id, "length": len(report)},
        )
        return {"final_report": report, "final_artifact_id": artifact.id}


def render_final_outcome(state: Dict[str, Any], template_id: Optional[str] = None) -> str:
    lines = ["# Final Outcome", ""]
    if "plan" in state:
        lines.append("## Plan")
        for step in state.get("plan", []):
            lines.append(f"- {step}")
        lines.append("")
    if "root_cause" in state:
        lines.append("## Root cause")
        lines.append(str(state["root_cause"]))
        lines.append("")
    if "changed_files" in state:
        lines.append("## Changed files")
        for f in state.get("changed_files", []):
            lines.append(f"- {f}")
        lines.append("")
    if "test_result" in state:
        lines.append("## Test result")
        tr = state["test_result"]
        if isinstance(tr, dict):
            lines.append(f"- status: {tr.get('status')}")
            lines.append(f"- summary: {tr.get('summary')}")
        else:
            lines.append(str(tr))
        lines.append("")
    if "verdict" in state:
        lines.append("## Verdict")
        lines.append(f"- {state.get('verdict')}")
        for reason in state.get("reasons", []) or []:
            lines.append(f"  - {reason}")
        lines.append("")
    if "shortlist" in state:
        lines.append("## Shortlist")
        for c in state.get("shortlist", []):
            lines.append(f"- {c}")
        lines.append("")
    if "campaign_plan" in state:
        lines.append("## Campaign plan")
        lines.append(str(state["campaign_plan"]))
        lines.append("")
    if "milestones" in state:
        lines.append("## Milestones")
        for m in state.get("milestones", []):
            lines.append(f"- {m}")
        lines.append("")
    return "\n".join(lines)


def build_default_runtime(
    run_id: str,
    *,
    pack_id: Optional[str],
    events: EventBus,
    policy: PolicyEngine,
    agent_instances: Dict[str, AgentInstance],
    factory: AgentFactory,
    auto_approve: bool = True,
    force_failure_first: bool = False,
    memory: Optional[MemoryBackend] = None,
    memory_config: Optional[MemoryConfig] = None,
    provider: str = "mock",
    provider_options: Optional[Dict[str, Any]] = None,
    models: Optional[ModelRegistry] = None,
    real_tools_config: Optional[RealToolsConfig] = None,
) -> Runtime:
    if models is None:
        models = default_registry(
            force_failure_first=force_failure_first,
            provider=provider,
            provider_options=provider_options or {},
        )
    tool_registry = ToolRegistry()
    if real_tools_config is not None:
        # Real tools take precedence; mock tools fill in the gaps for refs the
        # real implementation does not yet cover (marketing/HR mock tools).
        MockMCP().register_default(tool_registry)
        register_real_tools(tool_registry, real_tools_config)
    else:
        MockMCP().register_default(tool_registry)
    if memory is None:
        try:
            memory = build_backend(memory_config or MemoryConfig())
        except Exception:  # noqa: BLE001
            memory = MockGraphRAG()
    artifacts = ArtifactGraph()
    gate = HumanGateController(auto_approve=auto_approve)
    return Runtime(
        run_id=run_id,
        pack_id=pack_id,
        events=events,
        models=models,
        tools=tool_registry,
        policy=policy,
        memory=memory,
        artifacts=artifacts,
        agents=agent_instances,
        factory=factory,
        gate=gate,
    )
