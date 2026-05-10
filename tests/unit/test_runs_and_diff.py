"""Tests for runs.py + diff_preview.py."""

from __future__ import annotations

import json
from pathlib import Path

from neuronium_agent.runtime.diff_preview import (
    render_edit_diff,
    render_patch_diff,
    render_write_preview,
)
from neuronium_agent.runtime.runs import list_runs, show_run


def test_render_edit_diff_for_existing_file(tmp_path: Path) -> None:
    src = tmp_path / "x.py"
    src.write_text("def f():\n    return 1\n")
    diff = render_edit_diff(str(src), "return 1", "return 2")
    assert "-    return 1" in diff
    assert "+    return 2" in diff


def test_render_edit_diff_for_missing_old_falls_back_to_full(tmp_path: Path) -> None:
    src = tmp_path / "x.py"
    src.write_text("hello\n")
    diff = render_edit_diff(str(src), "missing", "world")
    assert diff == "(no changes)"


def test_render_patch_diff_truncates_huge() -> None:
    blob = "x" * (32 * 1024)
    out = render_patch_diff(blob)
    assert "(truncated)" in out


def test_render_write_preview_marks_create_vs_overwrite(tmp_path: Path) -> None:
    p = tmp_path / "new.txt"
    out = render_write_preview(str(p), "hi")
    assert "create:" in out
    p.write_text("old")
    out = render_write_preview(str(p), "hi")
    assert "overwrite:" in out


def test_list_runs_summarizes_and_show_returns_events(tmp_path: Path) -> None:
    trace = tmp_path / "run-1.jsonl"
    events = [
        {
            "run_id": "run-1",
            "seq": 1,
            "ts": 100.0,
            "kind": "run.started",
            "payload": {"objective": "fix tests", "pack_id": "coding"},
        },
        {
            "run_id": "run-1",
            "seq": 2,
            "ts": 100.5,
            "kind": "run.completed",
            "payload": {},
        },
    ]
    trace.write_text("\n".join(json.dumps(e) for e in events) + "\n")
    summaries = list_runs(str(tmp_path))
    assert len(summaries) == 1
    s = summaries[0]
    assert s.run_id == "run-1"
    assert s.pack_id == "coding"
    assert s.status == "succeeded"
    assert s.objective == "fix tests"
    assert s.event_count == 2
    data = show_run(str(trace))
    assert len(data["events"]) == 2
    assert data["summary"]["pack_id"] == "coding"
