#!/usr/bin/env python3
"""Storage-neutral runtime identity.

Capability-specific admission policy belongs to the owning coordinator.  This
module only validates package identity and its declared runtime file inventory.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any


PROFILE_SCHEMA = "forecast-skill-profile/v1"


def skill_root_from_script(script_file: str | Path) -> Path:
    return Path(script_file).resolve().parent.parent


def load_profile(skill_root: str | Path) -> dict[str, Any]:
    path = Path(skill_root).resolve() / "assets" / "profile.json"
    payload = json.loads(path.read_text(encoding="utf-8"))
    if payload.get("schema_version") != PROFILE_SCHEMA:
        raise ValueError(f"invalid profile schema in {path}")
    profile = str(payload.get("profile") or "").strip()
    if not profile:
        raise ValueError(f"invalid profile name {profile or '<blank>'}")
    scripts = payload.get("runtime_scripts")
    if (
        not isinstance(scripts, list)
        or not scripts
        or any(not isinstance(item, str) or not item.endswith(".py") for item in scripts)
        or len(scripts) != len(set(scripts))
    ):
        raise ValueError("profile.runtime_scripts must be a unique non-empty .py array")
    payload["profile"] = profile
    return payload
