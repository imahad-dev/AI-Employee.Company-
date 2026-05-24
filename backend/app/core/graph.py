from __future__ import annotations

from app.core.models import ProjectState
from app.core.routing import route_next


def build_langgraph_app():
    """Build the real LangGraph object when the optional dependency is installed.

    The runtime pipeline service uses the same routing rules and can run without
    LangGraph in mock-only development environments. Installing requirements
    enables this factory for production graph inspection and future migration.
    """
    try:
        from langgraph.graph import END, StateGraph
    except ModuleNotFoundError:
        return None

    graph = StateGraph(ProjectState)

    def passthrough(state: ProjectState) -> ProjectState:
        return state

    for node in [
        "project_manager",
        "requirements_analyst",
        "system_architect",
        "ui_designer",
        "component_planner",
        "frontend_developer",
        "backend_developer",
        "database_agent",
        "qa_agent",
        "code_reviewer",
        "security_agent",
        "devops_agent",
        "docs_writer",
        "monitor_agent",
        "summarizer",
    ]:
        graph.add_node(node, passthrough)

    graph.set_entry_point("project_manager")

    def conditional(state: ProjectState) -> str:
        next_agent = route_next(state)
        return next_agent.value if next_agent else END

    for node in graph.nodes:
        graph.add_conditional_edges(node, conditional)
    return graph.compile()

