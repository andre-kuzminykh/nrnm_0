"""Neuronium Super Agent Platform."""

__version__ = "0.1.0"

from neuronium_agent.api import (
    list_packs,
    load_pack,
    run_objective,
)

__all__ = ["__version__", "list_packs", "load_pack", "run_objective"]
