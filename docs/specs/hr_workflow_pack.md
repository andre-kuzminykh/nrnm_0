# HR Workflow Pack

Agents: `recruiter`, `candidate_screener`, `interview_planner`, `compliance_critic`.

Objectives:
- `screen_candidates` — produce shortlist with rationale.
- `plan_interview` — produce an interview plan with questions.

Tools (all mocked in v0.1): `ats.search`, `ats.read_candidate`, `calendar.create`, `email.draft`, `doc.write`, `ats.update_status` (critical).

Quality gates: `compliance_passes`.

CLI:

```bash
neuronium-agent objective run "Screen candidates for senior backend role" --pack hr --mock
```
