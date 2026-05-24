# Agent Contracts

Every agent returns strict JSON:

```json
{
  "phase": "next_phase",
  "summary": "short operational summary",
  "data": {},
  "artifacts": [],
  "approvals": [],
  "errors": []
}
```

The backend validates the shape with Pydantic and then applies semantic checks:

- Requirements must include acceptance criteria.
- Architecture must include API contracts.
- Frontend and backend agents must produce code-oriented outputs or approval proposals.
- QA must include a `failed` list.
- Security must include a `critical` list.
- DevOps must create an approval-gated deployment plan.

Approval kinds:

- `file_write`
- `dependency_install`
- `shell_command`
- `git_commit`
- `deployment_plan`

