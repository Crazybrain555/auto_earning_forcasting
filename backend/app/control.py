"""The one file the dashboard side may write: training-runs/control.json.

Training sessions read it before each case (see project CLAUDE.md/AGENTS.md);
absence means auto_training is running.
"""
from __future__ import annotations

import datetime as dt
import json
from pathlib import Path

from .config import CONFIG

CONTROL_PATH = Path(CONFIG["runs_root"]) / "control.json"
VALID_STATES = {"run", "pause"}


def read_control() -> dict:
    if CONTROL_PATH.is_file():
        try:
            payload = json.loads(CONTROL_PATH.read_text(encoding="utf-8"))
            if payload.get("auto_training") in VALID_STATES:
                return payload
        except Exception:
            pass
    return {"auto_training": "run", "note": "default (no control.json present)", "updated_at": None}


def write_control(auto_training: str, note: str = "") -> dict:
    if auto_training not in VALID_STATES:
        raise ValueError(f"auto_training must be one of {sorted(VALID_STATES)}")
    payload = {
        "auto_training": auto_training,
        "note": note,
        "updated_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "updated_by": "dashboard-backend",
    }
    CONTROL_PATH.parent.mkdir(parents=True, exist_ok=True)
    CONTROL_PATH.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return payload
