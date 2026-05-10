"""Real MCP (Model Context Protocol) client + server lifecycle.

Supports two transports:
- `stdio` — spawn a subprocess and exchange JSON-RPC over stdin/stdout.
- `http` — POST JSON-RPC to a remote endpoint.

Each registered MCP server exposes its tools under namespaced refs
`<server_name>.<tool_name>` and registers them onto Neuronium's `ToolRegistry`.
The same `PolicyEngine` + human gates apply.
"""

from neuronium_agent.mcp.client import (
    JSONRPCError,
    MCPClient,
    MCPHttpClient,
    MCPStdioClient,
    MCPToolDescriptor,
)
from neuronium_agent.mcp.config import MCPServerConfig, MCPTransport
from neuronium_agent.mcp.loader import MCPLoader, MCPLoaderResult

__all__ = [
    "JSONRPCError",
    "MCPClient",
    "MCPHttpClient",
    "MCPLoader",
    "MCPLoaderResult",
    "MCPServerConfig",
    "MCPStdioClient",
    "MCPToolDescriptor",
    "MCPTransport",
]
