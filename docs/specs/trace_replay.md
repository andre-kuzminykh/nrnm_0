# Trace and Replay

## v0.1 — Trace

- Append-only JSON Lines file at `<trace_dir>/<run_id>.jsonl`.
- Canonical envelope: `{run_id, seq, ts, kind, payload}`.
- `seq` is monotonically increasing within a run.
- Secrets are redacted via `neuronium_agent.trace.redact` before write.

## v0.1 — Replay

Mock mode is deterministic enough that re-running an objective with the same
inputs produces an equivalent event sequence. A formal `replay` command is
planned for v0.2.

## v0.2 — Replay command

- `neuronium-agent runs replay <run_id> [--strict]`
- Reconstructs the run from trace events.
- Strict mode verifies every event matches the original trace.
