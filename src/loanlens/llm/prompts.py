"""Load and discover versioned LLM prompts."""

import re
from pathlib import Path

PROMPT_DIR = Path(__file__).resolve().parents[3] / "prompts"


def list_versions(task: str) -> list[Path]:
    """Find prompt versions for a task, sorted numerically."""
    pattern = re.compile(rf"^{re.escape(task)}_v(\d+)\.md$")
    matches = []

    for path in PROMPT_DIR.glob(f"{task}_v*.md"):
        match = pattern.match(path.name)
        if match:
            matches.append((int(match.group(1)), path))

    return [path for _, path in sorted(matches)]


def load_prompt(task: str, version: int) -> str:
    """Load a specific version of a prompt."""
    path = PROMPT_DIR / f"{task}_v{version}.md"
    return path.read_text(encoding="utf-8")
