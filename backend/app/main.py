from __future__ import annotations

import json
from contextlib import asynccontextmanager
from io import BytesIO
from zipfile import ZIP_DEFLATED, ZipFile

import httpx
from fastapi import APIRouter, Depends, FastAPI, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response, StreamingResponse

from app.agents.catalog import serializable_catalog
from app.agents.providers import build_provider, provider_profiles
from app.core.config import Settings, get_settings
from app.core.http import set_http_client
from app.core.credentials import get_github_token, has_github_token, has_project_api_key, set_github_token, set_project_credentials
from app.core.events import broker
from app.core.github import GitHubClient, GitHubWorkflowError, build_preflight_report, create_project_pull_request, parse_github_repo, summarize_pull_request_status
from app.core.connectors import serializable_connectors
from app.core.missions import get_mission_profile, serializable_mission_profiles
from app.core.models import ActionProposalRequest, ActionResolutionRequest, ApprovalPolicyRequest, AuditLog, BuildAgentRequest, ConnectorSetting, ConnectorSettingsRequest, CreateProjectRequest, GitHubCredentialsRequest, GitHubRepositoryCreateRequest, ProjectCredentialsRequest, ProjectResponse, ProjectState, PullRequestRequest, RepositorySettings, RepositorySettingsRequest, SecretStatus, utc_now
from app.core.policy import create_action_request
from app.core.pipeline import PipelineService
from app.core.workspace import assert_inside, ensure_project_workspace, list_file_tree
from app.db.sqlite import SQLiteStore


def make_service(settings: Settings = Depends(get_settings)) -> PipelineService:
    store = SQLiteStore(settings.database_path, settings.secret_vault_key)
    return PipelineService(store, build_provider(settings), settings)


def require_operator(
    x_operator_key: str | None = Header(default=None),
    settings: Settings = Depends(get_settings),
) -> None:
    if settings.operator_api_key and x_operator_key != settings.operator_api_key:
        raise HTTPException(status_code=401, detail="Operator API key required.")


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    client = httpx.AsyncClient(timeout=settings.provider_timeout_seconds)
    set_http_client(client)
    store = SQLiteStore(settings.database_path, settings.secret_vault_key)
    service = PipelineService(store, build_provider(settings), settings)
    for project in store.list_running_projects():
        await service.resume(project.project_id)
    yield
    await client.aclose()
    set_http_client(None)


app = FastAPI(title="Autonomous AI Software Company", lifespan=lifespan)
protected = APIRouter(dependencies=[Depends(require_operator)])
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health")
def health(settings: Settings = Depends(get_settings)) -> dict[str, object]:
    return {"ok": True, "provider_mode": settings.provider_mode, "max_pipeline_loops": settings.max_pipeline_loops}


@protected.get("/api/agents")
def agents() -> dict[str, object]:
    return {"agents": serializable_catalog(), "performance_agent": {"status": "deferred", "target": "v1.1"}}


@protected.get("/api/providers")
def providers(settings: Settings = Depends(get_settings)) -> dict[str, object]:
    return {
        "active_provider": settings.provider_mode,
        "providers": provider_profiles(),
        "local_base_url": settings.local_base_url,
    }


def audit(service: PipelineService, project_id: str | None, action: str, target: str | None = None, metadata: dict[str, object] | None = None) -> None:
    service.store.add_audit_log(AuditLog(project_id=project_id, action=action, target=target, metadata=metadata or {}))


def provider_ready(mode: str | None, settings: Settings, project_id: str | None = None, service: PipelineService | None = None) -> dict[str, object]:
    selected = (mode or settings.provider_mode).lower()
    runtime_key = has_project_api_key(project_id) if project_id else False
    stored_key = bool(project_id and service and service.store.has_secret(project_id, "provider_api_key"))
    env_keys = {
        "mock": True,
        "anthropic": bool(settings.anthropic_api_key),
        "openai": bool(settings.openai_api_key),
        "gemini": bool(settings.gemini_api_key),
        "groq": bool(settings.groq_api_key),
        "openrouter": bool(settings.openrouter_api_key),
        "local": True,
    }
    ready = selected == "mock" or selected == "local" or runtime_key or stored_key or env_keys.get(selected, False)
    return {
        "provider": selected,
        "ready": ready,
        "has_runtime_key": runtime_key,
        "has_stored_key": stored_key,
        "uses_env_key": env_keys.get(selected, False),
        "message": "Ready to run" if ready else "Paste an API key or configure the matching environment variable before running.",
    }


