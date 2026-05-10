"""MCP client + loader tests using injected fake transports."""

from __future__ import annotations

from typing import Any, Dict, List

import pytest

from neuronium_agent.mcp.client import (
    JSONRPCError,
    MCPToolDescriptor,
)
from neuronium_agent.mcp.config import MCPServerConfig, MCPTransport
from neuronium_agent.mcp.loader import MCPLoader
from neuronium_agent.tools.registry import ToolRegistry


class _FakeMCPClient:
    """Drop-in replacement implementing the MCPClient Protocol."""

    def __init__(
        self,
        name: str,
        tools: List[Dict[str, Any]],
        responses: Dict[str, Any] | None = None,
        fail_initialize: bool = False,
    ) -> None:
        self.name = name
        self._tools = tools
        self._responses = responses or {}
        self.fail_initialize = fail_initialize
        self.calls: List[Dict[str, Any]] = []
        self.closed = False

    def initialize(self) -> Dict[str, Any]:
        if self.fail_initialize:
            raise RuntimeError("initialize failed")
        return {"protocolVersion": "2024-11-05"}

    def list_tools(self) -> List[MCPToolDescriptor]:
        return [
            MCPToolDescriptor(
                server=self.name,
                name=t["name"],
                description=t.get("description", ""),
                input_schema=t.get("inputSchema", {}),
            )
            for t in self._tools
        ]

    def call_tool(self, name: str, arguments: Dict[str, Any]) -> Any:
        self.calls.append({"name": name, "arguments": arguments})
        if name in self._responses:
            value = self._responses[name]
            if isinstance(value, Exception):
                raise value
            return value
        return {"ok": True}

    def close(self) -> None:
        self.closed = True


def test_loader_registers_tools_with_namespaced_refs() -> None:
    fake_clients = [
        _FakeMCPClient(
            "bash",
            tools=[
                {
                    "name": "run",
                    "description": "Run a bash command",
                    "inputSchema": {
                        "type": "object",
                        "properties": {"command": {"type": "string"}},
                    },
                }
            ],
            responses={"run": {"stdout": "hello", "return_code": 0}},
        ),
        _FakeMCPClient(
            "fs",
            tools=[
                {"name": "read", "description": "Read file"},
                {"name": "write", "description": "Write file"},
            ],
        ),
    ]
    iter_clients = iter(fake_clients)

    def factory(cfg: MCPServerConfig):
        return next(iter_clients)

    registry = ToolRegistry()
    loader = MCPLoader(
        [
            MCPServerConfig(name="bash", transport=MCPTransport.STDIO, command="x"),
            MCPServerConfig(name="fs", transport=MCPTransport.STDIO, command="x"),
        ],
        client_factory=factory,
    )
    result = loader.connect_and_register(registry)
    assert set(result.connected) == {"bash", "fs"}
    assert registry.has("bash.run")
    assert registry.has("fs.read")
    assert registry.has("fs.write")
    desc = registry.descriptor("bash.run")
    assert desc.kind == "mcp"
    assert desc.input_schema["properties"]["command"]["type"] == "string"
    out = registry.call("bash.run", command="echo hi")
    assert out["stdout"] == "hello"


def test_loader_continues_on_optional_failure() -> None:
    iter_clients = iter([
        _FakeMCPClient("flaky", tools=[], fail_initialize=True),
        _FakeMCPClient(
            "ok",
            tools=[{"name": "ping", "description": ""}],
            responses={"ping": "pong"},
        ),
    ])

    def factory(cfg: MCPServerConfig):
        return next(iter_clients)

    registry = ToolRegistry()
    loader = MCPLoader(
        [
            MCPServerConfig(name="flaky", transport=MCPTransport.STDIO, command="x"),
            MCPServerConfig(name="ok", transport=MCPTransport.STDIO, command="x"),
        ],
        client_factory=factory,
    )
    result = loader.connect_and_register(registry)
    assert result.connected == ["ok"]
    assert "flaky" in result.failed
    assert registry.has("ok.ping")
    assert not registry.has("flaky.ping")


def test_loader_required_server_failure_raises() -> None:
    def factory(cfg: MCPServerConfig):
        return _FakeMCPClient("needed", tools=[], fail_initialize=True)

    loader = MCPLoader(
        [
            MCPServerConfig(
                name="needed",
                transport=MCPTransport.STDIO,
                command="x",
                required=True,
            )
        ],
        client_factory=factory,
    )
    with pytest.raises(RuntimeError):
        loader.connect_and_register(ToolRegistry())


def test_loader_close_all() -> None:
    client = _FakeMCPClient("ok", tools=[])

    def factory(cfg: MCPServerConfig):
        return client

    loader = MCPLoader(
        [MCPServerConfig(name="ok", transport=MCPTransport.STDIO, command="x")],
        client_factory=factory,
    )
    result = loader.connect_and_register(ToolRegistry())
    loader.close_all(result)
    assert client.closed is True


def test_jsonrpc_error_translates_to_tool_error() -> None:
    client = _FakeMCPClient(
        "explode",
        tools=[{"name": "boom"}],
        responses={"boom": JSONRPCError(-32601, "method not found")},
    )

    def factory(cfg: MCPServerConfig):
        return client

    registry = ToolRegistry()
    loader = MCPLoader(
        [MCPServerConfig(name="explode", transport=MCPTransport.STDIO, command="x")],
        client_factory=factory,
    )
    loader.connect_and_register(registry)
    out = registry.call("explode.boom")
    assert out["status"] == "error"
    assert out["code"] == -32601
