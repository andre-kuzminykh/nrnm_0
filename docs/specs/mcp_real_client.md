# Real MCP Client

Beyond the mock, Neuronium ships a minimal real MCP (Model Context Protocol)
client that speaks JSON-RPC 2.0 over either stdio or HTTP. Tools discovered
from connected servers are registered onto `ToolRegistry` under
`<server_name>.<tool_name>` refs and obey the same `PolicyEngine` + human gate
governance.

## Configuration

```yaml
# .neuronium/mcp.yaml
mcp_servers:
  bash:
    transport: stdio
    command: npx
    args: [-y, "@modelcontextprotocol/server-bash"]
    risk_default: critical
    required: false

  filesystem:
    transport: stdio
    command: npx
    args: [-y, "@modelcontextprotocol/server-filesystem", "~/Desktop/hmnd"]
    risk_default: medium

  smithery_remote:
    transport: http
    url: https://server.smithery.ai/<server>
    api_key_env: SMITHERY_API_KEY
    risk_default: medium
```

Validation is via `MCPServerConfig`. Required servers cause startup to fail;
optional ones are reported in `MCPLoaderResult.failed`.

## API

```python
from neuronium_agent.mcp.config import MCPServerConfig, MCPTransport
from neuronium_agent.mcp.loader import MCPLoader
from neuronium_agent.tools.registry import ToolRegistry

registry = ToolRegistry()
loader = MCPLoader(
    [MCPServerConfig(name="bash", transport=MCPTransport.STDIO, command="bash-mcp")]
)
result = loader.connect_and_register(registry)
print(result.connected, result.failed)
out = registry.call("bash.run", command="ls -la")
loader.close_all(result)
```

## CLI

```bash
neuronium-agent mcp list
neuronium-agent mcp test bash
```

## Tests

`tests/unit/test_mcp.py` covers:
- loader registers tools under `<server>.<tool>` refs with correct schemas
- partial-success: one optional server fails, others still register
- required-server failure raises
- `close_all` releases child processes / sessions
- JSON-RPC errors translate into `{status: "error", code: ...}` tool results
