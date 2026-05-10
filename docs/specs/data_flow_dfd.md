# Data Flow Diagram

```
CLI / API
   │
   ▼
ObjectiveRunner ───► PackRegistry ───► CompiledPack
   │                                   │
   ├──► AgentFactory ──► AgentInstance[]
   │
   ├──► MockGraphRAG ──► RetrievalResult
   │
   ├──► IR Builder ────► Program ──► CompiledGraph
   │
   ├──► Runtime
   │      ├─ ModelRegistry ──► MockModelProvider
   │      ├─ ToolRegistry ───► MockMCP
   │      ├─ PolicyEngine
   │      ├─ HumanGateController
   │      ├─ ArtifactGraph
   │      └─ EventBus ──► TraceRecorder ──► trace.jsonl
   │
   └──► RunResult ──► CLI output / API response
```
