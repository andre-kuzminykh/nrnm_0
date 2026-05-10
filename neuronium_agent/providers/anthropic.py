"""Anthropic provider for Neuronium.

Implements `ModelProvider` against the Anthropic SDK with the defaults the
official Claude API skill prescribes:

- Model: Claude Opus 4.7 (`claude-opus-4-7`) by default.
- Adaptive thinking only (`thinking={"type": "adaptive"}`); `temperature` /
  `top_p` / `top_k` are removed (would return 400 on Opus 4.7).
- `thinking.display="summarized"` so reasoning blocks carry visible text into
  Neuronium's trace; default on Opus 4.7 is `"omitted"`.
- `effort` per role: `xhigh` for coding/agentic, `high` for general intelligence,
  `medium` for fast/cheap, `low` for latency-sensitive paths.
- Streaming under the hood via `client.messages.stream(...).get_final_message()`,
  which prevents SDK HTTP timeouts on long thinking + tool-use loops.
- Prompt caching: top-level `cache_control={"type": "ephemeral"}` so the stable
  system prefix (frozen prompt files + agent goal + contract) is cached and the
  volatile per-turn state lives in the user message after the breakpoint.
- Structured output: agent's `OutputContract` is translated into
  `output_config.format = {"type": "json_schema", "schema": ...}` when no
  tool-use is in flight.
- Tool-use loop: when the model emits `tool_use`, the provider calls the
  injected `tool_executor` and feeds the result back as a `tool_result` block,
  iterating until `stop_reason == "end_turn"` or a hard cap.
- Optional dependency: when `anthropic` is not installed the provider remains
  importable, reports `ready=False`, and `generate` raises a clear error.
- CI safety: tests inject a synchronous fake client; no live API key required.
"""

from __future__ import annotations

import importlib
import json
import os
from contextlib import contextmanager
from typing import Any, Callable, Dict, Iterator, List, Optional, Tuple

from neuronium_agent.providers.base import (
    ModelProvider,
    ModelRequest,
    ModelResponse,
)


DEFAULT_MODEL = "claude-opus-4-7"


def _try_import_anthropic() -> Optional[Any]:
    try:
        return importlib.import_module("anthropic")
    except Exception:  # noqa: BLE001 — optional dep
        return None


def _effort_for_role(role: str) -> str:
    """Map a Neuronium role to an Anthropic `output_config.effort` value.

    Per the Claude API skill: `xhigh` is the best setting for coding and
    agentic work; `high` is the recommended minimum for intelligence-sensitive
    tasks; `low` for short, latency-sensitive paths; `medium` for cost-sensitive
    work.
    """
    role_lc = role.lower()
    if role_lc in {"critic", "planner", "researcher", "designer"}:
        return "xhigh"
    if role_lc in {"executor", "recovery", "curator"}:
        return "high"
    if role_lc == "fast":
        return "low"
    return "high"


def _thinking_for_role(role: str) -> Dict[str, str]:
    """Adaptive thinking with summarized display, except for latency-sensitive
    roles where thinking is disabled."""
    if role.lower() in {"fast"}:
        return {"type": "disabled"}
    return {"type": "adaptive", "display": "summarized"}


def _contract_to_schema(contract: Any) -> Optional[Dict[str, Any]]:
    """Translate Neuronium's OutputContract into a JSON schema fragment.

    Returns `None` when no usable contract is available.
    """
    if contract is None:
        return None
    contract_type = getattr(contract, "type", None) or "object"
    required = list(getattr(contract, "required", []) or [])
    properties = dict(getattr(contract, "properties", {}) or {})
    if not properties and required:
        # Synthesize a permissive property entry for each required key so the
        # JSON schema validates structurally without overconstraining content.
        for key in required:
            properties[key] = {}
    if not properties:
        return None
    return {
        "type": contract_type,
        "properties": properties,
        "required": required,
        "additionalProperties": True,
    }


