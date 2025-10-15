from __future__ import annotations

import json
import os
import threading
from datetime import datetime
from pathlib import Path
from typing import Any, Dict

from flask import Flask, jsonify, request

from utils.validators import load_config, validate_request, validate_secret
from builder.generator import generate_project, update_project
from utils.state import (
    get_latest_for_email,
    set_latest_for_email,
    upsert_project_record,
)
from deployer.github_utils import deploy_project, post_evaluation


app = Flask(__name__)

CONFIG_PATH = str(Path(__file__).resolve().parents[1] / 'config.json')
CONFIG = load_config(CONFIG_PATH)


def handle_task_async(payload: Dict[str, Any]) -> None:
    try:
        student_email = payload["email"]
        task_text = payload["task"]
        round_num = int(payload["round"])
        nonce = payload["nonce"]
        evaluation_url = payload["evaluation_url"]

        workspace_dir = CONFIG.get("workspace_dir")
        # Round handling: round 1 creates a new project; subsequent rounds update and reuse repo
        project_info = generate_project(workspace_dir, task_text, round_num)

        token_env = CONFIG.get("github_token_env", "GITHUB_TOKEN")
        token = os.environ.get(token_env)
        if not token:
            app.logger.error("Missing GitHub token in environment: %s", token_env)
            return

        username = CONFIG.get("github_username")
        default_branch = CONFIG.get("default_branch", "main")

        # Reuse the same repo across rounds based on email when round > 1
        latest = get_latest_for_email(workspace_dir, student_email)
        repo_name = latest["repo_name"] if (latest and round_num > 1) else f"task-{project_info.slug}"

        commit_message = f"Round {round_num}: {task_text[:72]}"
        deploy_res = deploy_project(
            token,
            username,
            str(project_info.directory),
            repo_name,
            default_branch=default_branch,
            commit_message=commit_message,
        )

        upsert_project_record(workspace_dir, project_info.slug, repo_name, str(project_info.directory))
        set_latest_for_email(workspace_dir, student_email, project_info.slug, repo_name, str(project_info.directory))

        report = {
            "email": student_email,
            "task": task_text,
            "round": round_num,
            "nonce": nonce,
            "repo_url": deploy_res.repo_url,
            "commit_sha": deploy_res.commit_sha,
            "pages_url": deploy_res.pages_url,
        }
        status, text = post_evaluation(evaluation_url, report)
        app.logger.info("Posted evaluation: status=%s", status)
    except Exception as e:
        app.logger.exception("Error handling task: %s", e)


@app.post("/api-endpoint")
def api_endpoint():
    # Basic JSON validation
    try:
        payload = request.get_json(force=True)
    except Exception:
        return jsonify({"error": "Invalid JSON"}), 400

    req, err = validate_request(payload or {})
    if err:
        return jsonify({"error": "Validation failed", "details": json.loads(err)}), 400

    expected_secret = CONFIG.get("shared_secret", "")
    if not validate_secret(req.secret, expected_secret):
        return jsonify({"error": "Unauthorized"}), 401

    # Accept and process async to keep endpoint responsive
    thread = threading.Thread(target=handle_task_async, args=(payload,))
    thread.daemon = True
    thread.start()

    return jsonify({"status": "Task accepted"}), 202


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000)
