from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Literal
from uuid import uuid4

from pydantic import BaseModel, Field, field_validator


ProjectType = Literal["webapp", "dashboard", "game", "system", "workflow"]
ProjectStatus = Literal["running", "paused", "completed", "failed"]
ApprovalKind = Literal["file_write", "dependency_install", "shell_command", "git_commit", "deployment_plan"]
ProviderMode = Literal["mock", "anthropic", "openai", "gemini", "groq", "openrouter", "local"]


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class AgentId(str, Enum):
    project_manager = "project_manager"
    requirements_analyst = "requirements_analyst"
    system_architect = "system_architect"
    ui_designer = "ui_designer"
    component_planner = "component_planner"
    frontend_developer = "frontend_developer"
    backend_developer = "backend_developer"
    database_agent = "database_agent"
    qa_agent = "qa_agent"
    code_reviewer = "code_reviewer"
    security_agent = "security_agent"
    devops_agent = "devops_agent"
    docs_writer = "docs_writer"
    monitor_agent = "monitor_agent"
    summarizer = "summarizer"


PIPELINE_AGENT_IDS: list[AgentId] = [
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
]


class TokenUsage(BaseModel):
    input_tokens: int = 0
    output_tokens: int = 0
    estimated_cost_usd: float = 0.0


class Artifact(BaseModel):
    artifact_id: str = Field(default_factory=lambda: str(uuid4()))
    project_id: str
    agent_id: str
    name: str
    kind: str
    content: dict[str, Any] | list[Any] | str
    created_at: datetime = Field(default_factory=utc_now)


class ApprovalRequest(BaseModel):
    approval_id: str = Field(default_factory=lambda: str(uuid4()))
    project_id: str
    agent_id: str
    kind: ApprovalKind
    title: str
    payload: dict[str, Any]
    status: Literal["pending", "approved", "rejected"] = "pending"
    reviewer_note: str | None = None
    created_at: datetime = Field(default_factory=utc_now)
    resolved_at: datetime | None = None

    @field_validator("payload")
    @classmethod
    def payload_cannot_be_empty(cls, value: dict[str, Any]) -> dict[str, Any]:
        if not value:
            raise ValueError("approval payload cannot be empty")
        return value


class ApprovalPolicy(BaseModel):
    require_file_write_approval: bool = True
    require_dependency_approval: bool = True
    require_shell_approval: bool = True
    require_commit_approval: bool = True
    require_deployment_approval: bool = True
    block_on_provider_not_ready: bool = True
    max_auto_loop_count: int = 10


class AuditLog(BaseModel):
    audit_id: str = Field(default_factory=lambda: str(uuid4()))
    project_id: str | None = None
    actor: str = "system"
    action: str
    target: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=utc_now)


class RepositorySettings(BaseModel):
    provider: Literal["local", "github", "gitlab"] = "local"
    repository_url: str | None = None
    default_branch: str = "main"
    working_branch: str | None = None


class RunEvent(BaseModel):
    event_id: str = Field(default_factory=lambda: str(uuid4()))
    project_id: str
    type: Literal["project", "agent", "summary", "approval", "error", "cost"]
    message: str
    agent_id: str | None = None
    data: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=utc_now)


class AgentRun(BaseModel):
    run_id: str = Field(default_factory=lambda: str(uuid4()))
    project_id: str
    agent_id: str
    status: Literal["started", "completed", "failed"]
    output: dict[str, Any] = Field(default_factory=dict)
    errors: list[str] = Field(default_factory=list)
    token_usage: TokenUsage = Field(default_factory=TokenUsage)
    created_at: datetime = Field(default_factory=utc_now)


class Summary(BaseModel):
    summary_id: str = Field(default_factory=lambda: str(uuid4()))
    project_id: str
    after_agent_count: int
    content: str
    token_usage: TokenUsage = Field(default_factory=TokenUsage)
    created_at: datetime = Field(default_factory=utc_now)


