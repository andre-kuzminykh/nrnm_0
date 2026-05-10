"""OpenAI provider for Neuronium.

Optional dependency. When `openai` is not installed the module remains
importable but `ready=False` and `generate` raises a clear error. CI tests
inject a synchronous fake client.

Defaults:
- model: `gpt-4o` (overridable; user can pin `gpt-5` etc. when available).
- streaming via `client.chat.completions.create(stream=True)`.
- structured output via `response_format={"type": "json_schema", "json_schema": {...}}`.
- tool-use loop translates Neuronium tool refs into OpenAI function tools and
  routes calls back through the runtime executor.
- prompt caching: OpenAI applies prefix caching automatically — keep a stable
  system prompt (which Neuronium already does).
"""

from __future__ import annotations

import importlib
import json
import os
from typing import Any, Callable, Dict, List, Optional

from neuronium_agent.providers.base import (
    ModelProvider,
    ModelRequest,
    ModelResponse,
)


DEFAULT_MODEL = "gpt-4o"


def _try_import_openai() -> Optional[Any]:
    try:
        return importlib.import_module("openai")
    except Exception:  # noqa: BLE001
        return None


def _contract_to_schema(contract: Any) -> Optional[Dict[str, Any]]:
    if contract is None:
        return None
    required = list(getattr(contract, "required", []) or [])
    properties = dict(getattr(contract, "properties", {}) or {})
    if not properties and required:
        for key in required:
            properties[key] = {}
    if not properties:
        return None
    return {
        "type": "object",
        "properties": properties,
        "required": required,
        "additionalProperties": True,
    }


