"""Append-only JSON Lines trace recorder."""

from __future__ import annotations

import json
import os
import time
from typing import Any, Dict, List, Optional

from neuronium_agent.trace.redact import redact_payload


class TraceRecorder:
    """Records canonical run events with monotonic `seq`."""

    def __init__(self, run_id: str, path: Optional[str] = None) -> None:
        self.run_id = run_id
        self.path = path
        self.seq = 0
        self.events: List[Dict[str, Any]] = []
        if path:
            parent = os.path.dirname(os.path.abspath(path))
            if parent:
                os.makedirs(parent, exist_ok=True)
            # Truncate any prior content for this run path.
            with open(path, "w", encoding="utf-8"):
                pass

    def emit(self, kind: str, payload: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        self.seq += 1
        event = {
            "run_id": self.run_id,
            "seq": self.seq,
            "ts": time.time(),
            "kind": kind,
            "payload": redact_payload(dict(payload or {})),
        }
        self.events.append(event)
        if self.path:
            with open(self.path, "a", encoding="utf-8") as fh:
                fh.write(json.dumps(event, default=str))
                fh.write("\n")
        return event

    def export(self) -> List[Dict[str, Any]]:
        return list(self.events)

    def by_kind(self, kind: str) -> List[Dict[str, Any]]:
        return [e for e in self.events if e["kind"] == kind]
