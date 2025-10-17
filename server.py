import os
import subprocess
import requests
from flask import Flask, request, jsonify
import re
import json
import time
import base64
from typing import Optional, Dict

app = Flask(__name__)

@app.route("/")
def root_endpoint():
    """Returns a status message for the root URL, fixing the 404 error."""
    return jsonify({
        "status": "Service Operational",
        "message": "This is the API base. The primary endpoint is /api-endpoint.",
        "version": "Final"
    })

AI_PIPE_TOKEN = os.environ.get("AI_PIPE_TOKEN", "placeholder_ai_token")
GITHUB_USERNAME = os.environ.get("GITHUB_USERNAME", "placeholder_user")
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN", "placeholder_github_token")
GITHUB_EMAIL = os.environ.get("GITHUB_EMAIL", "placeholder@email.com")
AI_PIPE_URL = "https://aipipe.org/openai/v1/chat/completions"
LLM_FILES = ["index.html", "style.css", "script.js", "README.md"]


def post_to_evaluation_api(url: str, payload: Dict):
    max_retries = 5
    delay = 1
    
    for attempt in range(max_retries):
        try:
            response = requests.post(
                url, 
                headers={'Content-Type': 'application/json'}, 
                data=json.dumps(payload),
                timeout=10
            )
            response.raise_for_status()
            print(f"Evaluation API ping successful on attempt {attempt + 1}.")
            return True, response.status_code
        except requests.exceptions.RequestException as e:
            print(f"Attempt {attempt + 1} failed: {e}. Retrying in {delay}s...")
            if attempt < max_retries - 1:
                time.sleep(delay)
                delay *= 2
            else:
                return False, str(e)
    return False, "Max retries exceeded"


def update_file_via_github_api(repo: str, path: str, content: str, commit_msg: str, sha: Optional[str] = None):
    url = f"https://api.github.com/repos/{GITHUB_USERNAME}/{repo}/contents/{path}"
    encoded_content = base64.b64encode(content.encode('utf-8')).decode('utf-8')
    headers = {"Authorization": f"token {GITHUB_TOKEN}"}
    
    payload = {
        "message": commit_msg,
        "content": encoded_content,
        "branch": "main"
    }
    
    if sha:
        payload["sha"] = sha
    
    response = requests.put(url, headers=headers, data=json.dumps(payload))
    response.raise_for_status()
    
    return response.json()


def get_file_sha(repo: str, path: str):
    url = f"https://api.github.com/repos/{GITHUB_USERNAME}/{repo}/contents/{path}?ref=main"
    headers = {"Authorization": f"token {GITHUB_TOKEN}"}
    
    response = requests.get(url, headers=headers)
    response.raise_for_status()
    
    return response.json().get('sha')


