"""Method-evolution view: the skills git repo is the method history."""
from __future__ import annotations

import json
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
    (re.compile(r"references/(analysis-kernel|driver-tree|equation-primitives|industry-economics|technology-commercialization|valuation-and-market|business-quality)"), "因果与价值方法"),
    (re.compile(r"references/module-|references/mechanism"), "经济方程原语"),
    (re.compile(r"references/historical-training-loop|references/.*loop"), "训练闭环"),
    (re.compile(r"scripts/validate_|scripts/.*seal|scripts/score_|scripts/freeze_"), "校验与封箱"),
    (re.compile(r"scripts/(?:build_skill_system|build_live_release)|assets/live_release"), "发布链路"),
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


# ---------- 生产 skill 地图:canonical JSON → 阶段 / 硬门槛 / 责任文件 ----------
_LIVE_SKILL = "technology-company-profit-forecasting"


def _load_method_system(root: Path) -> tuple[dict, str]:
    """Load the versioned method map; never maintain a second Python truth."""
    candidates = [
        root / "assets" / "method_system.json",
        SKILLS_REPO / "technology-company-forecasting-trainer" / "assets" / "method_system.json",
    ]
    for path in candidates:
        if not path.is_file():
            continue
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
            if isinstance(payload.get("stages"), list):
                return payload, str(path)
        except (OSError, ValueError, TypeError):
            continue
    return {
        "schema_version": "unavailable",
        "method_id": "technology-company-causal-value-system",
        "method_version": "unavailable",
        "title": "Method map unavailable",
        "stages": [],
    }, ""


def skill_map() -> dict:
    root = SKILLS_REPO / _LIVE_SKILL
    method_system, source = _load_method_system(root)
    stages = []
    for index, stage in enumerate(method_system.get("stages", []), 1):
        files = []
        seen: set[str] = set()
        for pattern in stage.get("files", []):
            matches = sorted(root.glob(pattern)) if "*" in pattern else [root / pattern]
            for path in matches:
                rel = str(path.relative_to(root))
                if rel in seen:
                    continue
                seen.add(rel)
                entry = {"path": rel, "exists": path.is_file()}
                if entry["exists"]:
                    try:
                        text = path.read_text(encoding="utf-8", errors="replace")
                        entry["lines"] = len(text.splitlines())
                        for line in text.splitlines():
                            line = line.strip()
                            if line.startswith("#"):
                                entry["title"] = line.lstrip("# ").strip()
                                break
                    except OSError:
                        pass
                files.append(entry)
        stages.append({**stage, "no": f"{int(stage.get('no', index)):02d}", "files": files})
    return {
        "skill": _LIVE_SKILL,
        "root": str(root),
        "method_id": method_system.get("method_id"),
        "method_version": method_system.get("method_version"),
        "schema_version": method_system.get("schema_version"),
        "title": method_system.get("title"),
        "canonical_flow": method_system.get("canonical_flow", []),
        "judgment_boundary": method_system.get("judgment_boundary", {}),
        "optional_calibration": method_system.get("optional_calibration", {}),
        "source": source,
        "stages": stages,
        "how_to_change": "方法只在 trainer 的 canonical 源（协调器 SKILL.md、references/、templates/、assets/method_system.json，以及 assets/skill_system/ 的 specialists/contracts）中修改 → 用 scripts/build_skill_system.py 生成并自检全部 skill → 跑全套正交契约/回归 → 独立证据支持后再 commit、push；不要直接改生成副本。",
    }


def skill_file(rel_path: str) -> tuple[str, str] | None:
    """Read one file inside the live skill, traversal-safe. Returns (path, text)."""
    root = (SKILLS_REPO / _LIVE_SKILL).resolve()
    candidate = (root / rel_path).resolve()
    try:
        candidate.relative_to(root)
    except ValueError:
        return None
    if not candidate.is_file() or candidate.suffix not in {".md", ".py", ".json", ".yaml", ".yml", ".csv", ".jsonl"}:
        return None
    return str(candidate.relative_to(root)), candidate.read_text(encoding="utf-8", errors="replace")[:400_000]
