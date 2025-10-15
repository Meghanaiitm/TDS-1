from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Optional

STATE_FILENAME = "state.json"


def _state_path(project_root: str | Path) -> Path:
    root = Path(project_root)
    return root / STATE_FILENAME


def load_state(project_root: str | Path) -> Dict[str, Any]:
    path = _state_path(project_root)
    if not path.exists():
        return {"projects": {}, "latest_by_email": {}}
    try:
        with path.open("r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {"projects": {}, "latest_by_email": {}}


def save_state(project_root: str | Path, state: Dict[str, Any]) -> None:
    path = _state_path(project_root)
    path.write_text(json.dumps(state, indent=2, ensure_ascii=False), encoding="utf-8")


def get_project_record(project_root: str | Path, slug: str) -> Optional[Dict[str, Any]]:
    state = load_state(project_root)
    return state.get("projects", {}).get(slug)


def upsert_project_record(project_root: str | Path, slug: str, repo_name: str, directory: str) -> None:
    state = load_state(project_root)
    projects = state.setdefault("projects", {})
    projects[slug] = {"repo_name": repo_name, "directory": directory}
    save_state(project_root, state)


def get_latest_for_email(project_root: str | Path, email: str) -> Optional[Dict[str, Any]]:
    state = load_state(project_root)
    return state.get("latest_by_email", {}).get(email)


def set_latest_for_email(project_root: str | Path, email: str, slug: str, repo_name: str, directory: str) -> None:
    state = load_state(project_root)
    latest = state.setdefault("latest_by_email", {})
    latest[email] = {"slug": slug, "repo_name": repo_name, "directory": directory}
    save_state(project_root, state)
