"""Public Python facade for Neuronium."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from neuronium_agent.memory.backend import MemoryBackend, MemoryConfig
from neuronium_agent.packs.compiler import CompiledPack
from neuronium_agent.packs.registry import PackRegistry
from neuronium_agent.runtime.objective_runner import ObjectiveRunner, RunResult


def list_packs() -> List[Dict[str, str]]:
    """Return a list of installed packs (id, name, version, domain)."""
    registry = PackRegistry()
    out: List[Dict[str, str]] = []
    for pack in registry.list():
        out.append(
            {
                "id": pack.pack.id,
                "name": pack.pack.name,
                "version": pack.pack.version,
                "domain": pack.pack.domain,
            }
        )
    return out


def load_pack(pack_id: str) -> CompiledPack:
    """Return a compiled pack by id."""
    registry = PackRegistry()
    return registry.get_compiled(pack_id)


def run_objective(
    objective: str,
    pack: Optional[str] = None,
    *,
    mock: bool = True,
    auto_approve: Optional[bool] = None,
    inputs: Optional[Dict[str, Any]] = None,
    trace_dir: Optional[str] = None,
    force_failure_first: bool = False,
    memory: Optional[MemoryBackend] = None,
    memory_config: Optional[MemoryConfig] = None,
) -> RunResult:
    """Run an objective with the chosen pack.

    `mock=True` is the default in v0.1: it uses the deterministic mock model
    provider and mock MCP tools. Memory defaults to the mock GraphRAG backend
    but can be switched to `raganything` (or any registered backend) by passing
    a `MemoryConfig` or a pre-built `memory` instance.
    """
    if auto_approve is None:
        auto_approve = mock
    runner = ObjectiveRunner(
        trace_dir=trace_dir,
        auto_approve=auto_approve,
        force_failure_first=force_failure_first,
        memory=memory,
        memory_config=memory_config,
    )
    return runner.run(objective, pack_id=pack, inputs=inputs)
