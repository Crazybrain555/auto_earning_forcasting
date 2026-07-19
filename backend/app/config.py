"""Backend configuration.

Deployment-layer settings live here and in config.json — never inside the
skills repo. Override the config file path with FORECAST_BACKEND_CONFIG.
"""
from __future__ import annotations

import json
import os
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent
DEFAULT_CONFIG_PATH = BACKEND_DIR / "config.json"


def load_config() -> dict:
    path = Path(os.environ.get("FORECAST_BACKEND_CONFIG", DEFAULT_CONFIG_PATH)).resolve()
    cfg = json.loads(path.read_text(encoding="utf-8"))
    cfg["_config_path"] = str(path)

    project_root = (path.parent / cfg.get("project_root", "..")).resolve()
    cfg["project_root"] = str(project_root)
    cfg["runs_root"] = str((project_root / cfg.get("runs_root", "training-runs")).resolve())
    cfg["skills_repo"] = str((project_root / cfg.get("skills_repo", ".claude/skills")).resolve())
    jobs_dir = Path(cfg.get("jobs_dir", "jobs"))
    if not jobs_dir.is_absolute():
        jobs_dir = path.parent / jobs_dir
    cfg["jobs_dir"] = str(jobs_dir.resolve())
    return cfg


CONFIG = load_config()
