"""Workflow Pack generator: markdown template → YAML."""

from __future__ import annotations

import os
from pathlib import Path

import yaml

from neuronium_agent.packs.generator import (
    generate_from_template_file,
    generate_pack_from_template,
)
from neuronium_agent.packs.parser import parse_pack
from neuronium_agent.packs.validator import validate_pack


TEMPLATE = """\
# Workflow Pack: HR Recruiting

## 1. Domain
HR.

## 2. What should the user be able to ask?
- screen candidates for a senior backend role
- create interview plan for a Series A startup

## 3. What outcomes should the system produce?
- candidate shortlist
- interview plan

## 4. What agents are needed?
```text
Name: Screener
Role: executor
Does: rank candidates
Tools: ats_search, doc_write
Output: shortlist
```

```text
Name: Critic
Role: critic
Does: verify compliance
Tools:
Output: verdict
```

## 5. What tools are needed?
- ATS search
- doc write
- calendar create

## 6. What actions are risky?
- changing candidate status
- sending email

## 7. When should a human approve?
- before publishing
- before rejecting a candidate

## 8. What memory / context is needed?
- candidate profiles
- prior interviews

## 9. What quality checks are needed?
- compliance passes

## 10. What should the final output look like?
- markdown report
- shortlist table
"""


def test_template_generates_valid_pack(tmp_path: Path) -> None:
    pack = generate_pack_from_template(TEMPLATE, pack_id="hr_custom")
    assert pack["pack"]["id"] == "hr_custom"
    parsed = parse_pack(pack)
    validate_pack(parsed)
    assert any(a["role"] == "critic" for a in pack["agents"])


def test_template_generation_writes_yaml(tmp_path: Path) -> None:
    template_path = tmp_path / "template.md"
    template_path.write_text(TEMPLATE)
    out = tmp_path / "pack.yaml"
    pack = generate_from_template_file(str(template_path), str(out), pack_id="hr_custom")
    assert out.exists()
    loaded = yaml.safe_load(out.read_text())
    assert loaded["pack"]["id"] == "hr_custom"
    parsed = parse_pack(loaded)
    validate_pack(parsed)
