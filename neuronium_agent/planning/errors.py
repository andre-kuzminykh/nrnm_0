"""Planning errors."""

from __future__ import annotations

from typing import List


class PlanningError(Exception):
    """Raised when HTN planning fails (unknown task, no applicable method, cycle)."""

    def __init__(self, errors: List[str]):
        super().__init__("; ".join(errors))
        self.errors = errors
