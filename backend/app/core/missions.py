from __future__ import annotations

from dataclasses import dataclass

from app.core.models import AgentId


@dataclass(frozen=True)
class MissionProfile:
    id: str
    name: str
    description: str
    default_connectors: tuple[str, ...]
    specialist_agents: tuple[AgentId, ...]
    quality_focus: tuple[str, ...]


SOFTWARE_DELIVERY = MissionProfile(
    id="software_delivery",
    name="Software Delivery",
    description="Plans, researches, builds, reviews, and prepares software projects through approval-gated delivery.",
    default_connectors=("governance", "web_research", "github_read", "document_store"),
    specialist_agents=(
        AgentId.project_manager,
        AgentId.requirements_analyst,
        AgentId.system_architect,
        AgentId.ui_designer,
        AgentId.component_planner,
        AgentId.frontend_developer,
        AgentId.backend_developer,
        AgentId.database_agent,
        AgentId.qa_agent,
        AgentId.code_reviewer,
        AgentId.security_agent,
        AgentId.devops_agent,
        AgentId.docs_writer,
        AgentId.monitor_agent,
    ),
    quality_focus=("acceptance criteria", "safe implementation", "test coverage", "security", "approval-gated delivery"),
)


MISSION_PROFILES: dict[str, MissionProfile] = {SOFTWARE_DELIVERY.id: SOFTWARE_DELIVERY}


def get_mission_profile(profile_id: str) -> MissionProfile:
    try:
        return MISSION_PROFILES[profile_id]
    except KeyError as exc:
        raise ValueError(f"Unknown mission profile: {profile_id}") from exc


def serializable_mission_profiles() -> list[dict[str, object]]:
    return [
        {
            "id": profile.id,
            "name": profile.name,
            "description": profile.description,
            "default_connectors": list(profile.default_connectors),
            "specialist_agents": [agent.value for agent in profile.specialist_agents],
            "quality_focus": list(profile.quality_focus),
        }
        for profile in MISSION_PROFILES.values()
    ]
