"""Shared pytest fixtures."""

from __future__ import annotations

import sys
from pathlib import Path

# Make the repo importable without `pip install`.
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


import pytest

from neuronium_agent.packs.registry import PackRegistry


@pytest.fixture()
def pack_registry() -> PackRegistry:
    return PackRegistry()
