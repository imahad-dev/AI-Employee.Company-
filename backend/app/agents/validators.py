from __future__ import annotations

from app.core.models import AgentId, AgentOutput


def semantic_errors(agent_id: AgentId, output: AgentOutput) -> list[str]:
    errors: list[str] = []
    if not output.summary.strip():
        errors.append("summary is required")

    data = output.data
    if agent_id == AgentId.requirements_analyst and not data.get("acceptance_criteria"):
        errors.append("requirements must include acceptance_criteria")
    if agent_id == AgentId.system_architect and not (data.get("api") or data.get("api_spec")):
        errors.append("architecture must include API contracts")
    if agent_id == AgentId.frontend_developer and not (data.get("files") or output.artifacts or output.approvals):
        errors.append("frontend output must include files, artifacts, or approval proposals")
    if agent_id == AgentId.backend_developer and not (data.get("services") or data.get("apis") or output.approvals):
        errors.append("backend output must include services, APIs, or approval proposals")
    if agent_id == AgentId.qa_agent and "failed" not in data:
        errors.append("QA output must include failed list")
    if agent_id == AgentId.code_reviewer and data.get("score", 10) < 0:
        errors.append("review score cannot be negative")
    if agent_id == AgentId.security_agent and "critical" not in data:
        errors.append("security output must include critical list")
    if agent_id == AgentId.devops_agent and not output.approvals:
        errors.append("DevOps output must create an approval-gated deployment plan")

    for approval in output.approvals:
        if not approval.get("kind") or not approval.get("payload"):
            errors.append("approval proposals require kind and payload")
    return errors

