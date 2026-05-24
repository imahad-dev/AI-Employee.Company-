from __future__ import annotations

from app.core.models import AgentId, ProjectState


PHASE_TO_AGENT: dict[str, AgentId] = {
    "intake": AgentId.project_manager,
    "requirements": AgentId.requirements_analyst,
    "architecture": AgentId.system_architect,
    "design": AgentId.ui_designer,
    "components": AgentId.component_planner,
    "frontend": AgentId.frontend_developer,
    "backend": AgentId.backend_developer,
    "database": AgentId.database_agent,
    "testing": AgentId.qa_agent,
    "review": AgentId.code_reviewer,
    "security": AgentId.security_agent,
    "deployment": AgentId.devops_agent,
    "docs": AgentId.docs_writer,
    "monitoring": AgentId.monitor_agent,
}


def should_summarize(state: ProjectState, interval: int) -> bool:
    completed = len(state.completed_agents)
    return completed > 0 and completed % interval == 0 and completed not in state.summarized_counts


def route_next(state: ProjectState, max_loops: int = 10) -> AgentId | None:
    if state.loop_count >= max_loops:
        return None

    phase = state.current_phase
    if phase == "testing" and state.test_results.get("failed"):
        failures = state.test_results["failed"]
        if any("frontend" in str(item).lower() for item in failures):
            return AgentId.frontend_developer
        return AgentId.backend_developer

    if phase == "security" and state.security_report.get("critical"):
        return AgentId.backend_developer

    if phase == "review":
        latest = state.review_feedback[-1] if state.review_feedback else {}
        if latest.get("score", 10) < 7:
            return AgentId.frontend_developer

    if phase == "monitoring" and state.incidents:
        return AgentId.project_manager

    if phase == "completed":
        return None

    return PHASE_TO_AGENT.get(phase)
