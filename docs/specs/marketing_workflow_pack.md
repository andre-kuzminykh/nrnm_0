# Marketing Workflow Pack

Agents: `audience_researcher`, `campaign_planner`, `copywriter`, `performance_critic`.

Objectives:
- `create_campaign` — plan a full marketing campaign with audience, channels, copy.
- `analyze_audience` — segment and persona analysis.

Tools (all mocked in v0.1): `web.search`, `analytics.read`, `crm.segment_read`, `doc.write`, `campaign.publish` (critical).

Quality gates: `critic_approves`.

CLI:

```bash
neuronium-agent objective run "Create a marketing campaign for our launch" --pack marketing --mock
```