@app.post("/api/projects", response_model=ProjectResponse)
async def create_project(request: CreateProjectRequest, service: PipelineService = Depends(make_service)) -> ProjectResponse:
    try:
        profile = get_mission_profile(request.mission_profile)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    state = ProjectState(
        project_type=request.project_type,
        client_brief=request.client_brief,
        timeline=request.timeline,
        stack_preferences=request.stack_preferences,
        provider_mode=request.provider_mode,
        model_name=request.model_name,
        agent_model_overrides=request.agent_model_overrides,
        mission_profile=profile.id,
        connector_settings={connector_id: ConnectorSetting(enabled=True) for connector_id in profile.default_connectors},
        status="paused",
    )
    set_project_credentials(state.project_id, request.provider_api_key, request.provider_base_url)
    service.store.set_secret(state.project_id, "provider_api_key", request.provider_api_key)
    service.store.set_secret(state.project_id, "provider_base_url", request.provider_base_url)
    service.store.save_project(state)
    audit(service, state.project_id, "project_created", state.project_id, {"provider": state.provider_mode or "default"})
    return ProjectResponse(project=state)


@protected.get("/api/mission-profiles")
def mission_profiles() -> dict[str, object]:
    return {"profiles": serializable_mission_profiles()}


@protected.get("/api/connectors")
def connectors() -> dict[str, object]:
    return {"connectors": serializable_connectors()}


