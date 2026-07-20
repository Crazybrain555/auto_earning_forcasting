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


# ---------- 方法演进脉络:每个版本改了什么、属于哪类 ----------
_CATEGORY_RULES = [
    (re.compile(r"references/module-|references/mechanism"), "机制规则"),
    (re.compile(r"references/historical-training-loop|references/.*loop"), "训练闭环"),
    (re.compile(r"scripts/validate_|scripts/.*seal|scripts/score_|scripts/freeze_"), "校验与封箱"),
    (re.compile(r"scripts/build_live_release|assets/live_release"), "发布链路"),
    (re.compile(r"assets/templates|assets/schemas"), "输出契约"),
    (re.compile(r"scripts/scaffold|scripts/package_self_test|scripts/"), "工具链"),
    (re.compile(r"tests/"), "测试"),
    (re.compile(r"assets/benchmarks|assets/examples"), "课程与示例"),
    (re.compile(r"SKILL\.md$|agents/"), "技能入口"),
]


def _categorize(files: list[str]) -> list[str]:
    cats: list[str] = []
    for f in files:
        for pattern, name in _CATEGORY_RULES:
            if pattern.search(f):
                if name not in cats:
                    cats.append(name)
                break
    return cats or ["其他"]


def evolution(limit: int = 60) -> dict:
    """git log --numstat 解析成结构化脉络:版本 → 类别 → 优化点 → 触及文件。"""
    raw = git("log", f"-n{limit}", "--numstat", "--pretty=format:\x1e%h\x1f%aI\x1f%s\x1f%b\x1d")
    versions = []
    for chunk in raw.split("\x1e"):
        chunk = chunk.strip()
        if not chunk:
            continue
        head, _, stat_part = chunk.partition("\x1d")
        parts = head.split("\x1f")
        if len(parts) < 3:
            continue
        files, adds, dels = [], 0, 0
        for line in stat_part.strip().splitlines():
            cols = line.split("\t")
            if len(cols) == 3:
                a, d, name = cols
                files.append(name)
                adds += int(a) if a.isdigit() else 0
                dels += int(d) if d.isdigit() else 0
        body = parts[3].strip() if len(parts) > 3 else ""
        body = re.sub(r"Co-Authored-By:.*", "", body, flags=re.I).strip()
        points = [ln.strip(" -*") for ln in body.splitlines()
                  if ln.strip().startswith(("-", "*", "1", "2", "3", "4", "5"))][:6]
        versions.append({
            "short": parts[0],
            "date": parts[1],
            "subject": parts[2],
            "body": body,
            "points": points,
            "categories": _categorize(files),
            "files": files[:12],
            "file_count": len(files),
            "adds": adds,
            "dels": dels,
        })
    return {"head": git("rev-parse", "--short", "HEAD"), "versions": versions}
