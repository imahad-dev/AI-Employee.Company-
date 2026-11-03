from __future__ import annotations

import base64
import re
from pathlib import Path
from typing import Any

import httpx

from app.core.models import ProjectState
from app.core.workspace import list_file_tree


class GitHubWorkflowError(ValueError):
    pass


def parse_github_repo(repository_url: str) -> tuple[str, str]:
    value = repository_url.strip()
    patterns = [
        r"^https://github\.com/([^/\s]+)/([^/\s]+?)(?:\.git)?/?$",
        r"^git@github\.com:([^/\s]+)/([^/\s]+?)(?:\.git)?$",
        r"^([^/\s]+)/([^/\s]+?)(?:\.git)?$",
    ]
    for pattern in patterns:
        match = re.match(pattern, value)
        if match:
            owner, repo = match.groups()
            return owner, repo.removesuffix(".git")
    raise GitHubWorkflowError("Enter a GitHub repository as owner/repo, https://github.com/owner/repo, or git@github.com:owner/repo.git.")


def safe_branch_name(project_id: str, branch: str | None = None) -> str:
    candidate = (branch or f"ai-company/{project_id}").strip()
    candidate = re.sub(r"[^A-Za-z0-9._/-]+", "-", candidate).strip("/.-")
    if not candidate:
        raise GitHubWorkflowError("Working branch cannot be empty.")
    return candidate


