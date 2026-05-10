"""Generate a draft Workflow Pack YAML from the simple markdown template."""

from __future__ import annotations

import os
import re
from typing import Any, Dict, List

import yaml

from neuronium_agent.packs.errors import PackError


_SECTION_PATTERN = re.compile(r"^##\s+\d+\.\s*(.+)$", re.MULTILINE)


def _split_sections(text: str) -> Dict[str, str]:
    """Split the template by `## <n>. <heading>` markers."""
    indices = [
        (m.group(1).strip().lower(), m.start(), m.end())
        for m in _SECTION_PATTERN.finditer(text)
    ]
    sections: Dict[str, str] = {}
    for i, (title, _, end) in enumerate(indices):
        next_start = indices[i + 1][1] if i + 1 < len(indices) else len(text)
        sections[title] = text[end:next_start].strip()
    return sections


_BULLET_PATTERN = re.compile(r"^[-*]\s+(.+)$", re.MULTILINE)


def _bullets(block: str) -> List[str]:
    return [m.group(1).strip() for m in _BULLET_PATTERN.finditer(block or "")]


def _slugify(text: str) -> str:
    text = text.strip().lower()
    text = re.sub(r"[^a-z0-9]+", "_", text)
    return text.strip("_") or "agent"


def _parse_agent_block(block: str) -> Dict[str, Any]:
    """Parse one ```text``` block describing an agent."""
    fields: Dict[str, str] = {}
    pattern = re.compile(
        r"^(name|role|does|tools|output|constraints|инструменты|роль|"
        r"что делает|что возвращает|ограничения|название)\s*:\s*(.+)$",
        re.IGNORECASE | re.MULTILINE,
    )
    for m in pattern.finditer(block):
        key = m.group(1).strip().lower()
        fields[key] = m.group(2).strip()
    name = fields.get("name") or fields.get("название") or "Agent"
    role_raw = fields.get("role") or fields.get("роль") or "executor"
    tools_raw = fields.get("tools") or fields.get("инструменты") or ""
    output = fields.get("output") or fields.get("что возвращает") or "result"
    does = fields.get("does") or fields.get("что делает") or ""
    tools = [t.strip() for t in re.split(r"[,;]", tools_raw) if t.strip()]
    return {
        "id": _slugify(name),
        "role": _slugify(role_raw),
        "goal": does,
        "tools": tools,
        "output_contract": {"type": "object", "required": [_slugify(output)]},
    }


def _extract_agents(block: str) -> List[Dict[str, Any]]:
    agents: List[Dict[str, Any]] = []
    for code in re.findall(r"```(?:text)?\n(.*?)```", block, flags=re.DOTALL):
        if re.search(r"(name|role|название|роль)\s*:", code, re.IGNORECASE):
            agents.append(_parse_agent_block(code))
    return agents


def _extract_pack_name(text: str) -> str:
    m = re.search(r"^#\s+Workflow Pack:\s*(.+)$", text, re.MULTILINE)
    return (m.group(1).strip() if m else "Custom Pack")


