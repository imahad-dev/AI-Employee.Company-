from __future__ import annotations

import asyncio
from datetime import timezone
from typing import Any

from app.agents.catalog import AGENT_CONFIGS
from app.agents.prompts import build_user_prompt, system_prompt
from app.agents.providers import LlmProvider
from app.agents.validators import semantic_errors
from app.core.config import Settings
from app.core.diffing import attach_diff
from app.core.events import broker
from app.core.models import AgentId, AgentRun, ApprovalRequest, Artifact, AuditLog, ProjectState, RunEvent, utc_now
from app.core.routing import route_next, should_summarize
from app.core.summarizer import summarize_state
from app.core.workspace import assert_inside, ensure_project_workspace
from app.db.sqlite import SQLiteStore


class PipelineService:
    def __init__(self, store: SQLiteStore, provider: LlmProvider, settings: Settings) -> None:
        self.store = store
        self.provider = provider
        self.settings = settings
        self._tasks: dict[str, asyncio.Task[None]] = {}

    async def start(self, project_id: str) -> ProjectState:
        state = self._require_project(project_id)
        state.status = "running"
        state.updated_at = utc_now()
        self.store.save_project(state)
        self._audit(state.project_id, "pipeline_started", "project", {"phase": state.current_phase})
        await self._event(state.project_id, "project", "Pipeline started")
        if project_id not in self._tasks or self._tasks[project_id].done():
            self._tasks[project_id] = asyncio.create_task(self.run(project_id))
        return state

    async def run(self, project_id: str) -> None:
        state = self._require_project(project_id)
        while state.status == "running":
            if should_summarize(state, self.settings.summarizer_interval):
                await self._summarize(state)
                state = self._require_project(project_id)

            agent_id = route_next(state, self.settings.max_pipeline_loops)
            if agent_id is None:
                state.status = "completed" if state.current_phase == "completed" else "failed"
                if state.loop_count >= self.settings.max_pipeline_loops:
                    state.errors.append("Loop guard reached before completion")
                    self._audit(project_id, "pipeline_loop_guard", "project", {"loop_count": state.loop_count})
                    await self._event(project_id, "error", "Loop guard reached before completion")
                else:
                    self._audit(project_id, "pipeline_completed", "project", {"completed_agents": len(state.completed_agents)})
                    await self._event(project_id, "project", "Pipeline completed")
                state.updated_at = utc_now()
                self.store.save_project(state)
                return

            await self._run_agent(state, agent_id)
            state = self._require_project(project_id)

    async def build_agent_preview(self, project_id: str, agent_id: AgentId, instructions: str | None = None) -> ApprovalRequest:
        state = self._require_project(project_id)
        config = AGENT_CONFIGS[agent_id]
        content = {
            "path": f"{project_id}/agents/{agent_id.value}.py",
            "content": (
                f"# Generated preview for {config.name}\n"
                f"AGENT_ID = {agent_id.value!r}\n"
                f"ROLE = {config.role!r}\n"
                f"INSTRUCTIONS = {instructions or 'Use configured system prompt.'!r}\n"
            ),
        }
        content = attach_diff(content, self.settings.workspace_root)
        approval = ApprovalRequest(
            project_id=project_id,
            agent_id=agent_id.value,
            kind="file_write",
            title=f"Build {config.name} agent code",
            payload=content,
        )
        state.approvals.append(approval)
        state.updated_at = utc_now()
        self.store.add_approval(approval)
        self.store.save_project(state)
        self._audit(project_id, "approval_created", approval.approval_id, {"kind": approval.kind, "agent_id": agent_id.value})
        await self._event(project_id, "approval", f"Generated preview for {config.name}", agent_id.value, {"approval_id": approval.approval_id})
        return approval

    async def resolve_approval(self, approval_id: str, approved: bool, note: str | None = None) -> ApprovalRequest:
        approval = self.store.get_approval(approval_id)
        if not approval:
            raise KeyError(f"approval {approval_id} not found")
        state = self._require_project(approval.project_id)
        approval.status = "approved" if approved else "rejected"
        approval.reviewer_note = note
        approval.resolved_at = utc_now()
        self.store.update_approval(approval)

        state.approvals = [approval if item.approval_id == approval_id else item for item in state.approvals]
        if approved:
            self._apply_approved_action(approval)
        state.updated_at = utc_now()
        self.store.save_project(state)
        self._audit(approval.project_id, f"approval_{approval.status}", approval.approval_id, {"kind": approval.kind, "agent_id": approval.agent_id})
        await self._event(approval.project_id, "approval", f"Approval {approval.status}: {approval.title}", approval.agent_id)
        return approval

    async def _run_agent(self, state: ProjectState, agent_id: AgentId) -> None:
        config = AGENT_CONFIGS[agent_id]
        state.active_agent = agent_id.value
        state.loop_count += 1
        state.updated_at = utc_now()
        self.store.save_project(state)
        self._audit(state.project_id, "agent_started", agent_id.value, {"phase": state.current_phase})
        await self._event(state.project_id, "agent", f"{config.name} started", agent_id.value)

        try:
            output = await self.provider.complete_agent(agent_id, system_prompt(config), build_user_prompt(agent_id, state), state)
            errors = semantic_errors(agent_id, output)
            if errors:
                raise ValueError("; ".join(errors))

            setattr_target = getattr(state, config.state_key)
            if config.state_key == "incidents":
                state.incidents.extend(output.data.get("incidents", []))
            elif isinstance(setattr_target, list):
                setattr_target.append(output.data)
            elif isinstance(setattr_target, dict) and config.state_key == "code_files":
                state.code_files.update(output.data.get("files", {}))
            else:
                setattr(state, config.state_key, output.data)

            for artifact_payload in output.artifacts:
                artifact = Artifact(
                    project_id=state.project_id,
                    agent_id=agent_id.value,
                    name=artifact_payload.get("name", f"{config.name} artifact"),
                    kind=artifact_payload.get("kind", "json"),
                    content=artifact_payload.get("content", artifact_payload),
                )
                state.artifacts.append(artifact)
                self.store.add_artifact(artifact)

            for proposal in output.approvals:
                payload = proposal["payload"]
                if proposal["kind"] == "file_write":
                    payload = attach_diff(payload, self.settings.workspace_root)
                approval = ApprovalRequest(
                    project_id=state.project_id,
                    agent_id=agent_id.value,
                    kind=proposal["kind"],
                    title=proposal.get("title", f"{config.name} approval"),
                    payload=payload,
                )
                state.approvals.append(approval)
                self.store.add_approval(approval)
                self._audit(state.project_id, "approval_created", approval.approval_id, {"kind": approval.kind, "agent_id": agent_id.value})

            state.current_phase = output.phase
            if agent_id.value not in state.completed_agents:
                state.completed_agents.append(agent_id.value)
            state.token_usage.input_tokens += output.token_usage.input_tokens
            state.token_usage.output_tokens += output.token_usage.output_tokens
            state.token_usage.estimated_cost_usd = round(state.token_usage.estimated_cost_usd + output.token_usage.estimated_cost_usd, 4)
            if state.current_phase == "completed":
                state.status = "completed"

            run = AgentRun(project_id=state.project_id, agent_id=agent_id.value, status="completed", output=output.model_dump(), token_usage=output.token_usage)
            self.store.add_agent_run(run)
            state.updated_at = utc_now()
            self.store.save_project(state)
            self._audit(state.project_id, "agent_completed", agent_id.value, {"phase": state.current_phase, "cost": output.token_usage.estimated_cost_usd})
            await self._event(state.project_id, "agent", f"{config.name} completed", agent_id.value, {"phase": state.current_phase})
        except Exception as exc:
            message = f"{config.name} failed: {exc}"
            state.errors.append(message)
            state.status = "failed"
            run = AgentRun(project_id=state.project_id, agent_id=agent_id.value, status="failed", errors=[str(exc)])
            self.store.add_agent_run(run)
            state.updated_at = utc_now()
            self.store.save_project(state)
            self._audit(state.project_id, "agent_failed", agent_id.value, {"error": str(exc)})
            await self._event(state.project_id, "error", message, agent_id.value)

    async def _summarize(self, state: ProjectState) -> None:
        summary = summarize_state(state)
        if summary.after_agent_count in state.summarized_counts:
            return
        state.summaries.append(summary.content)
        state.summarized_counts.append(summary.after_agent_count)
        state.token_usage.input_tokens += summary.token_usage.input_tokens
        state.token_usage.output_tokens += summary.token_usage.output_tokens
        state.updated_at = utc_now()
        self.store.add_summary(summary)
        self.store.save_project(state)
        self._audit(state.project_id, "context_summarized", "summarizer", {"after_agent_count": summary.after_agent_count})
        await self._event(state.project_id, "summary", f"Summarized context after {summary.after_agent_count} agents")

    async def _event(self, project_id: str, event_type: str, message: str, agent_id: str | None = None, data: dict[str, Any] | None = None) -> None:
        event = RunEvent(project_id=project_id, type=event_type, message=message, agent_id=agent_id, data=data or {})
        self.store.add_event(event)
        await broker.publish(event)

    def _require_project(self, project_id: str) -> ProjectState:
        state = self.store.get_project(project_id)
        if not state:
            raise KeyError(f"project {project_id} not found")
        return state

    def _apply_approved_action(self, approval: ApprovalRequest) -> None:
        if approval.kind != "file_write":
            return
        path_value = approval.payload.get("path")
        content = approval.payload.get("content", "")
        if not path_value:
            raise ValueError("file_write approval missing path")
        workspace_root = ensure_project_workspace(self.settings.workspace_root, approval.project_id)
        raw_path = str(path_value)
        if raw_path.startswith(f"{approval.project_id}/"):
            raw_path = raw_path[len(approval.project_id) + 1 :]
        target = (workspace_root / raw_path).resolve()
        assert_inside(workspace_root, target)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content if isinstance(content, str) else str(content), encoding="utf-8")
        self._audit(approval.project_id, "workspace_file_written", raw_path, {"approval_id": approval.approval_id})

    def _audit(self, project_id: str | None, action: str, target: str | None = None, metadata: dict[str, Any] | None = None) -> None:
        self.store.add_audit_log(AuditLog(project_id=project_id, action=action, target=target, metadata=metadata or {}))
