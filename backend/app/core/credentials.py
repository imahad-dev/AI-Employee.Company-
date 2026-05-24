from __future__ import annotations

from dataclasses import dataclass


@dataclass
class ProjectCredentials:
    api_key: str | None = None
    base_url: str | None = None


_credentials: dict[str, ProjectCredentials] = {}
_github_tokens: dict[str, str] = {}


def set_project_credentials(project_id: str, api_key: str | None = None, base_url: str | None = None) -> None:
    if not api_key and not base_url:
        return
    _credentials[project_id] = ProjectCredentials(api_key=api_key or None, base_url=base_url or None)


def get_project_credentials(project_id: str) -> ProjectCredentials:
    return _credentials.get(project_id, ProjectCredentials())


def has_project_api_key(project_id: str) -> bool:
    return bool(_credentials.get(project_id, ProjectCredentials()).api_key)


def set_github_token(project_id: str, token: str | None = None) -> None:
    if token:
        _github_tokens[project_id] = token
    else:
        _github_tokens.pop(project_id, None)


def get_github_token(project_id: str) -> str | None:
    return _github_tokens.get(project_id)


def has_github_token(project_id: str) -> bool:
    return bool(_github_tokens.get(project_id))