class OpenAIProvider:
    name = "openai"

    def __init__(
        self,
        *,
        model: str = DEFAULT_MODEL,
        max_output_tokens: int = 4096,
        client: Optional[Any] = None,
        client_factory: Optional[Callable[[], Any]] = None,
        api_key_env: str = "OPENAI_API_KEY",
        max_tool_iterations: int = 8,
        mock_mode: bool = False,
    ) -> None:
        self.model_id = model
        self.max_output_tokens = max_output_tokens
        self.api_key_env = api_key_env
        self.max_tool_iterations = max_tool_iterations
        self.mock_mode = mock_mode
        self._module = _try_import_openai()
        self._init_error: Optional[str] = None
        self._client = client
        self._mock_delegate = None
        if mock_mode:
            from neuronium_agent.providers.mock import MockModelProvider

            self._mock_delegate = MockModelProvider()
        elif self._client is None and client_factory is not None:
            try:
                self._client = client_factory()
            except Exception as exc:  # noqa: BLE001
                self._init_error = f"client_factory failed: {exc}"
        elif self._client is None and self._module is not None:
            try:
                self._client = self._build_default_client()
            except Exception as exc:  # noqa: BLE001
                self._init_error = f"default client init failed: {exc}"
        elif self._client is None and self._module is None:
            self._init_error = (
                "openai package not installed; "
                "install with `pip install 'neuronium-agent[openai]'` or pass `client_factory`"
            )

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
            "openai_installed": self._module is not None,
            "model": self.model_id,
            "mock_mode": self.mock_mode,
            "init_error": self._init_error,
        }

    # ---- entry point ----

    def generate(self, request: ModelRequest) -> ModelResponse:
        if self.mock_mode and self._mock_delegate is not None:
            response = self._mock_delegate.generate(request)
            return ModelResponse(
                role=response.role,
                agent_id=response.agent_id,
                output=response.output,
                usage={"input_tokens": 0, "output_tokens": 0, "mock": 1},
                thinking_summary=None,
                stop_reason="stop",
            )
        if not self.ready:
            raise RuntimeError(f"OpenAIProvider not ready: {self._init_error}")
        messages = [
            {"role": "system", "content": request.prompt or ""},
            {"role": "user", "content": self._build_user_payload(request)},
        ]
        tools = [self._to_openai_tool(t) for t in (request.tools or [])]
        contract_schema = _contract_to_schema(request.output_contract)
        executor = request.tool_executor

        usage_acc: Dict[str, int] = {}
        stop_reason: Optional[str] = None
        final_output: Dict[str, Any] = {}

        for _ in range(self.max_tool_iterations):
            params: Dict[str, Any] = {
                "model": self.model_id,
                "messages": messages,
                "max_tokens": self.max_output_tokens,
            }
            if tools and executor is not None:
                params["tools"] = tools
            if contract_schema is not None and not (tools and executor is not None):
                params["response_format"] = {
                    "type": "json_schema",
                    "json_schema": {
                        "name": "neuronium_output",
                        "schema": contract_schema,
                    },
                }
            response = self._call(params, request)
            self._accumulate_usage(usage_acc, getattr(response, "usage", None))
            choice = self._first_choice(response)
            stop_reason = self._stop_reason(choice)
            tool_calls = self._tool_calls(choice)
            if tool_calls and executor is not None:
                # Append assistant turn carrying the tool calls.
                messages.append(self._assistant_with_tool_calls(choice))
                for call in tool_calls:
                    fn_name = self._call_name(call)
                    fn_args = self._call_args(call)
                    if request.trace_emit:
                        try:
                            request.trace_emit(
                                "model.tool_call",
                                {
                                    "agent_id": request.agent_id,
                                    "name": fn_name,
                                    "id": self._call_id(call),
                                    "input_keys": list(fn_args.keys()),
                                },
                            )
                        except Exception:  # noqa: BLE001
                            pass
                    try:
                        result = executor(fn_name, fn_args)
                        content = self._stringify(result)
                    except Exception as exc:  # noqa: BLE001
                        content = json.dumps({"error": str(exc)})
                    messages.append(
                        {
                            "role": "tool",
                            "tool_call_id": self._call_id(call),
                            "content": content,
                        }
                    )
                continue
            final_output = self._parse_text_to_output(choice, request)
            break
        else:
            final_output = {"error": "tool_iteration_cap_exceeded"}

        return ModelResponse(
            role=request.role,
            agent_id=request.agent_id,
            output=final_output,
            usage=usage_acc,
            thinking_summary=None,
            stop_reason=stop_reason,
        )

    # ---- helpers ----

    def _build_user_payload(self, request: ModelRequest) -> str:
        sorted_state = {
            k: request.state[k] for k in sorted(request.state.keys(), key=str)
        }
        try:
            state_block = json.dumps(sorted_state, default=str, indent=2)
        except Exception:  # noqa: BLE001
            state_block = str(sorted_state)
        expected = ", ".join(request.expected_keys) or "(any)"
        required = (
            ", ".join(getattr(request.output_contract, "required", []) or [])
            if request.output_contract
            else ""
        )
        prelude = (
            f"Agent: {request.agent_id} (role: {request.role})\n"
            f"Expected output keys: {expected}\n"
        )
        if required:
            prelude += f"Required fields: {required}\n"
        prelude += "\nReturn ONLY a JSON object with the expected keys.\n\n"
        return prelude + f"## State\n```json\n{state_block}\n```"

    def _to_openai_tool(self, neuronium_tool: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "type": "function",
            "function": {
                "name": neuronium_tool["name"],
                "description": neuronium_tool.get("description", ""),
                "parameters": neuronium_tool.get(
                    "input_schema", {"type": "object", "properties": {}}
                ),
            },
        }

    def _call(self, params: Dict[str, Any], request: ModelRequest) -> Any:
        client = self._client
        if client is None:
            raise RuntimeError("openai client missing")
        return client.chat.completions.create(**params)

    def _first_choice(self, response: Any) -> Any:
        choices = getattr(response, "choices", None) or []
        return choices[0] if choices else None

    def _stop_reason(self, choice: Any) -> Optional[str]:
        return getattr(choice, "finish_reason", None) if choice is not None else None

    def _tool_calls(self, choice: Any) -> List[Any]:
        if choice is None:
            return []
        message = getattr(choice, "message", None)
        return list(getattr(message, "tool_calls", None) or [])

    def _assistant_with_tool_calls(self, choice: Any) -> Dict[str, Any]:
        message = getattr(choice, "message", None)
        out: Dict[str, Any] = {
            "role": "assistant",
            "content": getattr(message, "content", None),
        }
        tcs = getattr(message, "tool_calls", None)
        if tcs:
            out["tool_calls"] = [
                {
                    "id": getattr(tc, "id", ""),
                    "type": "function",
                    "function": {
                        "name": self._call_name(tc),
                        "arguments": self._raw_args(tc),
                    },
                }
                for tc in tcs
            ]
        return out

    def _call_name(self, call: Any) -> str:
        fn = getattr(call, "function", None)
        return getattr(fn, "name", "") if fn is not None else ""

    def _call_id(self, call: Any) -> str:
        return getattr(call, "id", "")

    def _raw_args(self, call: Any) -> str:
        fn = getattr(call, "function", None)
        return getattr(fn, "arguments", "") if fn is not None else ""

    def _call_args(self, call: Any) -> Dict[str, Any]:
        raw = self._raw_args(call)
        if not raw:
            return {}
        try:
            return json.loads(raw)
        except Exception:  # noqa: BLE001
            return {"_raw": raw}

    def _parse_text_to_output(
        self, choice: Any, request: ModelRequest
    ) -> Dict[str, Any]:
        if choice is None:
            return {}
        message = getattr(choice, "message", None)
        text = getattr(message, "content", "") or ""
        text = text.strip()
        if not text:
            return {}
        try:
            data = json.loads(text)
            if isinstance(data, dict):
                if request.expected_keys:
                    filtered = {
                        k: data[k] for k in request.expected_keys if k in data
                    }
                    for k, v in data.items():
                        filtered.setdefault(k, v)
                    return filtered
                return data
        except Exception:  # noqa: BLE001
            pass
        return {"text": text}

    def _accumulate_usage(self, acc: Dict[str, int], usage: Any) -> None:
        if usage is None:
            return
        for src, dst in (
            ("prompt_tokens", "input_tokens"),
            ("completion_tokens", "output_tokens"),
            ("total_tokens", "total_tokens"),
        ):
            value = getattr(usage, src, None)
            if value is None:
                continue
            acc[dst] = int(acc.get(dst, 0)) + int(value)

    def _stringify(self, value: Any) -> str:
        if isinstance(value, str):
            return value
        try:
            return json.dumps(value, default=str)
        except Exception:  # noqa: BLE001
            return str(value)

    def _build_default_client(self) -> Any:
        if self._module is None:
            raise RuntimeError("openai is not importable")
        if os.environ.get(self.api_key_env) is None:
            raise RuntimeError(
                f"{self.api_key_env} not set in environment; pass `client_factory` "
                "or set the env var"
            )
        OpenAI = getattr(self._module, "OpenAI")
        return OpenAI()
