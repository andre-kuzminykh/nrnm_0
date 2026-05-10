"""Canonical event bus for a run.

Wraps a TraceRecorder so that any subsystem can `emit` a typed event.
"""

from __future__ import annotations

from typing import Any, Callable, Dict, List, Optional

from neuronium_agent.trace.recorder import TraceRecorder


EventHandler = Callable[[Dict[str, Any]], None]


class EventBus:
    def __init__(self, recorder: TraceRecorder) -> None:
        self.recorder = recorder
        self._subscribers: List[EventHandler] = []

    def emit(self, kind: str, payload: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        event = self.recorder.emit(kind, payload or {})
        for sub in self._subscribers:
            try:
                sub(event)
            except Exception:  # noqa: BLE001
                pass
        return event

    def subscribe(self, handler: EventHandler) -> None:
        self._subscribers.append(handler)

    @property
    def events(self) -> List[Dict[str, Any]]:
        return self.recorder.events
