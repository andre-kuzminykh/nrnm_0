"""Minimal MCP client implementations: stdio + http.

The protocol shape we implement is the standard MCP JSON-RPC 2.0:
- `initialize` (handshake)
- `tools/list`
- `tools/call`

The clients are deliberately small and dependency-free so CI can exercise them
with a fake transport. A production deployment may swap in the official `mcp`
SDK; the `MCPClient` Protocol is the seam.
"""

from __future__ import annotations

import json
import os
import subprocess
import threading
import time
from typing import Any, Dict, List, Optional, Protocol

from pydantic import BaseModel, ConfigDict, Field


class JSONRPCError(RuntimeError):
    def __init__(self, code: int, message: str, data: Any = None) -> None:
        super().__init__(f"JSON-RPC error {code}: {message}")
        self.code = code
        self.message = message
        self.data = data


class MCPToolDescriptor(BaseModel):
    model_config = ConfigDict(extra="forbid")
    server: str
    name: str
    description: str = ""
    input_schema: Dict[str, Any] = Field(default_factory=dict)

    @property
    def ref(self) -> str:
        return f"{self.server}.{self.name}"


class MCPClient(Protocol):
    """Protocol implemented by every MCP transport."""

    name: str

    def initialize(self) -> Dict[str, Any]: ...

    def list_tools(self) -> List[MCPToolDescriptor]: ...

    def call_tool(self, name: str, arguments: Dict[str, Any]) -> Any: ...

    def close(self) -> None: ...


# ---- stdio ----


class MCPStdioClient:
    """JSON-RPC over stdin/stdout against a long-lived subprocess.

    Frames are newline-delimited JSON objects (LSP-style without the
    Content-Length header — most reference servers accept this and the
    official SDKs handle either).
    """

    def __init__(
        self,
        name: str,
        command: str,
        args: Optional[List[str]] = None,
        *,
        env: Optional[Dict[str, str]] = None,
        startup_timeout_s: int = 5,
        request_timeout_s: int = 30,
    ) -> None:
        self.name = name
        self.command = command
        self.args = args or []
        self.env = env or {}
        self.startup_timeout_s = startup_timeout_s
        self.request_timeout_s = request_timeout_s
        self._proc: Optional[subprocess.Popen[str]] = None
        self._next_id = 1
        self._lock = threading.Lock()

    def start(self) -> None:
        merged_env = dict(os.environ)
        merged_env.update(self.env)
        self._proc = subprocess.Popen(
            [self.command, *self.args],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1,
            env=merged_env,
        )

    def initialize(self) -> Dict[str, Any]:
        if self._proc is None:
            self.start()
        return self._request(
            "initialize",
            {
                "protocolVersion": "2024-11-05",
                "clientInfo": {"name": "neuronium-agent", "version": "0.1.0"},
                "capabilities": {},
            },
        )

    def list_tools(self) -> List[MCPToolDescriptor]:
        result = self._request("tools/list", {}) or {}
        items = result.get("tools") or []
        return [
            MCPToolDescriptor(
                server=self.name,
                name=item.get("name", ""),
                description=item.get("description", ""),
                input_schema=item.get("inputSchema") or item.get("input_schema") or {},
            )
            for item in items
            if item.get("name")
        ]

    def call_tool(self, name: str, arguments: Dict[str, Any]) -> Any:
        return self._request("tools/call", {"name": name, "arguments": arguments})

    def close(self) -> None:
        if self._proc is None:
            return
        try:
            self._proc.terminate()
            try:
                self._proc.wait(timeout=2)
            except subprocess.TimeoutExpired:
                self._proc.kill()
        finally:
            self._proc = None

    def _request(self, method: str, params: Dict[str, Any]) -> Any:
        with self._lock:
            if self._proc is None:
                raise RuntimeError("stdio MCP server is not started")
            req_id = self._next_id
            self._next_id += 1
            payload = {
                "jsonrpc": "2.0",
                "id": req_id,
                "method": method,
                "params": params,
            }
            assert self._proc.stdin is not None and self._proc.stdout is not None
            self._proc.stdin.write(json.dumps(payload) + "\n")
            self._proc.stdin.flush()
            deadline = time.monotonic() + self.request_timeout_s
            while True:
                if self._proc.stdout is None:
                    raise RuntimeError("MCP server stdout closed")
                line = self._proc.stdout.readline()
                if not line:
                    if time.monotonic() > deadline:
                        raise TimeoutError(f"MCP request '{method}' timed out")
                    if self._proc.poll() is not None:
                        raise RuntimeError(
                            f"MCP server '{self.name}' exited with {self._proc.returncode}"
                        )
                    continue
                try:
                    data = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if data.get("id") != req_id:
                    continue
                if "error" in data:
                    err = data["error"] or {}
                    raise JSONRPCError(
                        err.get("code", -32603),
                        err.get("message", "unknown"),
                        err.get("data"),
                    )
                return data.get("result")


# ---- http ----


class MCPHttpClient:
    """JSON-RPC over HTTP. Uses `httpx` if available, else `urllib`."""

    def __init__(
        self,
        name: str,
        url: str,
        *,
        headers: Optional[Dict[str, str]] = None,
        timeout_s: int = 30,
    ) -> None:
        self.name = name
        self.url = url
        self.headers = dict(headers or {})
        self.headers.setdefault("Content-Type", "application/json")
        self.timeout_s = timeout_s
        self._next_id = 1
        self._lock = threading.Lock()

    def initialize(self) -> Dict[str, Any]:
        return self._request(
            "initialize",
            {
                "protocolVersion": "2024-11-05",
                "clientInfo": {"name": "neuronium-agent", "version": "0.1.0"},
                "capabilities": {},
            },
        )

    def list_tools(self) -> List[MCPToolDescriptor]:
        result = self._request("tools/list", {}) or {}
        items = result.get("tools") or []
        return [
            MCPToolDescriptor(
                server=self.name,
                name=item.get("name", ""),
                description=item.get("description", ""),
                input_schema=item.get("inputSchema") or item.get("input_schema") or {},
            )
            for item in items
            if item.get("name")
        ]

    def call_tool(self, name: str, arguments: Dict[str, Any]) -> Any:
        return self._request("tools/call", {"name": name, "arguments": arguments})

    def close(self) -> None:
        return None

    def _request(self, method: str, params: Dict[str, Any]) -> Any:
        with self._lock:
            req_id = self._next_id
            self._next_id += 1
            payload = {
                "jsonrpc": "2.0",
                "id": req_id,
                "method": method,
                "params": params,
            }
            data = self._post_json(payload)
            if "error" in data:
                err = data["error"] or {}
                raise JSONRPCError(
                    err.get("code", -32603),
                    err.get("message", "unknown"),
                    err.get("data"),
                )
            return data.get("result")

    def _post_json(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        try:
            import httpx

            with httpx.Client(timeout=self.timeout_s) as cli:
                resp = cli.post(self.url, headers=self.headers, json=payload)
                resp.raise_for_status()
                return resp.json()
        except Exception:
            # Fallback to stdlib urllib (no httpx in CI).
            import urllib.request

            body = json.dumps(payload).encode("utf-8")
            req = urllib.request.Request(self.url, data=body, headers=self.headers)
            with urllib.request.urlopen(req, timeout=self.timeout_s) as fh:
                raw = fh.read().decode("utf-8")
                return json.loads(raw)
