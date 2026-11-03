from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any

from app.core.config import DEFAULT_DEV_VAULT_KEY, PROMPT_LOG_MAX_CHARS
from app.core.models import ActionRequest, AgentExecutionLog, AgentRun, ApprovalRequest, Artifact, AuditLog, ProjectState, RunEvent, Summary
from app.core.vault import decrypt_secret, encrypt_secret

CHECKPOINT_RETENTION = 10


class ClosingConnection(sqlite3.Connection):
    def __exit__(self, exc_type, exc_value, traceback):
        result = super().__exit__(exc_type, exc_value, traceback)
        self.close()
        return result


class SQLiteStore:
    def __init__(self, path: Path, secret_key: str = DEFAULT_DEV_VAULT_KEY) -> None:
        if secret_key == DEFAULT_DEV_VAULT_KEY:
            raise ValueError(
                "SECRET_VAULT_KEY is still set to the default development value. "
                "Set a unique SECRET_VAULT_KEY before starting the server."
            )
        self.path = path
        self.secret_key = secret_key
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.init()

    def connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.path, factory=ClosingConnection)
        conn.row_factory = sqlite3.Row
        return conn

    def init(self) -> None:
        with self.connect() as conn:
            conn.executescript(
                """
                create table if not exists projects (
                    project_id text primary key,
                    state_json text not null,
                    updated_at text not null
                );
                create table if not exists agent_runs (
                    run_id text primary key,
                    project_id text not null,
                    agent_id text not null,
                    run_json text not null,
                    created_at text not null
                );
                create table if not exists artifacts (
                    artifact_id text primary key,
                    project_id text not null,
                    artifact_json text not null,
                    created_at text not null
                );
                create table if not exists approvals (
                    approval_id text primary key,
                    project_id text not null,
                    approval_json text not null,
                    status text not null,
                    created_at text not null
                );
                create table if not exists events (
                    event_id text primary key,
                    project_id text not null,
                    event_json text not null,
                    created_at text not null
                );
                create table if not exists summaries (
                    summary_id text primary key,
                    project_id text not null,
                    summary_json text not null,
                    created_at text not null
                );
                create table if not exists checkpoints (
                    checkpoint_id integer primary key autoincrement,
                    project_id text not null,
                    state_json text not null,
                    created_at text default current_timestamp
                );
                create table if not exists audit_logs (
                    audit_id text primary key,
                    project_id text,
                    audit_json text not null,
                    created_at text not null
                );
                create table if not exists secrets (
                    project_id text not null,
                    name text not null,
                    encrypted_value text not null,
                    updated_at text default current_timestamp,
                    primary key(project_id, name)
                );
                create table if not exists agent_execution_logs (
                    log_id text primary key,
                    project_id text not null,
                    agent_id text not null,
                    log_json text not null,
                    created_at text not null
                );
                create table if not exists action_requests (
                    action_id text primary key,
                    project_id text not null,
                    action_json text not null,
                    status text not null,
                    created_at text not null
                );
                """
            )

    def save_project(self, state: ProjectState) -> None:
        payload = state.model_dump_json()
        with self.connect() as conn:
            conn.execute(
                "insert or replace into projects(project_id, state_json, updated_at) values (?, ?, ?)",
                (state.project_id, payload, state.updated_at.isoformat()),
            )
            conn.execute("insert into checkpoints(project_id, state_json) values (?, ?)", (state.project_id, payload))
            self._prune_checkpoints(conn, state.project_id)

    def _prune_checkpoints(self, conn: sqlite3.Connection, project_id: str) -> None:
        rows = conn.execute(
            "select checkpoint_id from checkpoints where project_id = ? order by checkpoint_id desc",
            (project_id,),
        ).fetchall()
        if len(rows) <= CHECKPOINT_RETENTION:
            return
        stale_ids = [row["checkpoint_id"] for row in rows[CHECKPOINT_RETENTION:]]
        conn.executemany("delete from checkpoints where checkpoint_id = ?", ((checkpoint_id,) for checkpoint_id in stale_ids))

    def get_project(self, project_id: str) -> ProjectState | None:
        with self.connect() as conn:
            row = conn.execute("select state_json from projects where project_id = ?", (project_id,)).fetchone()
        if not row:
            return None
        return ProjectState.model_validate_json(row["state_json"])

    def list_projects(self) -> list[ProjectState]:
        with self.connect() as conn:
            rows = conn.execute("select state_json from projects order by updated_at desc").fetchall()
        return [ProjectState.model_validate_json(row["state_json"]) for row in rows]

    def list_running_projects(self) -> list[ProjectState]:
        return [project for project in self.list_projects() if project.status == "running"]

    def add_agent_run(self, run: AgentRun) -> None:
        self._insert_json("agent_runs", "run_id", run.run_id, run.project_id, "run_json", run.model_dump(), run.created_at.isoformat(), run.agent_id)

    def add_artifact(self, artifact: Artifact) -> None:
        self._insert_json("artifacts", "artifact_id", artifact.artifact_id, artifact.project_id, "artifact_json", artifact.model_dump(), artifact.created_at.isoformat())

    def add_approval(self, approval: ApprovalRequest) -> None:
        with self.connect() as conn:
            conn.execute(
                "insert or replace into approvals(approval_id, project_id, approval_json, status, created_at) values (?, ?, ?, ?, ?)",
                (approval.approval_id, approval.project_id, approval.model_dump_json(), approval.status, approval.created_at.isoformat()),
            )

    def update_approval(self, approval: ApprovalRequest) -> None:
        self.add_approval(approval)

    def add_event(self, event: RunEvent) -> None:
        self._insert_json("events", "event_id", event.event_id, event.project_id, "event_json", event.model_dump(), event.created_at.isoformat())

    def add_summary(self, summary: Summary) -> None:
        self._insert_json("summaries", "summary_id", summary.summary_id, summary.project_id, "summary_json", summary.model_dump(), summary.created_at.isoformat())

    def save_agent_execution_log(self, log: AgentExecutionLog) -> None:
        truncated = log.model_copy(
            update={
                "prompt_system": log.prompt_system[:PROMPT_LOG_MAX_CHARS],
                "prompt_user": log.prompt_user[:PROMPT_LOG_MAX_CHARS],
            }
        )
        self._insert_json(
            "agent_execution_logs",
            "log_id",
            truncated.log_id,
            truncated.project_id,
            "log_json",
            truncated.model_dump(),
            truncated.created_at.isoformat(),
            truncated.agent_id,
        )

    def list_agent_execution_logs(self, project_id: str, limit: int = 100) -> list[AgentExecutionLog]:
        with self.connect() as conn:
            rows = conn.execute(
                "select log_json from agent_execution_logs where project_id = ? order by created_at desc limit ?",
                (project_id, limit),
            ).fetchall()
        return [AgentExecutionLog.model_validate_json(row["log_json"]) for row in rows]

    def list_events(self, project_id: str) -> list[RunEvent]:
        with self.connect() as conn:
            rows = conn.execute("select event_json from events where project_id = ? order by created_at", (project_id,)).fetchall()
        return [RunEvent.model_validate_json(row["event_json"]) for row in rows]

    def get_approval(self, approval_id: str) -> ApprovalRequest | None:
        with self.connect() as conn:
            row = conn.execute("select approval_json from approvals where approval_id = ?", (approval_id,)).fetchone()
        return ApprovalRequest.model_validate_json(row["approval_json"]) if row else None

    def list_approvals(self, project_id: str) -> list[ApprovalRequest]:
        with self.connect() as conn:
            rows = conn.execute("select approval_json from approvals where project_id = ? order by created_at desc", (project_id,)).fetchall()
        return [ApprovalRequest.model_validate_json(row["approval_json"]) for row in rows]

    def add_action_request(self, action: ActionRequest) -> None:
        with self.connect() as conn:
            conn.execute(
                "insert or replace into action_requests(action_id, project_id, action_json, status, created_at) values (?, ?, ?, ?, ?)",
                (action.action_id, action.project_id, action.model_dump_json(), action.status, action.created_at.isoformat()),
            )

    def get_action_request(self, action_id: str) -> ActionRequest | None:
        with self.connect() as conn:
            row = conn.execute("select action_json from action_requests where action_id = ?", (action_id,)).fetchone()
        return ActionRequest.model_validate_json(row["action_json"]) if row else None

    def list_action_requests(self, project_id: str) -> list[ActionRequest]:
        with self.connect() as conn:
            rows = conn.execute(
                "select action_json from action_requests where project_id = ? order by created_at desc",
                (project_id,),
            ).fetchall()
        return [ActionRequest.model_validate_json(row["action_json"]) for row in rows]

    def approved_action_targets(self, project_id: str) -> set[tuple[str, str, str]]:
        actions = self.list_action_requests(project_id)
        return {
            (action.connector_id, action.capability, action.normalized_target)
            for action in actions
            if action.status in {"approved", "executed"}
        }

    def pending_action_count(self, project_id: str) -> int:
        return sum(action.status in {"queued", "blocked"} for action in self.list_action_requests(project_id))

    def cancel_actions_for_attempt(self, project_id: str, attempt_id: str, reason: str) -> list[ActionRequest]:
        """Invalidate approval requests created by an attempt superseded by a retry."""
        cancelled: list[ActionRequest] = []
        for action in self.list_action_requests(project_id):
            if action.attempt_id != attempt_id or action.status not in {"queued", "blocked"}:
                continue
            action.status = "cancelled"
            action.reason = reason
            self.add_action_request(action)
            cancelled.append(action)
        return cancelled

    def add_audit_log(self, audit: AuditLog) -> None:
        with self.connect() as conn:
            conn.execute(
                "insert or replace into audit_logs(audit_id, project_id, audit_json, created_at) values (?, ?, ?, ?)",
                (audit.audit_id, audit.project_id, audit.model_dump_json(), audit.created_at.isoformat()),
            )

    def list_audit_logs(self, project_id: str | None = None, limit: int = 100) -> list[AuditLog]:
        with self.connect() as conn:
            if project_id:
                rows = conn.execute(
                    "select audit_json from audit_logs where project_id = ? order by created_at desc limit ?",
                    (project_id, limit),
                ).fetchall()
            else:
                rows = conn.execute("select audit_json from audit_logs order by created_at desc limit ?", (limit,)).fetchall()
        return [AuditLog.model_validate_json(row["audit_json"]) for row in rows]

    def set_secret(self, project_id: str, name: str, value: str | None) -> None:
        with self.connect() as conn:
            if not value:
                conn.execute("delete from secrets where project_id = ? and name = ?", (project_id, name))
                return
            conn.execute(
                "insert or replace into secrets(project_id, name, encrypted_value, updated_at) values (?, ?, ?, current_timestamp)",
                (project_id, name, encrypt_secret(value, self.secret_key)),
            )

    def get_secret(self, project_id: str, name: str) -> str | None:
        with self.connect() as conn:
            row = conn.execute("select encrypted_value from secrets where project_id = ? and name = ?", (project_id, name)).fetchone()
        return decrypt_secret(row["encrypted_value"], self.secret_key) if row else None

    def has_secret(self, project_id: str, name: str) -> bool:
        with self.connect() as conn:
            row = conn.execute("select 1 from secrets where project_id = ? and name = ?", (project_id, name)).fetchone()
        return bool(row)

    def secret_status(self, project_id: str) -> dict[str, bool]:
        return {
            "provider_api_key": self.has_secret(project_id, "provider_api_key"),
            "provider_base_url": self.has_secret(project_id, "provider_base_url"),
            "github_token": self.has_secret(project_id, "github_token"),
        }

    def _insert_json(
        self,
        table: str,
        id_column: str,
        item_id: str,
        project_id: str,
        json_column: str,
        payload: dict[str, Any],
        created_at: str,
        agent_id: str | None = None,
    ) -> None:
        json_payload = json.dumps(payload, default=str)
        with self.connect() as conn:
            if table in {"agent_runs", "agent_execution_logs"}:
                conn.execute(
                    f"insert or replace into {table}({id_column}, project_id, agent_id, {json_column}, created_at) values (?, ?, ?, ?, ?)",
                    (item_id, project_id, agent_id, json_payload, created_at),
                )
            else:
                conn.execute(
                    f"insert or replace into {table}({id_column}, project_id, {json_column}, created_at) values (?, ?, ?, ?)",
                    (item_id, project_id, json_payload, created_at),
                )
