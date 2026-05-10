# Use Cases

## UC-1 — Fix failing tests with the coding pack

- **Actors:** developer.
- **Preconditions:** repository checked out; Neuronium installed.
- **Main flow:**
  1. Developer runs `neuronium-agent objective run "Fix failing tests" --pack coding --mock`.
  2. Runner selects coding pack, builds 5 agents, retrieves context.
  3. Plan → research → edit (human-gate auto-approved in mock) → test → critic.
  4. Critic PASS → terminal node renders markdown report.
- **Postconditions:** trace file written, report shown.

## UC-2 — Plan a campaign with the marketing pack

- **Actors:** marketer.
- **Main flow:** similar, but with `audience_researcher → campaign_planner → copywriter → performance_critic`.
- **Outputs:** campaign plan, milestones, copy drafts, critic verdict.

## UC-3 — Screen candidates with the HR pack

- **Actors:** recruiter.
- **Main flow:** `recruiter → screener → compliance_critic`.
- **Outputs:** shortlist, rationale, verdict.

## UC-4 — Author and use a custom workflow pack

- **Actors:** power user.
- **Main flow:**
  1. Fill `workflow_pack_template.md`.
  2. `neuronium-agent packs generate ... --out packs/my.yaml --id my`.
  3. `neuronium-agent packs validate packs/my.yaml`.
  4. `neuronium-agent packs install packs/my.yaml`.
  5. `neuronium-agent objective run "<phrase>" --pack my --mock`.

## UC-5 — Inspect tool policy

- **Actors:** SRE.
- **Main flow:** `neuronium-agent packs show coding` → review `tools` and per-agent `permissions`.
