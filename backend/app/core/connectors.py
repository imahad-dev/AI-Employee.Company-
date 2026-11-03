from __future__ import annotations

from dataclasses import dataclass
from typing import Literal


ConnectorKind = Literal["mcp", "native", "mock"]


@dataclass(frozen=True)
class ConnectorCapability:
    id: str
    risk: str
    description: str
    requires_secret: bool = False


@dataclass(frozen=True)
class ConnectorDefinition:
    id: str
    name: str
    kind: ConnectorKind
    description: str
    enabled_by_default: bool
    capabilities: tuple[ConnectorCapability, ...]


CONNECTORS: dict[str, ConnectorDefinition] = {
    "governance": ConnectorDefinition(
        id="governance",
        name="Runtime Governance",
        kind="native",
        description="Internal policy actions for budget increases and controlled pipeline continuation.",
        enabled_by_default=True,
        capabilities=(
            ConnectorCapability("budget.increase", "write", "Request approval to raise a project budget ceiling."),
        ),
    ),
    "web_research": ConnectorDefinition(
        id="web_research",
        name="Web Research",
        kind="mcp",
        description="Read-only web search and page retrieval with source capture.",
        enabled_by_default=False,
        capabilities=(
            ConnectorCapability("search", "read", "Search public web sources."),
            ConnectorCapability("fetch", "read", "Fetch and extract a public web page."),
        ),
    ),
    "github_read": ConnectorDefinition(
        id="github_read",
        name="GitHub Read",
        kind="native",
        description="Repository inspection, pull-request analysis, and workflow status reading.",
        enabled_by_default=False,
        capabilities=(
            ConnectorCapability("repository.read", "read", "Read repository metadata and files.", True),
            ConnectorCapability("pull_request.read", "read", "Read pull requests and checks.", True),
        ),
    ),
    "github_write": ConnectorDefinition(
        id="github_write",
        name="GitHub Delivery",
        kind="native",
        description="Approval-gated repository writes, commits, and pull-request delivery.",
        enabled_by_default=False,
        capabilities=(
            ConnectorCapability("contents.write", "write", "Create or update a repository file.", True),
            ConnectorCapability("pull_request.create", "write", "Create a pull request.", True),
            ConnectorCapability("repository.delete", "destructive", "Delete a repository resource.", True),
        ),
    ),
    "document_store": ConnectorDefinition(
        id="document_store",
        name="Document Store",
        kind="mcp",
        description="User-owned document retrieval and approval-gated document updates.",
        enabled_by_default=False,
        capabilities=(
            ConnectorCapability("document.read", "read", "Read an explicitly connected document."),
            ConnectorCapability("document.draft", "draft", "Generate a document draft without saving."),
            ConnectorCapability("document.write", "write", "Save a document update."),
        ),
    ),
    "email_triage": ConnectorDefinition(
        id="email_triage",
        name="Email Triage",
        kind="mcp",
        description="Read-only inbox triage and summarization. Sending is intentionally absent in V1.",
        enabled_by_default=False,
        capabilities=(ConnectorCapability("inbox.read", "read", "Read and classify connected inbox messages.", True),),
    ),
    "staging_deploy": ConnectorDefinition(
        id="staging_deploy",
        name="Staging Deployment",
        kind="mcp",
        description="Approval-gated staging deployment plans and executions. Production is unavailable in V1.",
        enabled_by_default=False,
        capabilities=(
            ConnectorCapability("deployment.plan", "draft", "Prepare a staging deployment plan."),
            ConnectorCapability("deployment.execute", "write", "Deploy to an approved staging target.", True),
        ),
    ),
}


def get_connector(connector_id: str) -> ConnectorDefinition:
    try:
        return CONNECTORS[connector_id]
    except KeyError as exc:
        raise ValueError(f"Unknown connector: {connector_id}") from exc


def get_capability(connector_id: str, capability_id: str) -> ConnectorCapability:
    connector = get_connector(connector_id)
    for capability in connector.capabilities:
        if capability.id == capability_id:
            return capability
    raise ValueError(f"Unknown capability '{capability_id}' for connector '{connector_id}'")


def serializable_connectors() -> list[dict[str, object]]:
    return [
        {
            "id": connector.id,
            "name": connector.name,
            "kind": connector.kind,
            "description": connector.description,
            "enabled_by_default": connector.enabled_by_default,
            "capabilities": [
                {"id": capability.id, "risk": capability.risk, "description": capability.description, "requires_secret": capability.requires_secret}
                for capability in connector.capabilities
            ],
        }
        for connector in CONNECTORS.values()
    ]