class AnthropicProvider:
    """`ModelProvider` backed by the official Anthropic SDK."""

    name = "anthropic"

    def __init__(
        self,
        *,
        model: str = DEFAULT_MODEL,
        max_tokens: int = 16000,
        enable_prompt_cache: bool = True,
        client: Optional[Any] = None,
        client_factory: Optional[Callable[[], Any]] = None,
        max_tool_iterations: int = 8,
        api_key_env: str = "ANTHROPIC_API_KEY",
        mock_mode: bool = False,
    ) -> None:
        self.model_id = model
        self.max_tokens = max_tokens
        self.enable_prompt_cache = enable_prompt_cache
        self.max_tool_iterations = max_tool_iterations
        self.api_key_env = api_key_env
        self.mock_mode = mock_mode
        self._anthropic_module = _try_import_anthropic()
        self._init_error: Optional[str] = None
        self._client: Optional[Any] = client
        self._mock_delegate: Optional[Any] = None
        if mock_mode:
            from neuronium_agent.providers.mock import MockModelProvider

            self._mock_delegate = MockModelProvider()
        elif self._client is None and client_factory is not None:
            try:
                self._client = client_factory()
            except Exception as exc:  # noqa: BLE001
                self._init_error = f"client_factory failed: {exc}"
        elif self._client is None and self._anthropic_module is not None:
            try:
                self._client = self._build_default_client()
            except Exception as exc:  # noqa: BLE001
                self._init_error = f"default client init failed: {exc}"
        elif self._client is None and self._anthropic_module is None:
            self._init_error = (
                "anthropic package not installed; install with "
                "`pip install 'neuronium-agent[anthropic]'` or pass `client_factory`"
            )

    # ---- properties ----

    @property
    def ready(self) -> bool:
        if self.mock_mode:
            return True
        return self._client is not None and self._init_error is None

    def supports(self, role: str) -> bool:
        return True

    def diagnostics(self) -> Dict[str, Any]:
        return {
            "provider": self.name,
            "ready": self.ready,
            "anthropic_installed": self._anthropic_module is not None,
            "model": self.model_id,
            "mock_mode": self.mock_mode,
            "init_error": self._init_error,
        }

    # ---- main entry point ----

    def generate(self, request: ModelRequest) -> ModelResponse:
        if self.mock_mode and self._mock_delegate is not None:
            response = self._mock_delegate.generate(request)
            # Tag the response so trace shows the simulated provider/model.
            return ModelResponse(
                role=response.role,
                agent_id=response.agent_id,
                output=response.output,
                usage={"input_tokens": 0, "output_tokens": 0, "mock": 1},
                thinking_summary=None,
                stop_reason="end_turn",
            )
        if not self.ready:
            raise RuntimeError(
                f"AnthropicProvider not ready: {self._init_error}"
            )

        system_blocks = self._build_system(request)
        messages: List[Dict[str, Any]] = [self._build_initial_user(request)]
        tools = list(request.tools or [])
        contract_schema = _contract_to_schema(request.output_contract)
        effort = _effort_for_role(request.role)
        thinking_cfg = _thinking_for_role(request.role)
        tool_executor = request.tool_executor

        iterations = 0
        final_output: Dict[str, Any] = {}
        usage_acc: Dict[str, int] = {}
        thinking_chunks: List[str] = []
        stop_reason: Optional[str] = None

        while iterations < self.max_tool_iterations:
            iterations += 1
            params = self._build_request_params(
                system_blocks=system_blocks,
                messages=messages,
                tools=tools,
                tool_executor=tool_executor,
                contract_schema=contract_schema,
                effort=effort,
                thinking_cfg=thinking_cfg,
            )
            message = self._call_streaming(params, request)
            stop_reason = getattr(message, "stop_reason", None)
            _accumulate_usage(usage_acc, getattr(message, "usage", None))
            for block in getattr(message, "content", []) or []:
                btype = getattr(block, "type", None)
                if btype == "thinking":
                    text = getattr(block, "thinking", "") or ""
                    if text:
                        thinking_chunks.append(text)
            if stop_reason == "tool_use":
                tool_uses = [
                    b for b in getattr(message, "content", []) or []
                    if getattr(b, "type", None) == "tool_use"
                ]
                if not tool_uses or tool_executor is None:
                    # Nothing to do; treat as end_turn-with-text.
                    final_output = self._parse_final_output(message, request)
                    break
                messages.append({"role": "assistant", "content": message.content})
                tool_results = []
                for use in tool_uses:
                    name = getattr(use, "name", "")
                    use_id = getattr(use, "id", "")
                    inputs = getattr(use, "input", {}) or {}
                    if request.trace_emit:
                        try:
                            request.trace_emit(
                                "model.tool_call",
                                {"agent_id": request.agent_id, "name": name, "id": use_id, "input_keys": list(inputs.keys())},
                            )
                        except Exception:  # noqa: BLE001
                            pass
                    try:
                        result = tool_executor(name, dict(inputs))
                        tool_results.append(
                            {
                                "type": "tool_result",
                                "tool_use_id": use_id,
                                "content": _stringify_tool_result(result),
                            }
                        )
                    except Exception as exc:  # noqa: BLE001
                        tool_results.append(
                            {
                                "type": "tool_result",
                                "tool_use_id": use_id,
                                "content": f"tool error: {exc}",
                                "is_error": True,
                            }
                        )
                messages.append({"role": "user", "content": tool_results})
                continue
            # Any other stop_reason → final output.
            final_output = self._parse_final_output(message, request)
            break
        else:  # while-else: iteration cap hit without break.
            final_output = {"error": "tool_iteration_cap_exceeded"}

        return ModelResponse(
            role=request.role,
            agent_id=request.agent_id,
            output=final_output,
            usage=usage_acc,
            thinking_summary=("\n".join(thinking_chunks).strip() or None),
            stop_reason=stop_reason,
        )

    # ---- system + initial user ----

    def _build_system(self, request: ModelRequest) -> List[Dict[str, Any]]:
        """Build system blocks with prompt caching on the last block.

        The composed prompt (agent header + goal + contract + body) is stable
        for the lifetime of a pack, so it caches cleanly. State keys live in
        the user message that follows, after the cache breakpoint.
        """
        body = request.prompt or ""
        blocks: List[Dict[str, Any]] = [{"type": "text", "text": body}]
        if self.enable_prompt_cache and body.strip():
            blocks[-1]["cache_control"] = {"type": "ephemeral"}
        return blocks

    def _build_initial_user(self, request: ModelRequest) -> Dict[str, Any]:
        """The user turn carries the per-run state — never cache it."""
        # Sort keys for determinism; secrets are already redacted upstream.
        sorted_state = {
            k: request.state[k]
            for k in sorted(request.state.keys(), key=str)
        }
        expected = ", ".join(request.expected_keys) or "(any)"
        contract_required = (
            ", ".join(getattr(request.output_contract, "required", []) or [])
            if request.output_contract
            else ""
        )
        prelude = (
            f"# Run context\n"
            f"Agent: {request.agent_id} (role: {request.role})\n"
            f"Expected output keys: {expected}\n"
        )
        if contract_required:
            prelude += f"Required fields: {contract_required}\n"
        prelude += (
            "\nReturn ONLY a JSON object containing the expected output keys. "
            "Do not include surrounding prose."
        )
        try:
            state_block = json.dumps(sorted_state, default=str, indent=2)
        except Exception:  # noqa: BLE001
            state_block = str(sorted_state)
        return {
            "role": "user",
            "content": [
                {"type": "text", "text": prelude},
                {"type": "text", "text": f"## State\n```json\n{state_block}\n```"},
            ],
        }

    # ---- request building ----

    def _build_request_params(
        self,
        *,
        system_blocks: List[Dict[str, Any]],
        messages: List[Dict[str, Any]],
        tools: List[Dict[str, Any]],
        tool_executor: Optional[Any],
        contract_schema: Optional[Dict[str, Any]],
        effort: str,
        thinking_cfg: Dict[str, str],
    ) -> Dict[str, Any]:
        params: Dict[str, Any] = {
            "model": self.model_id,
            "max_tokens": self.max_tokens,
            "system": system_blocks,
            "messages": messages,
            "thinking": thinking_cfg,
            "output_config": {"effort": effort},
        }
        if tools and tool_executor is not None:
            params["tools"] = tools
            # When tools are available, the schema is enforced when the model
            # finally responds with text — combining is supported per docs.
            if contract_schema is not None:
                params["output_config"]["format"] = {
                    "type": "json_schema",
                    "schema": contract_schema,
                }
        elif contract_schema is not None:
            params["output_config"]["format"] = {
                "type": "json_schema",
                "schema": contract_schema,
            }
        return params

    # ---- streaming call ----

    def _call_streaming(self, params: Dict[str, Any], request: ModelRequest) -> Any:
        """Use `client.messages.stream(...).get_final_message()` for timeout safety."""
        client = self._client
        if client is None:
            raise RuntimeError("anthropic client missing")
        # Optionally emit a token stream for callers that want it; default no-op.
        with client.messages.stream(**params) as stream:
            if request.trace_emit:
                for event in stream:
                    try:
                        kind = getattr(event, "type", None)
                        if kind == "content_block_delta":
                            delta = getattr(event, "delta", None)
                            dtext = getattr(delta, "text", None) if delta else None
                            if dtext:
                                request.trace_emit(
                                    "model.token",
                                    {"agent_id": request.agent_id, "text": dtext},
                                )
                    except Exception:  # noqa: BLE001
                        pass
            return stream.get_final_message()

    # ---- response parsing ----

    def _parse_final_output(self, message: Any, request: ModelRequest) -> Dict[str, Any]:
        """Pull JSON from the final assistant text block; fall back to raw text."""
        for block in getattr(message, "content", []) or []:
            if getattr(block, "type", None) == "text":
                text = getattr(block, "text", "") or ""
                parsed = _try_parse_json(text)
                if isinstance(parsed, dict):
                    if request.expected_keys:
                        filtered = {
                            k: parsed[k] for k in request.expected_keys if k in parsed
                        }
                        for k, v in parsed.items():
                            filtered.setdefault(k, v)
                        return filtered
                    return parsed
        # No JSON parsed — return raw text under "result".
        text_chunks = [
            getattr(b, "text", "")
            for b in getattr(message, "content", []) or []
            if getattr(b, "type", None) == "text"
        ]
        return {"text": "".join(text_chunks)}

    # ---- default client construction ----

    def _build_default_client(self) -> Any:
        module = self._anthropic_module
        if module is None:
            raise RuntimeError("anthropic is not importable")
        if os.environ.get(self.api_key_env) is None:
            raise RuntimeError(
                f"{self.api_key_env} not set in environment; pass `client_factory` "
                "or set the env var"
            )
        Anthropic = getattr(module, "Anthropic")
        return Anthropic()


