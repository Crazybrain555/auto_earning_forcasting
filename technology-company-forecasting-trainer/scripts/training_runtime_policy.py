#!/usr/bin/env python3
"""Trainer-owned runtime admission and historical-sandbox policy."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any


_SCRIPT_DIR = Path(__file__).resolve().parent
if str(_SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPT_DIR))

from runtime_context import load_profile


TRAINER_PROFILE = "trainer"
HISTORICAL_TRAIN_MODE = "historical_train"


def allowed_modes(profile: dict[str, Any]) -> list[str]:
    """Validate and return the coordinator-owned mode vocabulary."""

    declared = profile.get("allowed_modes")
    if (
        not isinstance(declared, list)
        or not declared
        or any(not isinstance(item, str) or not item.strip() for item in declared)
    ):
        raise ValueError("trainer profile.allowed_modes must be a non-empty string array")
    values = [item.strip() for item in declared]
    if len(set(values)) != len(values):
        raise ValueError("trainer profile.allowed_modes contains duplicates")
    return values


def load_training_profile(skill_root: str | Path) -> dict[str, Any]:
    """Load the trainer identity and prove that it owns historical training."""

    profile = load_profile(skill_root)
    if profile.get("profile") != TRAINER_PROFILE:
        raise ValueError(
            f"training runtime requires trainer profile, got {profile.get('profile')!r}"
        )
    modes = allowed_modes(profile)
    if HISTORICAL_TRAIN_MODE not in modes:
        raise ValueError("trainer profile must own historical_train")
    return profile


def require_allowed_mode(profile: dict[str, Any], mode: object) -> str:
    """Admit only a mode declared by the already-validated trainer profile."""

    value = str(mode or "").strip()
    admitted = allowed_modes(profile)
    if value not in admitted:
        raise ValueError(
            f"trainer profile supports only {', '.join(admitted)}; got {value or '<blank>'}"
        )
    return value


def artifact_profile_for_mode(mode: object) -> str:
    """Map trainer-owned run modes to the trainer registry's explicit views."""

    return TRAINER_PROFILE if str(mode).strip() == HISTORICAL_TRAIN_MODE else "live"
