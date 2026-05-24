from __future__ import annotations

from app.core.models import ProjectState, Summary, TokenUsage


def summarize_state(state: ProjectState) -> Summary:
    parts = [
        f"Project {state.project_id} is in phase {state.current_phase}.",
        f"Completed agents: {', '.join(state.completed_agents[-6:]) or 'none'}.",
    ]
    if state.requirements:
        parts.append(f"Requirements keys: {', '.join(state.requirements.keys())}.")
    if state.architecture:
        parts.append(f"Architecture keys: {', '.join(state.architecture.keys())}.")
    if state.test_results:
        parts.append(f"QA status: {state.test_results.get('status', 'unknown')}; failures: {state.test_results.get('failed', [])}.")
    if state.security_report:
        parts.append(f"Security critical issues: {state.security_report.get('critical', [])}.")
    if state.approvals:
        pending = [approval.title for approval in state.approvals if approval.status == "pending"]
        parts.append(f"Pending approvals: {pending[:5]}.")
    content = " ".join(parts)
    approx_tokens = max(1, len(content) // 4)
    return Summary(
        project_id=state.project_id,
        after_agent_count=len(state.completed_agents),
        content=content,
        token_usage=TokenUsage(input_tokens=approx_tokens, output_tokens=approx_tokens, estimated_cost_usd=0.0),
    )

