# Workflow Pack: HR Hiring Assistant

## 1. Domain

HR.

## 2. What should the user be able to ask?

- screen candidates for a senior backend role
- create interview plan for a Series A startup
- evaluate candidate fit

## 3. What outcomes should the system produce?

- candidate shortlist
- interview plan
- candidate evaluation summary

## 4. What agents are needed?

```text
Name: Screener
Role: executor
Does: rank candidates by skill match
Tools: ats_search, doc_write
Output: shortlist
```

```text
Name: Interviewer
Role: executor
Does: produce interview questions
Tools: doc_write
Output: questions
```

```text
Name: Compliance
Role: critic
Does: verify policy compliance
Tools:
Output: verdict
```

## 5. What tools are needed?

- ATS search
- doc write
- calendar create
- email draft

## 6. What actions are risky?

- changing candidate status
- sending email
- rejecting candidate

## 7. When should a human approve?

- before sending email
- before rejecting a candidate
- before publishing

## 8. What memory / context is needed?

- candidate profiles
- prior interviews
- company hiring policy

## 9. What quality checks are needed?

- compliance passes
- evidence linked

## 10. What should the final output look like?

- markdown report
- shortlist table
- next actions
