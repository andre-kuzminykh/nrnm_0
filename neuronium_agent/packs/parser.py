"""Parse Workflow Pack YAML into pydantic models."""

from __future__ import annotations

import os
from typing import Any, Dict

import yaml
from pydantic import ValidationError

from neuronium_agent.packs.errors import PackError, PackValidationError
from neuronium_agent.packs.models import WorkflowPack


def parse_pack(data: Dict[str, Any]) -> WorkflowPack:
    try:
        return WorkflowPack.model_validate(data)
    except ValidationError as exc:
        errors = [
            f"{'/'.join(str(p) for p in err['loc'])}: {err['msg']}"
            for err in exc.errors()
        ]
        raise PackValidationError(errors) from exc


def parse_pack_file(path: str) -> WorkflowPack:
    if not os.path.isfile(path):
        raise PackError(f"pack file not found: {path}")
    with open(path, "r", encoding="utf-8") as fh:
        data = yaml.safe_load(fh)
    if not isinstance(data, dict):
        raise PackError(f"pack file is empty or not a mapping: {path}")
    return parse_pack(data)
