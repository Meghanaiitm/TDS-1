from __future__ import annotations

import base64
import os
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Tuple

from github import Github
import requests


@dataclass
class DeploymentResult:
    repo_url: str
    commit_sha: str
    pages_url: Optional[str]


def run(cmd: list[str], cwd: Optional[str] = None) -> Tuple[int, str, str]:
    proc = subprocess.Popen(cmd, cwd=cwd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    out, err = proc.communicate()
    return proc.returncode, out.strip(), err.strip()


def ensure_git_repo(path: Path, default_branch: str = "main") -> None:
    if not (path / ".git").exists():
        code, out, err = run(["git", "init", "-b", default_branch], cwd=str(path))
        if code != 0:
            raise RuntimeError(f"git init failed: {err}")
    # Always set basic user name/email locally for commits (safe local scope)
    run(["git", "config", "user.email", "bot@example.com"], cwd=str(path))
    run(["git", "config", "user.name", "Project Maker Bot"], cwd=str(path))


def github_create_or_get_repo(token: str, repo_name: str, make_public: bool = True):
    gh = Github(token)
    user = gh.get_user()
    # Try to get, else create
    try:
        repo = user.get_repo(repo_name)
    except Exception:
        repo = user.create_repo(repo_name, private=not make_public, has_issues=True, auto_init=False, license_template="mit")
    return repo


def push_to_github_local(project_dir: Path, repo_full_name: str, token: str, default_branch: str = "main", commit_message: str = "Automated commit") -> str:
    ensure_git_repo(project_dir, default_branch=default_branch)

    # Add all files and commit
    code, out, err = run(["git", "add", "-A"], cwd=str(project_dir))
    if code != 0:
        raise RuntimeError(f"git add failed: {err}")
    code, out, err = run(["git", "commit", "-m", commit_message], cwd=str(project_dir))
    # If no changes, commit may fail; proceed

    # Configure remote with token in URL for auth
    remote_url = f"https://{token}:x-oauth-basic@github.com/{repo_full_name}.git"
    run(["git", "remote", "remove", "origin"], cwd=str(project_dir))
    code, out, err = run(["git", "remote", "add", "origin", remote_url], cwd=str(project_dir))
    if code != 0:
        raise RuntimeError(f"git remote add failed: {err}")

    code, out, err = run(["git", "push", "-u", "origin", default_branch], cwd=str(project_dir))
    if code != 0:
        raise RuntimeError(f"git push failed: {err}")

    # Get latest commit SHA
    code, out, err = run(["git", "rev-parse", "HEAD"], cwd=str(project_dir))
    if code != 0:
        raise RuntimeError(f"git rev-parse failed: {err}")
    return out.strip()


def enable_github_pages(repo, branch: str = "main") -> Optional[str]:
    try:
        # Configure Pages to serve from / (root) at branch
        repo.enable_pages(source="branch", branch=branch, path="/")
        pages = repo.get_pages()
        if pages and pages.html_url:
            return pages.html_url
    except Exception:
        pass
    return None


def deploy_project(token: str, username: str, project_dir: str, repo_name: str, default_branch: str = "main", commit_message: str = "Automated commit") -> DeploymentResult:
    repo = github_create_or_get_repo(token, repo_name, make_public=True)
    commit_sha = push_to_github_local(Path(project_dir), repo_full_name=repo.full_name, token=token, default_branch=default_branch, commit_message=commit_message)
    pages_url = enable_github_pages(repo, branch=default_branch)
    return DeploymentResult(repo.html_url, commit_sha, pages_url)


def post_evaluation(evaluation_url: str, payload: dict) -> Tuple[int, str]:
    resp = requests.post(evaluation_url, json=payload, timeout=30)
    return resp.status_code, resp.text
