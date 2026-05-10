"""Run discovery + replay for past traces under `<trace_dir>/*.jsonl`."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field


class RunSummary(BaseModel):
    model_config = ConfigDict(extra="forbid")
    run_id: str
    trace_path: str
    pack_id: Optional[str] = None
    objective: Optional[str] = None
    status: Optional[str] = None
    started_at: Optional[float] = None
    event_count: int = 0


def list_runs(trace_dir: str) -> List[RunSummary]:
    """Read every `*.jsonl` file under `trace_dir` and produce summaries."""
    out: List[RunSummary] = []
    root = Path(trace_dir)
    if not root.is_dir():
        return out
    for path in sorted(root.glob("*.jsonl")):
        try:
            summary = _summarize(path)
        except Exception:  # noqa: BLE001
            continue
        out.append(summary)
    return out


def show_run(trace_path: str) -> Dict[str, Any]:
    """Return the full event stream + computed summary for a run."""
    events = _load_events(trace_path)
    return {"summary": _summary_from_events(trace_path, events).model_dump(), "events": events}


def _summarize(path: Path) -> RunSummary:
    events = _load_events(str(path))
    return _summary_from_events(str(path), events)


def _load_events(trace_path: str) -> List[Dict[str, Any]]:
    events: List[Dict[str, Any]] = []
    with open(trace_path, "r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                events.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return events


def _summary_from_events(
    trace_path: str, events: List[Dict[str, Any]]
) -> RunSummary:
    run_id = ""
    pack_id: Optional[str] = None
    objective: Optional[str] = None
    status: Optional[str] = None
    started_at: Optional[float] = None
    for e in events:
        run_id = run_id or e.get("run_id", "")
        if started_at is None:
            started_at = e.get("ts")
        kind = e.get("kind")
        payload = e.get("payload") or {}
        if kind == "run.started":
            objective = payload.get("objective", objective)
            pack_id = payload.get("pack_id", pack_id)
        if kind == "run.completed":
            status = "succeeded"
        if kind == "run.failed":
            status = "failed"
    return RunSummary(
        run_id=run_id or os.path.basename(trace_path),
        trace_path=trace_path,
        pack_id=pack_id,
        objective=objective,
        status=status,
        started_at=started_at,
        event_count=len(events),
    )