def generate_pack_from_template(
    template_text: str, pack_id: str = "custom"
) -> Dict[str, Any]:
    """Parse the simple markdown template and emit a pack YAML structure."""
    sections = _split_sections(template_text)

    domain_block = (
        sections.get("домен")
        or sections.get("what domain is this for?")
        or sections.get("domain")
        or ""
    )
    objectives_block = (
        sections.get("что пользователь хочет делать?")
        or sections.get("what should the user be able to ask?")
        or ""
    )
    outcomes_block = (
        sections.get("какие результаты должны получаться?")
        or sections.get("what outcomes should the system produce?")
        or ""
    )
    agents_block = (
        sections.get("какие агенты нужны?")
        or sections.get("what agents are needed?")
        or ""
    )
    tools_block = (
        sections.get("какие инструменты нужны?")
        or sections.get("what tools are needed?")
        or ""
    )
    risky_block = (
        sections.get("какие действия опасные?")
        or sections.get("what actions are risky?")
        or ""
    )
    approvals_block = (
        sections.get("когда нужен человек?")
        or sections.get("when should a human approve?")
        or ""
    )
    output_block = (
        sections.get("как должен выглядеть финальный результат?")
        or sections.get("what should final output look like?")
        or ""
    )

    name = _extract_pack_name(template_text)
    domain = (
        domain_block.split("\n", 1)[0].strip().lstrip("Например:").strip()
        or "general"
    ).lower()
    user_phrases = _bullets(objectives_block) or [
        line.strip() for line in objectives_block.splitlines() if line.strip()
    ]
    outcomes = _bullets(outcomes_block)
    tools_list = _bullets(tools_block)
    risky_actions = _bullets(risky_block)
    approvals = _bullets(approvals_block)
    output_bullets = _bullets(output_block)
    agents = _extract_agents(agents_block)

    if not agents:
        agents = [
            {
                "id": "planner",
                "role": "planner",
                "goal": "plan the work",
                "tools": [],
                "output_contract": {"type": "object", "required": ["plan"]},
            },
            {
                "id": "executor",
                "role": "executor",
                "goal": "execute the plan",
                "tools": [],
                "output_contract": {"type": "object", "required": ["result"]},
            },
            {
                "id": "critic",
                "role": "critic",
                "goal": "check the result",
                "tools": [],
                "output_contract": {"type": "object", "required": ["verdict"]},
            },
        ]

    def _tool_risk(ref: str) -> str:
        l = ref.lower()
        if any(k in l for k in ("delete", "remove", "drop", "rm ", "destroy")):
            return "critical"
        if any(k in l for k in ("write", "edit", "publish", "send", "shell", "deploy")):
            return "high"
        if any(k in l for k in ("create", "update", "modify")):
            return "medium"
        return "low"

    pack_tools = []
    used_refs: set[str] = set()
    for t in tools_list:
        ref = _slugify(t)
        if ref in used_refs:
            continue
        used_refs.add(ref)
        risk = _tool_risk(t)
        entry: Dict[str, Any] = {"ref": ref, "kind": "mcp", "risk": risk}
        if risk in {"high", "critical"}:
            entry["default_permission"] = "require_approval"
        pack_tools.append(entry)
    # Ensure agent-declared tools exist in `tools` section.
    for agent in agents:
        for tref in list(agent["tools"]):
            slug = _slugify(tref)
            agent["tools"] = [_slugify(x) for x in agent["tools"]]
            if slug not in used_refs:
                used_refs.add(slug)
                pack_tools.append(
                    {"ref": slug, "kind": "mcp", "risk": _tool_risk(tref)}
                )

    workflow_phases = []
    for agent in agents:
        workflow_phases.append(
            {
                "id": agent["id"],
                "agent": agent["id"],
                "outputs": list(agent.get("output_contract", {}).get("required", [])),
                "requires_approval": any(
                    keyword in agent["goal"].lower()
                    for keyword in ("publish", "send", "edit", "delete")
                ),
            }
        )

    quality_gates = []
    if any(a["role"] == "critic" for a in agents):
        quality_gates.append(
            {
                "id": "critic_must_pass",
                "condition": "verdict == 'PASS'",
                "on_fail": "replan",
            }
        )

    objective = {
        "id": "primary_objective",
        "user_phrases": user_phrases or ["help with this task"],
        "expected_outcomes": outcomes or ["task completed"],
    }

    pack: Dict[str, Any] = {
        "pack": {
            "id": pack_id,
            "name": name,
            "version": "0.1.0",
            "schema_version": "0.1",
            "compatible_neuronium": ">=0.1.0",
            "domain": domain,
            "description": f"Workflow pack for {name}.",
        },
        "objectives": [objective],
        "agents": agents,
        "tools": pack_tools,
        "workflows": [
            {
                "id": "primary_workflow",
                "objective_match": "primary_objective",
                "phases": workflow_phases,
            }
        ],
        "quality_gates": quality_gates,
        "outputs": [
            {
                "id": "final_summary",
                "type": "markdown",
                "includes": output_bullets or ["result"],
            }
        ],
        "tests": [
            {
                "id": f"{pack_id}_mock_smoke",
                "objective": (user_phrases[0] if user_phrases else "smoke"),
                "expected": [
                    "Workflow reaches final phase",
                    "Final outcome is produced",
                ],
            }
        ],
    }
    if risky_actions:
        pack["pack"]["description"] += " Risky actions: " + ", ".join(risky_actions) + "."
    if approvals:
        pack["pack"]["description"] += " Human approval needed: " + ", ".join(approvals) + "."
    return pack


def write_pack_yaml(pack: Dict[str, Any], out_path: str) -> None:
    parent = os.path.dirname(os.path.abspath(out_path))
    os.makedirs(parent, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as fh:
        yaml.safe_dump(pack, fh, sort_keys=False, allow_unicode=True)


def generate_from_template_file(template_path: str, out_path: str, pack_id: str = "custom") -> Dict[str, Any]:
    if not os.path.isfile(template_path):
        raise PackError(f"template not found: {template_path}")
    with open(template_path, "r", encoding="utf-8") as fh:
        text = fh.read()
    pack = generate_pack_from_template(text, pack_id=pack_id)
    write_pack_yaml(pack, out_path)
    return pack
