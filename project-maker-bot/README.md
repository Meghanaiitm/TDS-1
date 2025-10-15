## Project-Maker Bot

An autonomous agent that receives JSON tasks, generates a web project, deploys to GitHub Pages, and reports back.

### Setup
1. Create a GitHub Personal Access Token with `repo` and `pages` scopes.
2. Export the token:
   ```bash
   export GITHUB_TOKEN=YOUR_TOKEN_VALUE
   ```
3. Update `config.json`:
   - `student_email`
   - `shared_secret`
   - `github_username`
4. Install Python dependencies:
   ```bash
   pip3 install -r requirements.txt
   ```
5. Run the API server:
   ```bash
   python3 -m api.server
   ```

### Endpoint
`POST /api-endpoint`

Example payload:
```json
{
  "email": "student@domain.com",
  "secret": "change-me",
  "task": "Build a webpage that shows a random quote each time a button is clicked",
  "round": 1,
  "nonce": "abc123",
  "evaluation_url": "https://eval.server/report"
}
```

Expected response: `{"status":"Task accepted"}` (202)

### Notes
- Projects are created under `workspace/`.
- Repos are created under your GitHub account. Pages will serve from the default branch.
- For subsequent rounds, you can enhance `builder/generator.update_project` to mutate the same repo instead of creating a new one.
