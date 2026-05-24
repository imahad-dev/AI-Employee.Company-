from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any

from pydantic import TypeAdapter

from app.core.models import AgentRun, ApprovalRequest, Artifact, AuditLog, ProjectState, RunEvent, Summary


class ClosingConnection(sqlite3.Connection):
    def __exit__(self, exc_type, exc_value, traceback):
        result = super().__exit__(exc_type, exc_value, traceback)
        self.close()
        return result


class SQLiteStore:
    def __init__(self, path: Path) -> None:
        self.path = path
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
            if table == "agent_runs":
                conn.execute(
                    f"insert or replace into {table}({id_column}, project_id, agent_id, {json_column}, created_at) values (?, ?, ?, ?, ?)",
                    (item_id, project_id, agent_id, json_payload, created_at),
                )
            else:
                conn.execute(
                    f"insert or replace into {table}({id_column}, project_id, {json_column}, created_at) values (?, ?, ?, ?)",
                    (item_id, project_id, json_payload, created_at),
                )
