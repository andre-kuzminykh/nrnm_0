"""Google Gemini provider for Neuronium.

Optional dependency on `google.genai`. Falls back gracefully when missing.
Defaults to `gemini-2.5-pro` for long-context / multimodal reasoning.
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


DEFAULT_MODEL = "gemini-2.5-pro"


def _try_import_genai() -> Optional[Any]:
    for candidate in ("google.genai", "google.generativeai"):
        try:
            return importlib.import_module(candidate)
        except Exception:  # noqa: BLE001
            continue
    return None


class GeminiProvider:
    name = "gemini"

    def __init__(
        self,
        *,
        model: str = DEFAULT_MODEL,
        max_output_tokens: int = 4096,
        client: Optional[Any] = None,
        client_factory: Optional[Callable[[], Any]] = None,
        api_key_env: str = "GEMINI_API_KEY",
        max_tool_iterations: int = 8,
    ) -> None:
        self.model_id = model
        self.max_output_tokens = max_output_tokens
        self.api_key_env = api_key_env
        self.max_tool_iterations = max_tool_iterations
        self._module = _try_import_genai()
        self._init_error: Optional[str] = None
        self._client = client
        if self._client is None and client_factory is not None:
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
                "google-genai package not installed; "
                "install with `pip install 'neuronium-agent[gemini]'` or pass `client_factory`"
            )

    @property
    def ready(self) -> bool:
        return self._client is not None and self._init_error is None

    def supports(self, role: str) -> bool:
        return True

    def diagnostics(self) -> Dict[str, Any]:
        return {
            "provider": self.name,
            "ready": self.ready,
            "google_genai_installed": self._module is not None,
            "model": self.model_id,
            "init_error": self._init_error,
        }

    def generate(self, request: ModelRequest) -> ModelResponse:
        if not self.ready:
            raise RuntimeError(f"GeminiProvider not ready: {self._init_error}")
        contents: List[Dict[str, Any]] = [
            {"role": "user", "parts": [{"text": self._compose_user_text(request)}]},
        ]
        executor = request.tool_executor
        tools = self._tools_payload(request.tools or [])
        usage_acc: Dict[str, int] = {}
        stop_reason: Optional[str] = None
        final_output: Dict[str, Any] = {}

        for _ in range(self.max_tool_iterations):
            params: Dict[str, Any] = {
                "model": self.model_id,
                "contents": contents,
                "system_instruction": request.prompt or "",
                "config": {"max_output_tokens": self.max_output_tokens},
            }
            if tools and executor is not None:
                params["tools"] = tools
            response = self._call(params, request)
            self._accumulate_usage(usage_acc, getattr(response, "usage_metadata", None))
            candidate = self._first_candidate(response)
            stop_reason = self._stop_reason(candidate)
            calls = self._function_calls(candidate)
            if calls and executor is not None:
                contents.append(
                    {"role": "model", "parts": [{"function_call": fc} for fc in calls]}
                )
                resp_parts = []
                for call in calls:
                    name = call.get("name", "")
                    args = call.get("args", {}) or {}
                    if request.trace_emit:
                        try:
                            request.trace_emit(
                                "model.tool_call",
                                {
                                    "agent_id": request.agent_id,
                                    "name": name,
                                    "id": call.get("id") or name,
                                    "input_keys": list(args.keys()),
                                },
                            )
                        except Exception:  # noqa: BLE001
                            pass
                    try:
                        result = executor(name, dict(args))
                        payload = {"result": result}
                    except Exception as exc:  # noqa: BLE001
                        payload = {"error": str(exc)}
                    resp_parts.append(
                        {
                            "function_response": {
                                "name": name,
                                "response": payload,
                            }
                        }
                    )
                contents.append({"role": "user", "parts": resp_parts})
                continue
            final_output = self._parse_text(candidate, request)
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

    def _compose_user_text(self, request: ModelRequest) -> str:
        try:
            state = json.dumps(
                {k: request.state[k] for k in sorted(request.state.keys(), key=str)},
                default=str,
                indent=2,
            )
        except Exception:  # noqa: BLE001
            state = str(request.state)
        expected = ", ".join(request.expected_keys) or "(any)"
        return (
            f"Agent: {request.agent_id} (role: {request.role})\n"
            f"Expected output keys: {expected}\n\n"
            "Return ONLY a JSON object with those keys.\n\n"
            f"## State\n```json\n{state}\n```"
        )

    def _tools_payload(self, tools: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        if not tools:
            return []
        decls = []
        for t in tools:
            decls.append(
                {
                    "name": t.get("name", ""),
                    "description": t.get("description", ""),
                    "parameters": t.get("input_schema", {"type": "object"}),
                }
            )
        return [{"function_declarations": decls}]

    def _call(self, params: Dict[str, Any], request: ModelRequest) -> Any:
        client = self._client
        if client is None:
            raise RuntimeError("gemini client missing")
        # Both google.genai (new) and google.generativeai (legacy) expose
        # `client.models.generate_content(...)`.
        models = getattr(client, "models", None)
        if models is not None and hasattr(models, "generate_content"):
            return models.generate_content(**params)
        if hasattr(client, "generate_content"):
            return client.generate_content(**params)
        raise RuntimeError("gemini client lacks `models.generate_content` / `generate_content`")

    def _first_candidate(self, response: Any) -> Any:
        candidates = getattr(response, "candidates", None) or []
        return candidates[0] if candidates else None

    def _stop_reason(self, candidate: Any) -> Optional[str]:
        return getattr(candidate, "finish_reason", None) if candidate is not None else None

    def _function_calls(self, candidate: Any) -> List[Dict[str, Any]]:
        if candidate is None:
            return []
        content = getattr(candidate, "content", None)
        parts = getattr(content, "parts", None) or []
        out = []
        for part in parts:
            fc = getattr(part, "function_call", None)
            if fc is None and isinstance(part, dict):
                fc = part.get("function_call")
            if fc is None:
                continue
            name = getattr(fc, "name", None) or fc.get("name") if isinstance(fc, dict) else getattr(fc, "name", None)
            args = getattr(fc, "args", None) or (fc.get("args") if isinstance(fc, dict) else None) or {}
            out.append({"name": name or "", "args": args})
        return out

    def _parse_text(self, candidate: Any, request: ModelRequest) -> Dict[str, Any]:
        if candidate is None:
            return {}
        content = getattr(candidate, "content", None)
        parts = getattr(content, "parts", None) or []
        text_chunks: List[str] = []
        for part in parts:
            text = getattr(part, "text", None)
            if text is None and isinstance(part, dict):
                text = part.get("text")
            if text:
                text_chunks.append(text)
        text = "".join(text_chunks).strip()
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
            ("prompt_token_count", "input_tokens"),
            ("candidates_token_count", "output_tokens"),
            ("total_token_count", "total_tokens"),
        ):
            value = getattr(usage, src, None)
            if value is None:
                continue
            acc[dst] = int(acc.get(dst, 0)) + int(value)

    def _build_default_client(self) -> Any:
        if self._module is None:
            raise RuntimeError("google-genai is not importable")
        if os.environ.get(self.api_key_env) is None:
            raise RuntimeError(
                f"{self.api_key_env} not set; pass `client_factory` or set the env var"
            )
        Client = getattr(self._module, "Client", None)
        if Client is not None:
            return Client(api_key=os.environ[self.api_key_env])
        # Legacy `google.generativeai` exposes `configure`.
        configure = getattr(self._module, "configure", None)
        if configure is not None:
            configure(api_key=os.environ[self.api_key_env])
            return self._module
        raise RuntimeError("google-genai client construction failed")
