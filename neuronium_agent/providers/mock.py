"""Deterministic mock model provider used in CI and `--mock` runs."""

from __future__ import annotations

import re
from typing import Any, Dict, Optional

from neuronium_agent.providers.base import ModelProvider, ModelRequest, ModelResponse


class MockModelProvider:
    """Returns deterministic outputs based on agent_id and expected_keys."""

    name = "mock"

    def __init__(self, force_failure_first: bool = False) -> None:
        # When True, the first run of the coding workflow will report a
        # failing test to exercise the replan loop. Subsequent runs pass.
        self._first_test_done = False
        self._force_failure_first = force_failure_first

    def supports(self, role: str) -> bool:
        return True

    def _coding_planner(self, request: ModelRequest) -> Dict[str, Any]:
        return {
            "plan": [
                "Identify the failing test by reading the report",
                "Trace the failure to source files",
                "Apply minimal patch",
                "Re-run tests",
            ],
            "files_to_inspect": ["src/calculator.py", "tests/test_calculator.py"],
            "risks": ["regression in unrelated callers"],
        }

    def _code_researcher(self, request: ModelRequest) -> Dict[str, Any]:
        return {
            "root_cause": (
                "Division by zero is unchecked in calculator.divide; an early "
                "return is missing."
            ),
            "snippets": [
                {
                    "path": "src/calculator.py",
                    "lines": "def divide(a, b):\n    return a / b",
                }
            ],
        }

    def _code_editor(self, request: ModelRequest) -> Dict[str, Any]:
        return {
            "patch_summary": "Guard divisor against zero in calculator.divide.",
            "changed_files": ["src/calculator.py"],
            "proposed_patch": (
                "--- a/src/calculator.py\n+++ b/src/calculator.py\n"
                "@@\n-def divide(a, b):\n-    return a / b\n+def divide(a, b):\n"
                "+    if b == 0:\n+        raise ValueError('divisor must be non-zero')\n"
                "+    return a / b\n"
            ),
        }

    def _test_runner(self, request: ModelRequest) -> Dict[str, Any]:
        if self._force_failure_first and not self._first_test_done:
            self._first_test_done = True
            return {
                "test_result": {
                    "status": "failed",
                    "summary": "1 failing test (mock)",
                }
            }
        return {
            "test_result": {"status": "passed", "summary": "all tests passing (mock)"}
        }

    def _code_reviewer(self, request: ModelRequest) -> Dict[str, Any]:
        test_result = request.state.get("test_result") or {}
        if isinstance(test_result, dict) and test_result.get("status") == "passed":
            return {"verdict": "PASS", "reasons": ["tests pass", "patch is minimal"]}
        return {"verdict": "FAIL", "reasons": ["tests failing — please replan"]}

    def _audience_researcher(self, request: ModelRequest) -> Dict[str, Any]:
        return {
            "segments": ["startups", "indie devs", "enterprise ML teams"],
            "personas": [
                {"name": "Indie dev", "pain": "wants quick coding agent"},
                {"name": "ML engineer", "pain": "wants workflow control"},
            ],
        }

    def _campaign_planner(self, request: ModelRequest) -> Dict[str, Any]:
        return {
            "campaign_plan": "4-week launch covering blog, email, and product hunt.",
            "milestones": ["W1 teaser", "W2 launch", "W3 deep dives", "W4 wrap-up"],
        }

    def _copywriter(self, request: ModelRequest) -> Dict[str, Any]:
        return {
            "copy_drafts": [
                {"channel": "blog", "draft": "Why Neuronium is a Super Agent..."},
                {"channel": "email", "draft": "Meet Neuronium..."},
            ]
        }

    def _performance_critic(self, request: ModelRequest) -> Dict[str, Any]:
        return {"verdict": "PASS", "reasons": ["copy on-brand", "milestones sound"]}

    def _recruiter(self, request: ModelRequest) -> Dict[str, Any]:
        return {"shortlist_plan": "Source from ATS, filter by skill match >= 0.7"}

    def _candidate_screener(self, request: ModelRequest) -> Dict[str, Any]:
        return {
            "shortlist": [
                {"id": "C-001", "name": "A. Doe", "score": 0.92},
                {"id": "C-002", "name": "B. Roe", "score": 0.87},
            ],
            "rationale": ["A. Doe matched 3/3 must-have skills"],
        }

    def _interview_planner(self, request: ModelRequest) -> Dict[str, Any]:
        return {
            "interview_plan": "Phone screen → tech interview → system design → bar raiser",
            "questions": [
                "Walk me through a hard outage you debugged.",
                "How do you reason about CAP tradeoffs?",
            ],
        }

    def _compliance_critic(self, request: ModelRequest) -> Dict[str, Any]:
        return {"verdict": "PASS", "reasons": ["screening is policy-compliant"]}

    _HANDLERS = {
        "code_planner": "_coding_planner",
        "code_researcher": "_code_researcher",
        "code_editor": "_code_editor",
        "test_runner": "_test_runner",
        "code_reviewer": "_code_reviewer",
        "audience_researcher": "_audience_researcher",
        "campaign_planner": "_campaign_planner",
        "copywriter": "_copywriter",
        "performance_critic": "_performance_critic",
        "recruiter": "_recruiter",
        "candidate_screener": "_candidate_screener",
        "interview_planner": "_interview_planner",
        "compliance_critic": "_compliance_critic",
    }

    def generate(self, request: ModelRequest) -> ModelResponse:
        handler_name = self._HANDLERS.get(request.agent_id)
        if handler_name is not None:
            output = getattr(self, handler_name)(request)
        else:
            output = self._fallback(request)
        # Restrict to expected_keys when the agent declared them.
        if request.expected_keys:
            filtered = {k: output[k] for k in request.expected_keys if k in output}
            # Preserve any keys we returned for downstream gates.
            for k, v in output.items():
                filtered.setdefault(k, v)
            output = filtered
        return ModelResponse(role=request.role, agent_id=request.agent_id, output=output)

    def _fallback(self, request: ModelRequest) -> Dict[str, Any]:
        if request.expected_keys:
            return {k: f"mock:{request.agent_id}:{k}" for k in request.expected_keys}
        return {"result": f"mock:{request.agent_id}"}
