"""Shared runtime identity stays neutral; training policy owns mode admission."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest


SKILL = Path(__file__).resolve().parents[1]


def _load(name: str):
    path = SKILL / "scripts" / f"{name}.py"
    spec = importlib.util.spec_from_file_location(f"forecast_{name}", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _write_profile(root: Path, payload: dict) -> None:
    assets = root / "assets"
    assets.mkdir(parents=True, exist_ok=True)
    (assets / "profile.json").write_text(json.dumps(payload), encoding="utf-8")


def test_shared_runtime_profile_accepts_arbitrary_identity_without_mode_policy(tmp_path):
    runtime = _load("runtime_context")
    root = tmp_path / "skill"
    _write_profile(
        root,
        {
            "schema_version": runtime.PROFILE_SCHEMA,
            "profile": "production-region-a",
            "runtime_scripts": ["runtime_context.py"],
        },
    )

    profile = runtime.load_profile(root)
    assert profile["profile"] == "production-region-a"
    assert "allowed_modes" not in profile
    assert not hasattr(runtime, "require_allowed_mode")


def test_shared_runtime_profile_rejects_blank_identity_and_invalid_script_inventory(tmp_path):
    runtime = _load("runtime_context")
    root = tmp_path / "skill"
    _write_profile(
        root,
        {
            "schema_version": runtime.PROFILE_SCHEMA,
            "profile": "",
            "runtime_scripts": ["runtime_context.py"],
        },
    )
    with pytest.raises(ValueError, match="profile name"):
        runtime.load_profile(root)

    _write_profile(
        root,
        {
            "schema_version": runtime.PROFILE_SCHEMA,
            "profile": "any-profile",
            "runtime_scripts": ["not-python.txt"],
        },
    )
    with pytest.raises(ValueError, match="runtime_scripts"):
        runtime.load_profile(root)


def test_training_policy_owns_trainer_identity_and_allowed_modes(tmp_path):
    policy = _load("training_runtime_policy")
    root = tmp_path / "skill"
    _write_profile(
        root,
        {
            "schema_version": "forecast-skill-profile/v1",
            "profile": "trainer",
            "allowed_modes": ["historical_train", "live_forecast"],
            "runtime_scripts": ["training_runtime_policy.py"],
        },
    )

    profile = policy.load_training_profile(root)
    assert policy.allowed_modes(profile) == ["historical_train", "live_forecast"]
    assert policy.require_allowed_mode(profile, "historical_train") == "historical_train"
    with pytest.raises(ValueError, match="supports only"):
        policy.require_allowed_mode(profile, "made_up")


def test_training_policy_rejects_nontrainer_or_missing_historical_mode(tmp_path):
    policy = _load("training_runtime_policy")
    root = tmp_path / "skill"
    base = {
        "schema_version": "forecast-skill-profile/v1",
        "profile": "production",
        "allowed_modes": ["historical_train"],
        "runtime_scripts": ["training_runtime_policy.py"],
    }
    _write_profile(root, base)
    with pytest.raises(ValueError, match="trainer profile"):
        policy.load_training_profile(root)

    base["profile"] = "trainer"
    base["allowed_modes"] = ["live_forecast"]
    _write_profile(root, base)
    with pytest.raises(ValueError, match="historical_train"):
        policy.load_training_profile(root)
