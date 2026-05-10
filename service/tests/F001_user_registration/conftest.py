"""
Фикстуры F001.

## Трассируемость
Feature: F001.
"""
from __future__ import annotations

import pytest


@pytest.fixture
def sample_user_payload() -> dict:
    return {"tg_id": 123, "username": "alice"}
