from __future__ import annotations

from pathlib import Path
from typing import Any


def project_workspace(workspace_root: Path, project_id: str) -> Path:
    return (workspace_root / project_id).resolve()


def ensure_project_workspace(workspace_root: Path, project_id: str) -> Path:
    root = project_workspace(workspace_root, project_id)
    root.mkdir(parents=True, exist_ok=True)
    return root


def assert_inside(root: Path, target: Path) -> None:
    resolved_root = root.resolve()
    resolved_target = target.resolve()
    if resolved_target != resolved_root and resolved_root not in resolved_target.parents:
        raise ValueError("path escapes project workspace")


def list_file_tree(root: Path, max_files: int = 200) -> list[dict[str, Any]]:
    if not root.exists():
        return []
    files: list[dict[str, Any]] = []
    for path in sorted(root.rglob("*")):
        if len(files) >= max_files:
            break
        if path.is_dir():
            continue
        rel = path.relative_to(root).as_posix()
        files.append({"path": rel, "size": path.stat().st_size, "modified": path.stat().st_mtime})
    return files