# ---- helpers ----


def _accumulate_usage(acc: Dict[str, int], usage: Any) -> None:
    if usage is None:
        return
    for key in (
        "input_tokens",
        "output_tokens",
        "cache_creation_input_tokens",
        "cache_read_input_tokens",
    ):
        value = getattr(usage, key, None)
        if value is None:
            continue
        acc[key] = int(acc.get(key, 0)) + int(value)


def _try_parse_json(text: str) -> Any:
    text = (text or "").strip()
    if not text:
        return None
    # Strip optional fences (```json ... ```).
    if text.startswith("```"):
        text = text.split("\n", 1)[-1] if "\n" in text else text
        if text.endswith("```"):
            text = text[: -3].rstrip()
    try:
        return json.loads(text)
    except Exception:  # noqa: BLE001
        pass
    # Best-effort: extract the first top-level JSON object.
    depth = 0
    start = None
    for i, ch in enumerate(text):
        if ch == "{":
            if depth == 0:
                start = i
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0 and start is not None:
                candidate = text[start : i + 1]
                try:
                    return json.loads(candidate)
                except Exception:  # noqa: BLE001
                    continue
    return None


def _stringify_tool_result(result: Any) -> str:
    if isinstance(result, str):
        return result
    try:
        return json.dumps(result, default=str)
    except Exception:  # noqa: BLE001
        return str(result)
