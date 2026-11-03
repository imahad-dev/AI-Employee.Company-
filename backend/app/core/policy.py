from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from typing import Any

from app.core.connectors import get_capability
from app.core.models import ActionRequest, ProjectState


@dataclass(frozen=True)
class PolicyDecision:
    risk: str
    requires_approval: bool
    normalized_target: str
    reason: str
    payload_hash: str


def _canonical_payload(payload: dict[str, Any]) -> str:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)


def payload_hash(payload: dict[str, Any]) -> str:
    return hashlib.sha256(_canonical_payload(payload).encode("utf-8")).hexdigest()


def normalize_target(connector_id: str, capability: str, target: str) -> str:
    value = target.strip().lower()
    if not value:
        raise ValueError("Action target cannot be empty.")
    if connector_id.startswith("github"):
        value = value.replace("https://github.com/", "").replace("git@github.com:", "")
        value = re.sub(r"\.git(?=/|$)", "", value)
        return re.sub(r"/+", "/", value).strip("/")
    if connector_id == "email_triage":
        return value
    return value.replace("\\", "/")


def classify_action(
    state: ProjectState,
    connector_id: str,
    capability: str,
    target: str,
    payload: dict[str, Any],
    approved_targets: set[tuple[str, str, str]] | None = None,
) -> PolicyDecision:
    setting = state.connector_settings.get(connector_id)
    if not setting or not setting.enabled:
        raise PermissionError(f"Connector '{connector_id}' is not enabled for this project.")
    if setting.allowed_capabilities and capability not in setting.allowed_capabilities:
        raise PermissionError(f"Capability '{capability}' is not enabled for connector '{connector_id}'.")

    definition = get_capability(connector_id, capability)
    normalized = normalize_target(connector_id, capability, target)
    risk = definition.risk
    is_first_contact = risk in {"write", "destructive"} and (connector_id, capability, normalized) not in (approved_targets or set())
    requires_approval = risk in {"write", "destructive", "first_contact"} or is_first_contact
    if risk in {"write", "destructive"}:
        reason = f"{risk.title()} capability requires human approval."
    elif is_first_contact:
        reason = "First contact with this connector capability and normalized target requires approval."
    else:
        reason = "Read/draft capability may run automatically after connector scope validation."
    return PolicyDecision(
        risk="first_contact" if is_first_contact and risk in {"read", "draft"} else risk,
        requires_approval=requires_approval,
        normalized_target=normalized,
        reason=reason,
        payload_hash=payload_hash(payload),
    )


def create_action_request(
    state: ProjectState,
    connector_id: str,
    capability: str,
    target: str,
    payload: dict[str, Any],
    attempt_id: str | None = None,
    approved_targets: set[tuple[str, str, str]] | None = None,
    pending_action_count: int = 0,
) -> ActionRequest:
    decision = classify_action(state, connector_id, capability, target, payload, approved_targets)
    if pending_action_count >= state.budget.max_pending_actions:
        status = "blocked"
        reason = "Pending approval backlog limit reached; dependent work is throttled."
    else:
        status = "queued" if decision.requires_approval else "approved"
        reason = decision.reason
    return ActionRequest(
        project_id=state.project_id,
        connector_id=connector_id,
        capability=capability,
        normalized_target=decision.normalized_target,
        payload=payload,
        risk=decision.risk,
        status=status,
        reason=reason,
        attempt_id=attempt_id,
        payload_hash=decision.payload_hash,
    )