@app.route("/api-endpoint", methods=["POST"])
def handle_request():
    data = request.get_json()
    secret = data.get("secret")
    task = data.get("task")
    round_number = data.get("round")
    
    email = data.get("email")
    nonce = data.get("nonce")
    evaluation_url = data.get("evaluation_url")
    brief = data.get("brief")

    if secret != "namaste":
        return jsonify({"error": "Invalid secret"}), 403
    
    if not all([email, nonce, evaluation_url]):
        return jsonify({"error": "Missing required fields (email, nonce, or evaluation_url) in request"}), 400

    unique_repo_name = f"{task}-round1" if round_number == 2 else f"{task}-round{round_number}"
    repo_url = f"https://github.com/{GITHUB_USERNAME}/{unique_repo_name}"
    remote_url_standard = f"https://github.com/{GITHUB_USERNAME}/{unique_repo_name}.git"

    folder_name = f"projects/{task}_{round_number}"
    os.makedirs(folder_name, exist_ok=True)

    for f in LLM_FILES + ["LICENSE"]:
        path = os.path.join(folder_name, f)
        if os.path.exists(path):
            try:
                os.remove(path)
            except OSError as e:
                print(f"Error removing file {path}: {e}")
                pass
            
    commit_msg = f"Revision commit for {task} - Round {round_number} (AI Generated)"
    
    prompt = f"""
Strictly use the format '--- filename ---' for file headers. Do not use bold markdown or any other formatting.

Task Brief: {brief}
Generate updated files for project "{task}", round {round_number}:

--- index.html ---
Provide only HTML content for the main page.

--- style.css ---
Provide only CSS code for styling the page.

--- script.js ---
Provide only JavaScript code for functionality.

--- README.md ---
Provide an updated, professional README explaining the project and including the new changes for round {round_number}.

Do not include any extra text, explanations, or emojis.
"""

    try:
        response = requests.post(
            AI_PIPE_URL,
            headers={"Authorization": f"Bearer {AI_PIPE_TOKEN}", "Content-Type": "application/json"},
            json={
                "model": "gpt-4o-mini",
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.7
            },
            timeout=60
        )
        response.raise_for_status() 
    except requests.exceptions.RequestException as e:
        return jsonify({"error": f"AI Pipe API request failed: {e}"}), 503

    res_json = response.json()

    try:
        content = res_json["choices"][0]["message"]["content"]
    except (KeyError, IndexError):
        return jsonify({"error": "AI Pipe response invalid or missing content", "response": res_json}), 500

    file_patterns = re.findall(r"--- (\w+\.\w+) ---\n([\s\S]*?)(?=(--- \w+\.\w+ ---|$))", content)

    if not file_patterns or len(file_patterns) < len(LLM_FILES):
        return jsonify({"error": "Could not parse AI response or files are missing", "response": content}), 500

    file_contents = {}
    for fname, fcontent, _ in file_patterns:
        cleaned_content = re.sub(r"^```[a-z]*\n", "", fcontent.strip())
        cleaned_content = re.sub(r"\n```$", "", cleaned_content)
        file_contents[fname] = cleaned_content
        
        with open(os.path.join(folder_name, fname), "w", encoding="utf-8") as f:
            f.write(cleaned_content)

    mit_text = f"""MIT License

Copyright (c) 2025 {GITHUB_USERNAME}

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
"""
    with open(os.path.join(folder_name, "LICENSE"), "w", encoding="utf-8") as f:
        f.write(mit_text)
    file_contents["LICENSE"] = mit_text

    commit_sha = "API_GENERATED"
    headers = {"Authorization": f"token {GITHUB_TOKEN}"}

    if round_number == 1:
        payload = {"name": unique_repo_name, "private": False, "auto_init": False}
        repo_creation_response = requests.post("https://api.github.com/user/repos", headers=headers, data=json.dumps(payload))

        if repo_creation_response.status_code not in [201, 422]:
            return jsonify({"error": "Failed to create GitHub repository", "status": repo_creation_response.status_code, "detail": repo_creation_response.json()}), 500

        try:
            subprocess.run(["git", "init"], cwd=folder_name, check=True)
            subprocess.run(["git", "config", "user.name", GITHUB_USERNAME], cwd=folder_name, check=True)
            subprocess.run(["git", "config", "user.email", GITHUB_EMAIL], cwd=folder_name, check=True)
            subprocess.run(["git", "add", "."], cwd=folder_name, check=True)
            
            commit_result = subprocess.run(["git", "commit", "-m", commit_msg], cwd=folder_name, capture_output=True, text=True)
            
            if commit_result.returncode != 0 and (commit_result.stderr is None or "nothing to commit" not in commit_result.stderr):
                 raise subprocess.CalledProcessError(commit_result.returncode, commit_result.args, output=commit_result.stdout, stderr=commit_result.stderr)

            subprocess.run(["git", "branch", "-M", "main"], cwd=folder_name, check=True)
            
            remote_url_with_token = f"https://{GITHUB_USERNAME}:{GITHUB_TOKEN}@github.com/{GITHUB_USERNAME}/{unique_repo_name}.git"

            subprocess.run(["git", "remote", "add", "origin", remote_url_with_token], cwd=folder_name, check=True)
            
            subprocess.run(["git", "push", "-u", "origin", "main"], cwd=folder_name, check=True)
            
            sha_result = subprocess.run(
                ["git", "rev-parse", "HEAD"], 
                cwd=folder_name, 
                capture_output=True, 
                text=True,
                check=True
            )
            commit_sha = sha_result.stdout.strip()
            
        except subprocess.CalledProcessError as e:
            return jsonify({"error": f"Git/Push failed in Round 1: {e.cmd} returned {e.returncode}. Stderr: {e.stderr}"}), 500

        pages_config_response = requests.post(
            f"https://api.github.com/repos/{GITHUB_USERNAME}/{unique_repo_name}/pages",
            headers=headers,
            json={"source": {"branch": "main", "path": "/"}} 
        )
        if pages_config_response.status_code not in [201, 409]:
             print(f"Warning: Pages setup returned {pages_config_response.status_code}.")

    
    elif round_number == 2:
        last_commit_sha = None
        
        files_to_update = LLM_FILES + ["LICENSE"]

        for file_path in files_to_update:
            try:
                current_file_sha = get_file_sha(unique_repo_name, file_path)
                
                update_response = update_file_via_github_api(
                    repo=unique_repo_name,
                    path=file_path,
                    content=file_contents.get(file_path, "Error: File content missing."),
                    commit_msg=commit_msg,
                    sha=current_file_sha
                )
                
                last_commit_sha = update_response['commit']['sha']

            except requests.exceptions.HTTPError as e:
                if e.response.status_code == 409:
                    print(f"Warning: File {file_path} content is identical. Skipping push for this file.")
                    if not last_commit_sha: 
                        continue
                
                return jsonify({"error": f"GitHub API update failed for {file_path} in R2. Status: {e.response.status_code}", "detail": e.response.json()}), 500

        if last_commit_sha:
            commit_sha = last_commit_sha
        else:
             try:
                 commits_url = f"https://api.github.com/repos/{GITHUB_USERNAME}/{unique_repo_name}/commits/main"
                 response = requests.get(commits_url, headers=headers)
                 response.raise_for_status()
                 commit_sha = response.json()['sha']
             except requests.exceptions.RequestException as e:
                 return jsonify({"error": f"Failed to retrieve HEAD SHA after no updates in R2: {e}"}), 500


    pages_url = f"https://{GITHUB_USERNAME}.github.io/{unique_repo_name}/"
    
    evaluation_payload = {
        "email": email,
        "task": task,
        "round": round_number,
        "nonce": nonce,
        "repo_url": repo_url,
        "commit_sha": commit_sha,
        "pages_url": pages_url,
    }
    
    success, result = post_to_evaluation_api(evaluation_url, evaluation_payload)
    
    evaluation_message = "Evaluation API notified successfully!" if success else f"FAILED to notify evaluation API: {result}"

    return jsonify({
        "message": f"Project deployed successfully. {evaluation_message}",
        "repo_url": repo_url,
        "pages_url": pages_url,
        "commit_sha": commit_sha,
        "evaluation_status": "Successful" if success else "Failed to Notify"
    })


if __name__ == "__main__":
    app.run(debug=True)


