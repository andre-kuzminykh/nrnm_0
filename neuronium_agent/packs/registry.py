"""Workflow Pack registry: built-in + user-installed."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Dict, List, Optional

from neuronium_agent.packs.errors import PackError
from neuronium_agent.packs.compiler import CompiledPack, compile_pack
from neuronium_agent.packs.models import WorkflowPack
from neuronium_agent.packs.parser import parse_pack_file


_BUILTIN_DIR = Path(__file__).parent / "builtin"


class PackRegistry:
    def __init__(self, extra_paths: Optional[List[str]] = None) -> None:
        self._packs: Dict[str, WorkflowPack] = {}
        self._compiled: Dict[str, CompiledPack] = {}
        self._sources: Dict[str, str] = {}
        self.extra_paths: List[str] = list(extra_paths or [])
        self._discover()

    def _discover(self) -> None:
        search_dirs: List[Path] = [_BUILTIN_DIR]
        for p in self.extra_paths:
            path = Path(p)
            if path.exists():
                search_dirs.append(path)
        cwd = Path.cwd() / ".neuronium" / "packs"
        if cwd.exists():
            search_dirs.append(cwd)
        for d in search_dirs:
            if not d.is_dir():
                continue
            for yaml_file in d.glob("*.yaml"):
                try:
                    pack = parse_pack_file(str(yaml_file))
                except PackError:
                    continue
                self._packs[pack.id] = pack
                self._sources[pack.id] = str(yaml_file)

    def reload(self) -> None:
        self._packs.clear()
        self._compiled.clear()
        self._sources.clear()
        self._discover()

    def list(self) -> List[WorkflowPack]:
        return list(self._packs.values())

    def list_ids(self) -> List[str]:
        return sorted(self._packs.keys())

    def has(self, pack_id: str) -> bool:
        return pack_id in self._packs

    def get(self, pack_id: str) -> WorkflowPack:
        if pack_id not in self._packs:
            raise PackError(f"pack '{pack_id}' not installed")
        return self._packs[pack_id]

    def source_path(self, pack_id: str) -> Optional[str]:
        return self._sources.get(pack_id)

    def get_compiled(self, pack_id: str) -> CompiledPack:
        if pack_id not in self._compiled:
            self._compiled[pack_id] = compile_pack(self.get(pack_id))
        return self._compiled[pack_id]

    def install_from_file(self, path: str) -> WorkflowPack:
        pack = parse_pack_file(path)
        self._packs[pack.id] = pack
        self._compiled.pop(pack.id, None)
        self._sources[pack.id] = path
        return pack

    def remove(self, pack_id: str) -> None:
        if pack_id not in self._packs:
            raise PackError(f"pack '{pack_id}' not installed")
        self._packs.pop(pack_id, None)
        self._compiled.pop(pack_id, None)
        self._sources.pop(pack_id, None)

    def suggest_for_objective(self, objective: str) -> Optional[WorkflowPack]:
        """Return the pack whose objective phrases best match the text."""
        best: Optional[WorkflowPack] = None
        best_score = 0
        text = objective.lower()
        for pack in self._packs.values():
            for obj in pack.objectives:
                for phrase in obj.user_phrases:
                    if phrase.lower() in text:
                        score = len(phrase)
                        if score > best_score:
                            best_score = score
                            best = pack
        return best