class GitHubClient:
    def __init__(self, token: str, timeout_seconds: float = 30.0) -> None:
        self.token = token
        self.timeout_seconds = timeout_seconds

    async def _request(self, method: str, path: str, **kwargs: Any) -> dict[str, Any]:
        headers = {
            "Authorization": f"Bearer {self.token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        }
        async with httpx.AsyncClient(base_url="https://api.github.com", timeout=self.timeout_seconds) as client:
            response = await client.request(method, path, headers=headers, **kwargs)
        if response.status_code >= 400:
            detail = response.text
            try:
                detail = response.json().get("message", detail)
            except ValueError:
                pass
            raise GitHubWorkflowError(f"GitHub {method} {path} failed: {detail}")
        if not response.content:
            return {}
        return response.json()

    async def get_branch_sha(self, owner: str, repo: str, branch: str) -> str:
        data = await self._request("GET", f"/repos/{owner}/{repo}/git/ref/heads/{branch}")
        sha = data.get("object", {}).get("sha")
        if not sha:
            raise GitHubWorkflowError(f"Could not find base branch '{branch}'.")
        return str(sha)

    async def create_branch(self, owner: str, repo: str, branch: str, sha: str) -> None:
        try:
            await self._request("POST", f"/repos/{owner}/{repo}/git/refs", json={"ref": f"refs/heads/{branch}", "sha": sha})
        except GitHubWorkflowError as exc:
            if "Reference already exists" not in str(exc):
                raise

    async def get_file_sha(self, owner: str, repo: str, path: str, branch: str) -> str | None:
        try:
            data = await self._request("GET", f"/repos/{owner}/{repo}/contents/{path}", params={"ref": branch})
        except GitHubWorkflowError as exc:
            if "Not Found" in str(exc):
                return None
            raise
        sha = data.get("sha")
        return str(sha) if sha else None

    async def put_file(self, owner: str, repo: str, path: str, content: str, branch: str, message: str, sha: str | None = None) -> None:
        payload: dict[str, Any] = {
            "message": message,
            "content": base64.b64encode(content.encode("utf-8")).decode("ascii"),
            "branch": branch,
        }
        if sha:
            payload["sha"] = sha
        await self._request("PUT", f"/repos/{owner}/{repo}/contents/{path}", json=payload)

    async def create_tree(self, owner: str, repo: str, tree_items: list[dict[str, Any]], base_tree_sha: str) -> dict[str, Any]:
        return await self._request(
            "POST",
            f"/repos/{owner}/{repo}/git/trees",
            json={"base_tree": base_tree_sha, "tree": tree_items},
        )

    async def create_commit(self, owner: str, repo: str, message: str, tree_sha: str, parent_sha: str) -> dict[str, Any]:
        return await self._request(
            "POST",
            f"/repos/{owner}/{repo}/git/commits",
            json={"message": message, "tree": tree_sha, "parents": [parent_sha]},
        )

    async def update_branch_ref(self, owner: str, repo: str, branch: str, sha: str) -> None:
        await self._request("PATCH", f"/repos/{owner}/{repo}/git/refs/heads/{branch}", json={"sha": sha, "force": False})

    async def create_pull_request(self, owner: str, repo: str, title: str, body: str, head: str, base: str) -> dict[str, Any]:
        return await self._request("POST", f"/repos/{owner}/{repo}/pulls", json={"title": title, "body": body, "head": head, "base": base})

    async def create_repository(self, name: str, description: str | None = None, private: bool = True) -> dict[str, Any]:
        return await self._request("POST", "/user/repos", json={"name": name, "description": description or "", "private": private, "auto_init": True})

    async def get_pull_request(self, owner: str, repo: str, number: int) -> dict[str, Any]:
        return await self._request("GET", f"/repos/{owner}/{repo}/pulls/{number}")

    async def list_pull_request_files(self, owner: str, repo: str, number: int) -> list[dict[str, Any]]:
        data = await self._request("GET", f"/repos/{owner}/{repo}/pulls/{number}/files", params={"per_page": 100})
        return data if isinstance(data, list) else []

    async def list_pull_request_reviews(self, owner: str, repo: str, number: int) -> list[dict[str, Any]]:
        data = await self._request("GET", f"/repos/{owner}/{repo}/pulls/{number}/reviews", params={"per_page": 100})
        return data if isinstance(data, list) else []

    async def list_check_runs(self, owner: str, repo: str, ref: str) -> list[dict[str, Any]]:
        data = await self._request("GET", f"/repos/{owner}/{repo}/commits/{ref}/check-runs", params={"per_page": 100})
        runs = data.get("check_runs", [])
        return runs if isinstance(runs, list) else []


def build_pull_request_summary(state: ProjectState, files: list[dict[str, Any]]) -> str:
    file_lines = "\n".join(f"- {file_info['path']}" for file_info in files[:50])
    if len(files) > 50:
        file_lines += f"\n- ...and {len(files) - 50} more files"
    approvals = [approval for approval in state.approvals if approval.status == "approved"]
    summary_parts = [
        "## AI Company Delivery Summary",
        f"- Project: `{state.project_id}`",
        f"- Type: `{state.project_type}`",
        f"- Current phase: `{state.current_phase}`",
        f"- Completed agents: {len(state.completed_agents)}/14",
        f"- Approved actions: {len(approvals)}",
        f"- Estimated cost: ${state.token_usage.estimated_cost_usd:.4f}",
        "",
        "## Files Included",
        file_lines or "- No files detected.",
        "",
        "## Review Notes",
        "- These files came from the approval-gated workspace.",
        "- Review generated code, dependencies, and deployment plans before merging.",
        "- Keep real deployment actions separate from this pull request in V1.",
    ]
    if state.errors:
        summary_parts.extend(["", "## Known Pipeline Errors", *[f"- {error}" for error in state.errors[-10:]]])
    return "\n".join(summary_parts)


def build_preflight_report(state: ProjectState, workspace_root: Path, has_token: bool) -> dict[str, Any]:
    files = list_file_tree(workspace_root, max_files=500)
    blocked_prefixes = (".git/", ".env", "node_modules/", "__pycache__/", ".next/")
    blocked_files = [file_info["path"] for file_info in files if str(file_info["path"]).startswith(blocked_prefixes)]
    large_files = [file_info["path"] for file_info in files if int(file_info["size"]) > 1_000_000]
    pending_approvals = [approval.title for approval in state.approvals if approval.status == "pending"]
    checks = [
        {"name": "GitHub provider selected", "passed": state.repository.provider == "github"},
        {"name": "Repository URL configured", "passed": bool(state.repository.repository_url)},
        {"name": "GitHub token saved", "passed": has_token},
        {"name": "Approved workspace files exist", "passed": len(files) > 0},
        {"name": "No pending approvals", "passed": len(pending_approvals) == 0},
        {"name": "No blocked paths", "passed": len(blocked_files) == 0},
        {"name": "No files over 1 MB", "passed": len(large_files) == 0},
    ]
    passed = all(check["passed"] for check in checks)
    return {
        "ready": passed,
        "checks": checks,
        "files": files,
        "blocked_files": blocked_files,
        "large_files": large_files,
        "pending_approvals": pending_approvals,
        "summary": build_pull_request_summary(state, files),
        "message": "Preflight passed. This project is ready for PR creation." if passed else "Preflight needs attention before this is merge-ready.",
    }


def summarize_pull_request_status(pr: dict[str, Any], files: list[dict[str, Any]], reviews: list[dict[str, Any]], check_runs: list[dict[str, Any]]) -> dict[str, Any]:
    failed_checks = [run for run in check_runs if run.get("conclusion") not in (None, "success", "skipped", "neutral")]
    pending_checks = [run for run in check_runs if run.get("status") != "completed"]
    approved_reviews = [review for review in reviews if review.get("state") == "APPROVED"]
    change_requests = [review for review in reviews if review.get("state") == "CHANGES_REQUESTED"]
    merge_ready = (
        pr.get("state") == "open"
        and pr.get("mergeable") is not False
        and not pr.get("draft")
        and len(failed_checks) == 0
        and len(pending_checks) == 0
        and len(change_requests) == 0
    )
    return {
        "url": pr.get("html_url"),
        "number": pr.get("number"),
        "state": pr.get("state"),
        "draft": bool(pr.get("draft")),
        "title": pr.get("title"),
        "base_branch": pr.get("base", {}).get("ref"),
        "head_branch": pr.get("head", {}).get("ref"),
        "head_sha": pr.get("head", {}).get("sha"),
        "mergeable": pr.get("mergeable"),
        "merge_ready": merge_ready,
        "file_count": len(files),
        "changed_files": [file_info.get("filename") for file_info in files],
        "checks": [{"name": run.get("name"), "status": run.get("status"), "conclusion": run.get("conclusion")} for run in check_runs],
        "review_summary": {
            "approved": len(approved_reviews),
            "changes_requested": len(change_requests),
            "total_reviews": len(reviews),
        },
        "message": "Ready for human merge review." if merge_ready else "Not merge-ready yet. Review checks, draft state, mergeability, or requested changes.",
    }


async def create_project_pull_request(
    state: ProjectState,
    workspace_root: Path,
    token: str,
    title: str | None = None,
    body: str | None = None,
    branch: str | None = None,
    timeout_seconds: float = 30.0,
) -> dict[str, Any]:
    if state.repository.provider != "github":
        raise GitHubWorkflowError("Set repository provider to GitHub before creating a pull request.")
    if not state.repository.repository_url:
        raise GitHubWorkflowError("Add a GitHub repository URL before creating a pull request.")

    owner, repo = parse_github_repo(state.repository.repository_url)
    base_branch = state.repository.default_branch or "main"
    working_branch = safe_branch_name(state.project_id, branch or state.repository.working_branch)
    files = list_file_tree(workspace_root, max_files=500)
    if not files:
        raise GitHubWorkflowError("No approved workspace files are available for a pull request yet.")

    client = GitHubClient(token, timeout_seconds=timeout_seconds)
    base_sha = await client.get_branch_sha(owner, repo, base_branch)
    await client.create_branch(owner, repo, working_branch, base_sha)
    try:
        working_sha = await client.get_branch_sha(owner, repo, working_branch)
    except GitHubWorkflowError:
        working_sha = base_sha

    tree_items = []
    changed_paths: list[str] = []
    for file_info in files:
        rel_path = str(file_info["path"])
        file_path = workspace_root / rel_path
        content = file_path.read_text(encoding="utf-8")
        tree_items.append({"path": rel_path, "mode": "100644", "type": "blob", "content": content})
        changed_paths.append(rel_path)

    tree = await client.create_tree(owner, repo, tree_items, working_sha)
    commit = await client.create_commit(
        owner,
        repo,
        f"AI company delivery for {state.project_id}",
        str(tree["sha"]),
        working_sha,
    )
    await client.update_branch_ref(owner, repo, working_branch, str(commit["sha"]))

    pr_title = title or f"AI company output for {state.project_id}"
    pr_body = body or build_pull_request_summary(state, files)
    pr = await client.create_pull_request(owner, repo, pr_title, pr_body, working_branch, base_branch)
    return {
        "repository": f"{owner}/{repo}",
        "url": pr.get("html_url"),
        "number": pr.get("number"),
        "branch": working_branch,
        "base_branch": base_branch,
        "files_changed": changed_paths,
    }
