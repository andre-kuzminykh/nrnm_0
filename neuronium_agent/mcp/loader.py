"""Connect MCP servers and register their tools onto Neuronium's ToolRegistry."""

from __future__ import annotations

import os
from typing import Any, Dict, List, Optional, Union

from pydantic import BaseModel, ConfigDict, Field

from neuronium_agent.mcp.client import (
    JSONRPCError,
    MCPClient,
    MCPHttpClient,
    MCPStdioClient,
    MCPToolDescriptor,
)
from neuronium_agent.mcp.config import MCPServerConfig, MCPTransport
from neuronium_agent.tools.registry import ToolRegistry


class MCPLoaderResult(BaseModel):
    model_config = ConfigDict(extra="forbid", arbitrary_types_allowed=True)
    connected: List[str] = Field(default_factory=list)
    failed: Dict[str, str] = Field(default_factory=dict)
    tools: List[MCPToolDescriptor] = Field(default_factory=list)
    clients: List[Any] = Field(default_factory=list)


def _build_client(cfg: MCPServerConfig) -> MCPClient:
    env = dict(cfg.env or {})
    if cfg.api_key_env and cfg.api_key_env in os.environ:
        env.setdefault(cfg.api_key_env, os.environ[cfg.api_key_env])
    if cfg.transport == MCPTransport.STDIO:
        if not cfg.command:
            raise ValueError(f"stdio MCP '{cfg.name}' missing `command`")
        return MCPStdioClient(
            name=cfg.name,
            command=cfg.command,
            args=cfg.args,
            env=env,
        )
    if cfg.transport == MCPTransport.HTTP:
        if not cfg.url:
            raise ValueError(f"http MCP '{cfg.name}' missing `url`")
        headers = dict(cfg.headers or {})
        if cfg.api_key_env and cfg.api_key_env in os.environ:
            headers.setdefault("Authorization", f"Bearer {os.environ[cfg.api_key_env]}")
        return MCPHttpClient(
            name=cfg.name, url=cfg.url, headers=headers
        )
    raise ValueError(f"unsupported transport: {cfg.transport}")


class MCPLoader:
    """Connects to a set of MCP servers and registers their tools.

    Partial-success: optional servers that fail to connect are reported in
    `failed`; required servers raise. Caller is responsible for closing clients
    via `close_all`.
    """

    def __init__(
        self,
        servers: List[MCPServerConfig],
        *,
        client_factory: Optional[Any] = None,
    ) -> None:
        self.servers = list(servers)
        self.client_factory = client_factory

    def connect_and_register(
        self, registry: ToolRegistry
    ) -> MCPLoaderResult:
        connected: List[str] = []
        failed: Dict[str, str] = {}
        tools: List[MCPToolDescriptor] = []
        clients: List[MCPClient] = []
        for cfg in self.servers:
            try:
                client = (
                    self.client_factory(cfg) if self.client_factory else _build_client(cfg)
                )
                client.initialize()
                server_tools = client.list_tools()
            except Exception as exc:  # noqa: BLE001
                if cfg.required:
                    raise
                failed[cfg.name] = str(exc)
                continue
            connected.append(cfg.name)
            tools.extend(server_tools)
            clients.append(client)
            for tool in server_tools:
                self._register_tool(registry, client, tool, cfg.risk_default)
        return MCPLoaderResult(
            connected=connected, failed=failed, tools=tools, clients=clients
        )

    def _register_tool(
        self,
        registry: ToolRegistry,
        client: MCPClient,
        tool: MCPToolDescriptor,
        risk_default: str,
    ) -> None:
        def _runner(**kwargs: Any) -> Any:
            try:
                return client.call_tool(tool.name, kwargs)
            except JSONRPCError as exc:
                return {"status": "error", "reason": exc.message, "code": exc.code}

        registry.register(
            tool.ref,
            _runner,
            kind="mcp",
            risk=risk_default,
            description=tool.description,
            input_schema=tool.input_schema,
        )

    def close_all(self, result: MCPLoaderResult) -> None:
        for client in result.clients:
            try:
                client.close()
            except Exception:  # noqa: BLE001
                pass