@protected.post("/api/projects/{project_id}/connectors", response_model=ProjectResponse)
def update_connector_setting(
    project_id: str,
    request: ConnectorSettingsRequest,
    service: PipelineService = Depends(make_service),
) -> ProjectResponse:
    state = service.store.get_project(project_id)
    if not state:
        raise HTTPException(status_code=404, detail="project not found")
    from app.core.connectors import get_connector

    try:
        connector = get_connector(request.connector_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    valid_capabilities = {item.id for item in connector.capabilities}
    unknown = set(request.allowed_capabilities) - valid_capabilities
    if unknown:
        raise HTTPException(status_code=400, detail=f"Unknown capabilities: {', '.join(sorted(unknown))}")
    state.connector_settings[request.connector_id] = ConnectorSetting(
        enabled=request.enabled,
        allowed_capabilities=request.allowed_capabilities,
    )
    state.updated_at = utc_now()
    service.store.save_project(state)
    audit(service, project_id, "connector_setting_updated", request.connector_id, {"enabled": request.enabled, "capabilities": request.allowed_capabilities})
    return ProjectResponse(project=state)


@protected.get("/api/projects/{project_id}/actions")
def list_actions(project_id: str, service: PipelineService = Depends(make_service)) -> dict[str, object]:
    if not service.store.get_project(project_id):
        raise HTTPException(status_code=404, detail="project not found")
    return {"actions": service.store.list_action_requests(project_id)}


@protected.post("/api/projects/{project_id}/actions")
def propose_action(
    project_id: str,
    request: ActionProposalRequest,
    service: PipelineService = Depends(make_service),
) -> dict[str, object]:
    state = service.store.get_project(project_id)
    if not state:
        raise HTTPException(status_code=404, detail="project not found")
    try:
        action = create_action_request(
            state,
            request.connector_id,
            request.capability,
            request.target,
            request.payload,
            request.attempt_id,
            service.store.approved_action_targets(project_id),
            service.store.pending_action_count(project_id),
        )
    except (PermissionError, ValueError) as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    service.store.add_action_request(action)
    audit(service, project_id, "action_classified", action.normalized_target, {"action_id": action.action_id, "connector": action.connector_id, "capability": action.capability, "risk": action.risk, "status": action.status, "payload_hash": action.payload_hash})
    return {"action": action}


@protected.post("/api/actions/{action_id}/resolve")
def resolve_action(
    action_id: str,
    request: ActionResolutionRequest,
    service: PipelineService = Depends(make_service),
) -> dict[str, object]:
    action = service.store.get_action_request(action_id)
    if not action:
        raise HTTPException(status_code=404, detail="action not found")
    if action.status not in {"queued", "blocked"}:
        raise HTTPException(status_code=400, detail=f"Action is already {action.status}.")
    action.status = "approved" if request.approved else "rejected"
    action.reviewer_note = request.note
    action.resolved_at = utc_now()
    service.store.add_action_request(action)
    audit(service, action.project_id, f"action_{action.status}", action.normalized_target, {"action_id": action.action_id, "connector": action.connector_id, "capability": action.capability, "payload_hash": action.payload_hash})
    return {"action": action}


@protected.get("/api/projects")
def list_projects(service: PipelineService = Depends(make_service)) -> dict[str, object]:
    return {"projects": service.store.list_projects()}


@protected.get("/api/projects/{project_id}", response_model=ProjectResponse)
def get_project(project_id: str, service: PipelineService = Depends(make_service)) -> ProjectResponse:
    state = service.store.get_project(project_id)
    if not state:
        raise HTTPException(status_code=404, detail="project not found")
    return ProjectResponse(project=state)


@protected.get("/api/projects/{project_id}/audit")
def project_audit(project_id: str, service: PipelineService = Depends(make_service)) -> dict[str, object]:
    if not service.store.get_project(project_id):
        raise HTTPException(status_code=404, detail="project not found")
    return {"audit_logs": service.store.list_audit_logs(project_id)}


@protected.get("/api/audit")
def audit_logs(service: PipelineService = Depends(make_service)) -> dict[str, object]:
    return {"audit_logs": service.store.list_audit_logs()}


@protected.post("/api/projects/{project_id}/policy", response_model=ProjectResponse)
def update_policy(project_id: str, request: ApprovalPolicyRequest, service: PipelineService = Depends(make_service)) -> ProjectResponse:
    state = service.store.get_project(project_id)
    if not state:
        raise HTTPException(status_code=404, detail="project not found")
    state.approval_policy = request.approval_policy
    state.updated_at = utc_now()
    service.store.save_project(state)
    audit(service, project_id, "approval_policy_updated", project_id, request.approval_policy.model_dump())
    return ProjectResponse(project=state)


@protected.post("/api/projects/{project_id}/repository", response_model=ProjectResponse)
def update_repository(project_id: str, request: RepositorySettingsRequest, service: PipelineService = Depends(make_service)) -> ProjectResponse:
    state = service.store.get_project(project_id)
    if not state:
        raise HTTPException(status_code=404, detail="project not found")
    state.repository = request.repository
    state.updated_at = utc_now()
    service.store.save_project(state)
    audit(service, project_id, "repository_settings_updated", project_id, request.repository.model_dump())
    return ProjectResponse(project=state)


@protected.get("/api/projects/{project_id}/workspace")
def workspace_tree(project_id: str, service: PipelineService = Depends(make_service)) -> dict[str, object]:
    if not service.store.get_project(project_id):
        raise HTTPException(status_code=404, detail="project not found")
    root = ensure_project_workspace(service.settings.workspace_root, project_id)
    return {"root": str(root), "files": list_file_tree(root)}


@protected.get("/api/projects/{project_id}/workspace/file")
def workspace_file(project_id: str, path: str, service: PipelineService = Depends(make_service)) -> dict[str, object]:
    if not service.store.get_project(project_id):
        raise HTTPException(status_code=404, detail="project not found")
    root = ensure_project_workspace(service.settings.workspace_root, project_id)
    target = (root / path).resolve()
    assert_inside(root, target)
    if not target.exists() or not target.is_file():
        raise HTTPException(status_code=404, detail="file not found")
    return {"path": path, "content": target.read_text(encoding="utf-8")}


@protected.get("/api/projects/{project_id}/provider-status")
def project_provider_status(
    project_id: str,
    service: PipelineService = Depends(make_service),
    settings: Settings = Depends(get_settings),
) -> dict[str, object]:
    state = service.store.get_project(project_id)
    if not state:
        raise HTTPException(status_code=404, detail="project not found")
    return provider_ready(state.provider_mode, settings, project_id, service)


@protected.post("/api/projects/{project_id}/credentials")
def update_project_credentials(
    project_id: str,
    request: ProjectCredentialsRequest,
    service: PipelineService = Depends(make_service),
    settings: Settings = Depends(get_settings),
) -> dict[str, object]:
    state = service.store.get_project(project_id)
    if not state:
        raise HTTPException(status_code=404, detail="project not found")
    set_project_credentials(project_id, request.provider_api_key, request.provider_base_url)
    service.store.set_secret(project_id, "provider_api_key", request.provider_api_key)
    service.store.set_secret(project_id, "provider_base_url", request.provider_base_url)
    audit(service, project_id, "credentials_updated", project_id, {"provider": state.provider_mode or settings.provider_mode, "has_key": bool(request.provider_api_key), "has_base_url": bool(request.provider_base_url)})
    return provider_ready(state.provider_mode, settings, project_id, service)


@protected.get("/api/projects/{project_id}/secrets", response_model=SecretStatus)
def project_secret_status(project_id: str, service: PipelineService = Depends(make_service)) -> SecretStatus:
    if not service.store.get_project(project_id):
        raise HTTPException(status_code=404, detail="project not found")
    return SecretStatus(project_id=project_id, **service.store.secret_status(project_id))


def github_ready(state: ProjectState, service: PipelineService) -> dict[str, object]:
    workspace_root = ensure_project_workspace(service.settings.workspace_root, state.project_id)
    workspace_files = list_file_tree(workspace_root)
    provider_ok = state.repository.provider == "github"
    repo_ok = bool(state.repository.repository_url)
    token_ok = has_github_token(state.project_id) or service.store.has_secret(state.project_id, "github_token")
    files_ok = len(workspace_files) > 0
    ready = provider_ok and repo_ok and token_ok and files_ok
    missing = []
    if not provider_ok:
        missing.append("set repository provider to GitHub")
    if not repo_ok:
        missing.append("add a GitHub repository URL")
    if not token_ok:
        missing.append("save a GitHub token")
    if not files_ok:
        missing.append("approve at least one generated file")
    return {
        "ready": ready,
        "provider": state.repository.provider,
        "repository_url": state.repository.repository_url,
        "default_branch": state.repository.default_branch,
        "working_branch": state.repository.working_branch,
        "has_token": token_ok,
        "workspace_file_count": len(workspace_files),
        "message": "Ready to create a GitHub pull request." if ready else "Next: " + ", ".join(missing) + ".",
    }


@protected.get("/api/projects/{project_id}/github/status")
def project_github_status(project_id: str, service: PipelineService = Depends(make_service)) -> dict[str, object]:
    state = service.store.get_project(project_id)
    if not state:
        raise HTTPException(status_code=404, detail="project not found")
    return github_ready(state, service)


@protected.get("/api/projects/{project_id}/github/preflight")
def project_github_preflight(project_id: str, service: PipelineService = Depends(make_service)) -> dict[str, object]:
    state = service.store.get_project(project_id)
    if not state:
        raise HTTPException(status_code=404, detail="project not found")
    workspace_root = ensure_project_workspace(service.settings.workspace_root, project_id)
    return build_preflight_report(state, workspace_root, has_github_token(project_id))


@protected.post("/api/projects/{project_id}/github/credentials")
def update_github_credentials(project_id: str, request: GitHubCredentialsRequest, service: PipelineService = Depends(make_service)) -> dict[str, object]:
    state = service.store.get_project(project_id)
    if not state:
        raise HTTPException(status_code=404, detail="project not found")
    set_github_token(project_id, request.github_token)
    service.store.set_secret(project_id, "github_token", request.github_token)
    audit(service, project_id, "github_credentials_updated", project_id, {"has_token": bool(request.github_token)})
    return github_ready(state, service)


@protected.post("/api/projects/{project_id}/github/repository")
async def create_github_repository(project_id: str, request: GitHubRepositoryCreateRequest, service: PipelineService = Depends(make_service)) -> dict[str, object]:
    state = service.store.get_project(project_id)
    if not state:
        raise HTTPException(status_code=404, detail="project not found")
    token = get_github_token(project_id) or service.store.get_secret(project_id, "github_token")
    if not token:
        raise HTTPException(status_code=400, detail="Save a GitHub token before creating a repository.")
    try:
        repo = await GitHubClient(token, timeout_seconds=service.settings.provider_timeout_seconds).create_repository(
            request.name,
            description=request.description,
            private=request.private,
        )
    except GitHubWorkflowError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    repository_url = repo.get("html_url")
    state.repository = RepositorySettings(
        provider="github",
        repository_url=repository_url,
        default_branch=repo.get("default_branch") or state.repository.default_branch or "main",
        working_branch=state.repository.working_branch,
    )
    state.updated_at = utc_now()
    service.store.save_project(state)
    result = {
        "name": repo.get("full_name"),
        "url": repository_url,
        "private": repo.get("private"),
        "default_branch": repo.get("default_branch"),
    }
    audit(service, project_id, "github_repository_created", str(repository_url), result)
    return {"repository": result, "project": state}


@protected.post("/api/projects/{project_id}/github/pull-request")
async def create_github_pull_request(project_id: str, request: PullRequestRequest, service: PipelineService = Depends(make_service)) -> dict[str, object]:
    state = service.store.get_project(project_id)
    if not state:
        raise HTTPException(status_code=404, detail="project not found")
    token = get_github_token(project_id) or service.store.get_secret(project_id, "github_token")
    if not token:
        raise HTTPException(status_code=400, detail="Save a GitHub token before creating a pull request.")
    workspace_root = ensure_project_workspace(service.settings.workspace_root, project_id)
    try:
        result = await create_project_pull_request(
            state,
            workspace_root,
            token,
            title=request.title,
            body=request.body,
            branch=request.branch,
            timeout_seconds=service.settings.provider_timeout_seconds,
        )
    except GitHubWorkflowError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    audit(service, project_id, "github_pr_created", str(result.get("url")), result)
    return {"pull_request": result}


def latest_pull_request_from_audit(service: PipelineService, project_id: str) -> dict[str, object] | None:
    logs = service.store.list_audit_logs(project_id, limit=100)
    for log in logs:
        if log.action == "github_pr_created":
            return log.metadata
    return None


@protected.get("/api/projects/{project_id}/github/pull-request/status")
async def github_pull_request_status(project_id: str, service: PipelineService = Depends(make_service)) -> dict[str, object]:
    state = service.store.get_project(project_id)
    if not state:
        raise HTTPException(status_code=404, detail="project not found")
    token = get_github_token(project_id) or service.store.get_secret(project_id, "github_token")
    if not token:
        raise HTTPException(status_code=400, detail="Save a GitHub token before checking pull request status.")
    latest = latest_pull_request_from_audit(service, project_id)
    if not latest or not latest.get("number"):
        raise HTTPException(status_code=404, detail="No GitHub pull request has been created for this project yet.")
    if not state.repository.repository_url:
        raise HTTPException(status_code=400, detail="Repository URL is missing.")
    try:
        owner, repo = parse_github_repo(state.repository.repository_url)
        client = GitHubClient(token, timeout_seconds=service.settings.provider_timeout_seconds)
        pr = await client.get_pull_request(owner, repo, int(latest["number"]))
        files = await client.list_pull_request_files(owner, repo, int(latest["number"]))
        reviews = await client.list_pull_request_reviews(owner, repo, int(latest["number"]))
        head_sha = str(pr.get("head", {}).get("sha") or latest.get("branch") or "")
        checks = await client.list_check_runs(owner, repo, head_sha) if head_sha else []
    except GitHubWorkflowError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    result = summarize_pull_request_status(pr, files, reviews, checks)
    audit(service, project_id, "github_pr_status_checked", str(result.get("url")), {"merge_ready": result.get("merge_ready"), "number": result.get("number")})
    return {"pull_request_status": result}


@protected.get("/api/projects/{project_id}/export")
def export_project(project_id: str, service: PipelineService = Depends(make_service)) -> Response:
    state = service.store.get_project(project_id)
    if not state:
        raise HTTPException(status_code=404, detail="project not found")

    events = service.store.list_events(project_id)
    approvals = service.store.list_approvals(project_id)
    buffer = BytesIO()
    with ZipFile(buffer, "w", ZIP_DEFLATED) as archive:
        archive.writestr("project.json", state.model_dump_json(indent=2))
        archive.writestr("events.json", json.dumps([event.model_dump(mode="json") for event in events], indent=2))
        archive.writestr("approvals.json", json.dumps([approval.model_dump(mode="json") for approval in approvals], indent=2))
        archive.writestr("summaries.md", "\n\n".join(state.summaries) or "No summaries yet.")
        for artifact in state.artifacts:
            safe_name = "".join(char if char.isalnum() or char in "-_." else "_" for char in artifact.name)
            archive.writestr(f"artifacts/{safe_name or artifact.artifact_id}.json", artifact.model_dump_json(indent=2))
        workspace_root = ensure_project_workspace(service.settings.workspace_root, project_id)
        for file_info in list_file_tree(workspace_root, max_files=500):
            file_path = workspace_root / str(file_info["path"])
            archive.writestr(f"workspace/{file_info['path']}", file_path.read_text(encoding="utf-8"))
    return Response(
        content=buffer.getvalue(),
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="{project_id}.zip"'},
    )


@protected.post("/api/projects/{project_id}/start", response_model=ProjectResponse)
async def start_project(
    project_id: str,
    service: PipelineService = Depends(make_service),
    settings: Settings = Depends(get_settings),
) -> ProjectResponse:
    try:
        existing = service.store.get_project(project_id)
        if not existing:
            raise KeyError(project_id)
        stored_key = service.store.get_secret(project_id, "provider_api_key")
        stored_base = service.store.get_secret(project_id, "provider_base_url")
        if stored_key or stored_base:
            set_project_credentials(project_id, stored_key, stored_base)
        readiness = provider_ready(existing.provider_mode, settings, project_id, service)
        if existing.approval_policy.block_on_provider_not_ready and not readiness["ready"]:
            raise HTTPException(status_code=400, detail=readiness["message"])
        state = await service.start(project_id)
    except KeyError:
        raise HTTPException(status_code=404, detail="project not found")
    return ProjectResponse(project=state)


@protected.get("/api/projects/{project_id}/events")
async def project_events(project_id: str, service: PipelineService = Depends(make_service)) -> StreamingResponse:
    if not service.store.get_project(project_id):
        raise HTTPException(status_code=404, detail="project not found")

    async def stream():
        for event in service.store.list_events(project_id):
            yield f"data: {event.model_dump_json()}\n\n"
        async for event in broker.subscribe(project_id):
            yield f"data: {event.model_dump_json()}\n\n"

    return StreamingResponse(stream(), media_type="text/event-stream")


@protected.get("/api/projects/{project_id}/approvals")
def approvals(project_id: str, service: PipelineService = Depends(make_service)) -> dict[str, object]:
    return {"approvals": service.store.list_approvals(project_id)}


@protected.post("/api/approvals/{approval_id}/approve")
async def approve(approval_id: str, service: PipelineService = Depends(make_service)) -> dict[str, object]:
    try:
        approval = await service.resolve_approval(approval_id, True)
        return {"approval": approval}
    except KeyError:
        raise HTTPException(status_code=404, detail="approval not found")


@protected.post("/api/approvals/{approval_id}/reject")
async def reject(approval_id: str, body: dict[str, str] | None = None, service: PipelineService = Depends(make_service)) -> dict[str, object]:
    try:
        approval = await service.resolve_approval(approval_id, False, (body or {}).get("note"))
        return {"approval": approval}
    except KeyError:
        raise HTTPException(status_code=404, detail="approval not found")


@protected.post("/api/projects/{project_id}/agents/build")
async def build_agent(project_id: str, request: BuildAgentRequest, service: PipelineService = Depends(make_service)) -> dict[str, object]:
    try:
        approval = await service.build_agent_preview(project_id, request.agent_id, request.instructions)
        return {"approval": approval}
    except KeyError:
        raise HTTPException(status_code=404, detail="project not found")


app.include_router(protected)
