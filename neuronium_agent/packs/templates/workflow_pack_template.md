# Workflow Pack: <name>

## 1. Domain

Example: Coding, Marketing, HR, Sales, Finance, Consulting, Operations.

## 2. What should the user be able to ask?

Write 5-10 common requests in natural language.

- ...
- ...
- ...

## 3. What outcomes should the system produce?

- ...
- ...
- ...

## 4. What agents are needed?

For each agent, fill the block below:

```text
Name:
Role:
Does:
Tools:
Output:
Constraints:
```

```text
Name: Planner
Role: planner
Does: plans the work
Tools: web.search, doc.write
Output: plan
Constraints: do not publish without approval
```

## 5. What tools are needed?

- filesystem
- shell
- web search
- CRM / ATS / analytics / etc.

## 6. What actions are risky?

- editing files
- running shell commands
- sending email
- publishing campaigns
- changing candidate status

## 7. When should a human approve?

- before modifying files
- before sending email
- before publishing
- before changing budget
- before rejecting a candidate

## 8. What memory / context is needed?

- previous runs
- project files
- company policies
- candidate profiles
- prior campaigns

## 9. What quality checks are needed?

- tests pass
- compliance check passes
- critic approves
- budget within limit
- evidence linked

## 10. What should the final output look like?

- markdown report
- patch summary
- candidate shortlist
- campaign calendar
- risks list
- next actions
