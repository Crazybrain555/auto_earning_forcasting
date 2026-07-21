"""Specialists consume accepted bundles without knowing coordinator run policy.

The orthogonal failure guarded here is policy leakage across a capability
boundary.  Historical evaluation policy belongs to the coordinator that
creates the bundle; the shared specialist contract carries only accepted
inputs and audit identity.
"""

from __future__ import annotations

import importlib.util
import json
import shutil
from pathlib import Path


TRAINER = Path(__file__).resolve().parents[1]
CANONICAL = TRAINER / "assets" / "skill_system"
SPECIALISTS = (
    "company-evidence-research",
    "company-operating-modeling",
    "company-financial-forecasting",
)
POLICY_WORDS = ("trainer", "run_mode", "sealed_historical", "cutoff", "actuals")
FIXED_FORBIDDEN_INPUTS = {
    "unaccepted_orchestrator_bundle",
    "unrestricted_source_access",
    "raw_actuals_channel",
}


def _json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _validator_module():
    path = TRAINER / "scripts" / "validate_skill_system.py"
    spec = importlib.util.spec_from_file_location("validate_skill_system", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _staged_system(tmp_path: Path) -> Path:
    system = tmp_path / "system"
    system.mkdir()
    for name in SPECIALISTS:
        shutil.copytree(CANONICAL / "skills" / name, system / name)
    shutil.copytree(CANONICAL / "contracts", system / "forecasting-system-contracts")
    live = system / "technology-company-profit-forecasting"
    live.mkdir()
    (live / "SKILL.md").write_text(
        "---\nname: technology-company-profit-forecasting\n"
        "description: coordinate forecasts\n---\n",
        encoding="utf-8",
    )
    return system


def test_specialist_instructions_and_profiles_are_mode_agnostic():
    for name in SPECIALISTS:
        root = CANONICAL / "skills" / name
        skill_text = (root / "SKILL.md").read_text(encoding="utf-8").lower()
        profile = _json(root / "assets" / "capability.json")

        assert not any(word in skill_text for word in POLICY_WORDS), name
        assert "accepted" in skill_text and "orchestrator" in skill_text
        assert profile["schema_version"] == "forecast-capability-profile/v2"
        assert "allowed_modes" not in profile
        assert "forbidden_inputs_by_mode" not in profile
        assert set(profile["forbidden_inputs"]) == FIXED_FORBIDDEN_INPUTS


def test_shared_manifest_and_contracts_do_not_own_historical_policy():
    manifest = _json(CANONICAL / "manifest.json")
    contracts = "\n".join(
        path.read_text(encoding="utf-8")
        for path in sorted((CANONICAL / "contracts").rglob("*"))
        if path.is_file()
    ).lower()

    assert "training_contract" not in manifest
    assert not any(word in contracts for word in POLICY_WORDS)


def test_handoff_time_is_audit_identity_and_inputs_require_acceptance():
    schema = _json(CANONICAL / "contracts/schemas/capability_handoff.schema.json")
    required = set(schema["required"])
    properties = schema["properties"]

    assert schema["$id"] == "forecast-capability-handoff/v2"
    assert "snapshot_at" in required
    assert "orchestrator_acceptance_ref" in required
    assert "as_of" not in required and "as_of" not in properties
    description = properties["snapshot_at"]["description"].lower()
    assert "audit" in description
    assert "permission" in description
    assert properties["orchestrator_acceptance_ref"]["minLength"] == 1


def test_system_validator_rejects_mode_fields_but_accepts_static_boundary(tmp_path):
    validator = _validator_module()
    system = _staged_system(tmp_path)
    assert validator.validate(system, TRAINER) == []

    profile_path = system / SPECIALISTS[0] / "assets/capability.json"
    profile = _json(profile_path)
    profile["allowed_modes"] = ["some_mode"]
    profile_path.write_text(json.dumps(profile), encoding="utf-8")

    errors = validator.validate(system, TRAINER)
    assert any("mode policy" in error for error in errors)
