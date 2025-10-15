from __future__ import annotations

import json
import os
import re
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Optional


@dataclass
class ProjectInfo:
    task: str
    round: int
    slug: str
    directory: Path


HTML_TEMPLATE = """<!DOCTYPE html>
<html lang=\"en\">
<head>
  <meta charset=\"UTF-8\" />
  <meta name=\"viewport\" content=\"width=device-width, initial-scale=1.0\" />
  <title>{title}</title>
  <link rel=\"stylesheet\" href=\"style.css\" />
</head>
<body>
  <main class=\"container\">
    <h1>{title}</h1>
    <div id=\"app\"></div>
    <button id=\"actionBtn\">Run</button>
  </main>
  <script src=\"script.js\"></script>
</body>
</html>
"""

CSS_TEMPLATE = """:root { --bg: #0b1020; --fg: #e7ecf4; --muted: #a7b0c3; --accent: #8cc8ff; }
* { box-sizing: border-box; }
html, body { height: 100%; }
body { margin: 0; font-family: system-ui, -apple-system, Segoe UI, Roboto, Ubuntu, Cantarell, "Noto Sans", "Helvetica Neue", Arial, "Apple Color Emoji", "Segoe UI Emoji"; background: var(--bg); color: var(--fg); }
.container { max-width: 720px; margin: 48px auto; padding: 0 16px; }
h1 { font-weight: 700; letter-spacing: 0.2px; }
#app { margin: 16px 0 24px; padding: 16px; background: #121833; border: 1px solid #1b2347; border-radius: 8px; min-height: 64px; }
button { background: var(--accent); color: #0c1b2a; border: none; padding: 10px 16px; border-radius: 8px; cursor: pointer; font-weight: 600; }
button:hover { filter: brightness(0.95); }
"""

JS_TEMPLATE_RANDOM_QUOTE = """const quotes = [
  "The only way to do great work is to love what you do. — Steve Jobs",
  "Simplicity is the soul of efficiency. — Austin Freeman",
  "Code is like humor. When you have to explain it, it’s bad. — Cory House",
  "Programs must be written for people to read. — Harold Abelson",
  "Premature optimization is the root of all evil. — Donald Knuth"
];

function randomQuote() {
  const i = Math.floor(Math.random() * quotes.length);
  return quotes[i];
}

document.getElementById('actionBtn').addEventListener('click', () => {
  document.getElementById('app').textContent = randomQuote();
});

window.addEventListener('DOMContentLoaded', () => {
  document.getElementById('app').textContent = 'Click the button to see a random quote!';
});
"""

README_TEMPLATE = """# {title}

Task: {task}

This project was generated automatically by an autonomous Project-Maker Bot.

## How to run locally
Open `index.html` in your browser, or serve the folder.
"""

MIT_LICENSE = """MIT License

Copyright (c) {year} {holder}

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
"""


def slugify(text: str) -> str:
    text = text.lower()
    text = re.sub(r"[^a-z0-9]+", "-", text)
    text = re.sub(r"-+", "-", text)
    return text.strip("-")


def infer_initial_js(task: str) -> str:
    if "quote" in task.lower():
        return JS_TEMPLATE_RANDOM_QUOTE
    # Default simple handler updates app content
    return (
        "document.getElementById('actionBtn').addEventListener('click', () => {\n"
        "  document.getElementById('app').textContent = 'Action executed!';\n"
        "});\n"
        "window.addEventListener('DOMContentLoaded', () => {\n"
        "  document.getElementById('app').textContent = 'Ready.';\n"
        "});\n"
    )


def generate_project(base_dir: str, task: str, round_num: int, project_name_hint: Optional[str] = None) -> ProjectInfo:
    base = Path(base_dir)
    base.mkdir(parents=True, exist_ok=True)

    title = project_name_hint or task[:60]
    slug = slugify(project_name_hint or task.split(" ")[0:4] and " ".join(task.split(" ")[:5]))
    project_dir = base / f"task_{round_num}_{slug}"

    if project_dir.exists():
        shutil.rmtree(project_dir)
    project_dir.mkdir(parents=True, exist_ok=True)

    (project_dir / "index.html").write_text(HTML_TEMPLATE.format(title=title), encoding="utf-8")
    (project_dir / "style.css").write_text(CSS_TEMPLATE, encoding="utf-8")
    (project_dir / "script.js").write_text(infer_initial_js(task), encoding="utf-8")
    (project_dir / "README.md").write_text(README_TEMPLATE.format(title=title, task=task), encoding="utf-8")

    from datetime import datetime
    (project_dir / "LICENSE").write_text(MIT_LICENSE.format(year=datetime.utcnow().year, holder="Auto Project-Maker Bot"), encoding="utf-8")

    return ProjectInfo(task=task, round=round_num, slug=slug, directory=project_dir)


def update_project(project_dir: str, task_update: str) -> None:
    # For simplicity, append task update to README and adjust index title
    project_path = Path(project_dir)
    readme = project_path / "README.md"
    if readme.exists():
        with readme.open("a", encoding="utf-8") as f:
            f.write("\n\n## Update\n" + task_update + "\n")

    index_html = project_path / "index.html"
    if index_html.exists():
        content = index_html.read_text(encoding="utf-8")
        content = content.replace("<h1>", f"<h1>Updated - ")
        index_html.write_text(content, encoding="utf-8")
