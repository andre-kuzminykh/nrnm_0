# Data Model (ER)

```
Run ─────────── Trace ─────────── Event*
 │                                    ▲
 │                                    │
 ├── attachments                      │
 │                                    │
 ├── AgentInstance* ── AgentDefinition │
 │                                    │
 ├── Workflow Program ── Node*        │
 │                  └── Edge*         │
 │                                    │
 └── ArtifactGraph ── Artifact*
```

Key cardinalities:

- A `Run` has many `Event`s (ordered by `seq`).
- A `Run` has many `AgentInstance`s.
- A `Run` references one Workflow `Program`.
- A `Program` has many `Node`s and `Edge`s.
- An `AgentInstance` references one `AgentDefinition`.
- A `Pack` declares many `AgentDefinition`s, `PackTool`s, `Workflow`s, `QualityGate`s, `OutputTemplate`s, `Test`s.
