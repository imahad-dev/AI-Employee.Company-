from __future__ import annotations

import json
from difflib import unified_diff
from pathlib import Path
from typing import Any


def stringify_content(content: Any) -> str:
    if isinstance(content, str):
        return content
    return json.dumps(content, indent=2, sort_keys=True, default=str)


def build_unified_diff(path: str, new_content: Any, workspace_root: Path) -> str:
    target = (workspace_root / path).resolve()
    old_text = target.read_text(encoding="utf-8") if target.exists() else ""
    new_text = stringify_content(new_content)
    return "".join(
        unified_diff(
            old_text.splitlines(keepends=True),
            new_text.splitlines(keepends=True),
            fromfile=f"current/{path}",
            tofile=f"proposed/{path}",
        )
    )


def attach_diff(payload: dict[str, Any], workspace_root: Path) -> dict[str, Any]:
    path = payload.get("path")
    if not path:
        return payload
    enriched = dict(payload)
    enriched["diff"] = build_unified_diff(str(path), payload.get("content", ""), workspace_root)
    return enriched
