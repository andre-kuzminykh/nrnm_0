"""Compose effective prompts for an AgentInstance."""

from __future__ import annotations

import os
from typing import Any, Dict

from neuronium_agent.agents.models import AgentInstance


_PROMPT_CACHE: Dict[str, str] = {}


def _read_prompt_text(prompt_ref: str) -> str:
    if prompt_ref in _PROMPT_CACHE:
        return _PROMPT_CACHE[prompt_ref]
    candidates = [prompt_ref]
    if not os.path.isabs(prompt_ref):
        repo_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
        candidates.append(os.path.join(repo_root, prompt_ref))
    text = ""
    for path in candidates:
        if os.path.isfile(path):
            with open(path, "r", encoding="utf-8") as fh:
                text = fh.read()
                break
    _PROMPT_CACHE[prompt_ref] = text
    return text


def compose_prompt(instance: AgentInstance, state: Dict[str, Any]) -> str:
    """Combine system header + role intro + prompt-file body + state hints."""
    definition = instance.definition
    header = (
        f"# Agent: {definition.id} (role: {definition.role.value})\n"
        f"## Goal\n{definition.goal or '—'}\n"
    )
    body = ""
    if definition.prompt_ref:
        body = _read_prompt_text(definition.prompt_ref)
    constraints = ""
    if definition.acceptance_criteria:
        bullets = "\n".join(f"- {c}" for c in definition.acceptance_criteria)
        constraints = f"## Acceptance criteria\n{bullets}\n"
    contract = ""
    if definition.output_contract:
        required = ", ".join(definition.output_contract.required) or "—"
        contract = f"## Output contract\nRequired: {required}\n"
    state_block = "## State keys\n" + ", ".join(sorted(state.keys()))
    return "\n".join(s for s in [header, body, constraints, contract, state_block] if s)