class AgentOutput(BaseModel):
    phase: str
    summary: str
    data: dict[str, Any] = Field(default_factory=dict)
    artifacts: list[dict[str, Any]] = Field(default_factory=list)
    approvals: list[dict[str, Any]] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)
    token_usage: TokenUsage = Field(default_factory=TokenUsage)


class ProjectState(BaseModel):
    project_id: str = Field(default_factory=lambda: f"proj_{uuid4().hex[:10]}")
    project_type: ProjectType
    client_brief: str
    timeline: str | None = None
    stack_preferences: str | None = None
    provider_mode: ProviderMode | None = None
    model_name: str | None = None
    agent_model_overrides: dict[str, str] = Field(default_factory=dict)
    repository: RepositorySettings = Field(default_factory=RepositorySettings)

    sprint_plan: dict[str, Any] = Field(default_factory=dict)
    requirements: dict[str, Any] = Field(default_factory=dict)
    architecture: dict[str, Any] = Field(default_factory=dict)
    design_spec: dict[str, Any] = Field(default_factory=dict)
    component_plan: dict[str, Any] = Field(default_factory=dict)
    code_files: dict[str, str] = Field(default_factory=dict)
    backend_plan: dict[str, Any] = Field(default_factory=dict)
    database_plan: dict[str, Any] = Field(default_factory=dict)
    test_results: dict[str, Any] = Field(default_factory=dict)
    review_feedback: list[dict[str, Any]] = Field(default_factory=list)
    security_report: dict[str, Any] = Field(default_factory=dict)
    deployment_config: dict[str, Any] = Field(default_factory=dict)
    docs: dict[str, Any] = Field(default_factory=dict)
    performance_report: dict[str, Any] = Field(default_factory=dict)
    incidents: list[dict[str, Any]] = Field(default_factory=list)

    summaries: list[str] = Field(default_factory=list)
    summarized_counts: list[int] = Field(default_factory=list)
    artifacts: list[Artifact] = Field(default_factory=list)
    approvals: list[ApprovalRequest] = Field(default_factory=list)
    approval_policy: ApprovalPolicy = Field(default_factory=ApprovalPolicy)
    events: list[RunEvent] = Field(default_factory=list)
    token_usage: TokenUsage = Field(default_factory=TokenUsage)

    current_phase: str = "intake"
    active_agent: str = "project_manager"
    completed_agents: list[str] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)
    loop_count: int = 0
    status: ProjectStatus = "paused"
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)

    @field_validator("client_brief")
    @classmethod
    def brief_must_have_content(cls, value: str) -> str:
        if len(value.strip()) < 10:
            raise ValueError("client brief must contain at least 10 characters")
        return value.strip()


class CreateProjectRequest(BaseModel):
    project_type: ProjectType = "webapp"
    client_brief: str
    timeline: str | None = None
    stack_preferences: str | None = None
    provider_mode: ProviderMode | None = None
    model_name: str | None = None
    agent_model_overrides: dict[str, str] = Field(default_factory=dict)
    provider_api_key: str | None = None
    provider_base_url: str | None = None
    budget_warning_usd: float | None = None


class ProjectCredentialsRequest(BaseModel):
    provider_api_key: str | None = None
    provider_base_url: str | None = None


class GitHubCredentialsRequest(BaseModel):
    github_token: str | None = None


class PullRequestRequest(BaseModel):
    title: str | None = None
    body: str | None = None
    branch: str | None = None


class GitHubRepositoryCreateRequest(BaseModel):
    name: str
    description: str | None = None
    private: bool = True


class ApprovalPolicyRequest(BaseModel):
    approval_policy: ApprovalPolicy


class RepositorySettingsRequest(BaseModel):
    repository: RepositorySettings


class ProjectResponse(BaseModel):
    project: ProjectState


class BuildAgentRequest(BaseModel):
    agent_id: AgentId
    instructions: str | None = None
