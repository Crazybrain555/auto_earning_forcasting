"""Method-evolution view: the skills git repo is the method history."""
from __future__ import annotations

import re
import subprocess
from pathlib import Path

from .config import CONFIG

SKILLS_REPO = Path(CONFIG["skills_repo"])


def git(*args: str) -> str:
    result = subprocess.run(
        ["git", "-C", str(SKILLS_REPO), *args],
        capture_output=True, text=True, timeout=15,
    )
    return result.stdout.strip() if result.returncode == 0 else ""


def timeline(limit: int = 50) -> dict:
    raw = git("log", f"-n{limit}", "--pretty=format:%H%x1f%h%x1f%aI%x1f%s%x1f%b%x1e")
    commits = []
    for chunk in raw.split("\x1e"):
        parts = chunk.strip("\n").split("\x1f")
        if len(parts) >= 4:
            commits.append({
                "hash": parts[0].strip(),
                "short": parts[1],
                "date": parts[2],
                "subject": parts[3],
                "body": parts[4].strip() if len(parts) > 4 else "",
            })
    return {
        "head": git("rev-parse", "HEAD"),
        "branch": git("rev-parse", "--abbrev-ref", "HEAD"),
        "dirty": bool(git("status", "--porcelain")),
        "remote": git("remote", "get-url", "origin"),
        "commits": commits,
    }


def skills() -> list[dict]:
    found = []
    for skill_dir in sorted(SKILLS_REPO.iterdir()):
        skill_md = skill_dir / "SKILL.md"
        if not skill_md.is_file():
            continue
        text = skill_md.read_text(encoding="utf-8")
        front = text.split("---", 2)[1] if text.startswith("---\n") else ""
        name = re.search(r"^name:\s*(.+)$", front, re.M)
        desc = re.search(r"^description:\s*(.+)$", front, re.M)
        found.append({
            "dir": skill_dir.name,
            "name": name.group(1).strip() if name else skill_dir.name,
            "description": desc.group(1).strip() if desc else "",
            "body_lines": len(text.splitlines()),
        })
    return found
