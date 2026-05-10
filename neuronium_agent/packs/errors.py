"""Exceptions for the workflow pack system."""

from __future__ import annotations

from typing import List


class PackError(Exception):
    """Base class for pack errors."""


class PackValidationError(PackError):
    def __init__(self, errors: List[str]):
        super().__init__("; ".join(errors))
        self.errors = errors
