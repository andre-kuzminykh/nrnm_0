# Services

| Service | Module | Responsibility |
| --- | --- | --- |
| ObjectiveRunner | `neuronium_agent.runtime.objective_runner` | Coordinates the full lifecycle: intake → pack selection → agent factory → IR build/compile → execute → outcome. |
| PackRegistry | `neuronium_agent.packs.registry` | Discovers built-in + user-installed packs; caches compiled artifacts; suggests packs by phrase. |
| AgentFactory | `neuronium_agent.agents.factory` | Per-run instantiation; dynamic synthesis. |
| AgentRegistry | `neuronium_agent.agents.registry` | Persistent agent definitions keyed by pack. |
| PolicyEngine | `neuronium_agent.tools.governance` | Resolves tool permission decisions per (tool, agent). |
| ToolRegistry | `neuronium_agent.tools.registry` | Holds callable tool implementations. |
| MockMCP | `neuronium_agent.tools.mock_mcp` | Mock implementations of MCP-style tools. |
| ModelRegistry | `neuronium_agent.providers.registry` | Maps aliases (fast/smart/cheap/critic) to providers. |
| MockModelProvider | `neuronium_agent.providers.mock` | Deterministic outputs for tests and `--mock` runs. |
| TraceRecorder | `neuronium_agent.trace.recorder` | Append-only JSONL trace with secret redaction. |
| MockGraphRAG | `neuronium_agent.memory.graphrag` | Retrieval over golden fixtures; writeback API. |
| EffectiveConfig | `neuronium_agent.config.hierarchy` | Resolves layered config (built-in → global → project → local → env → CLI → session). |
