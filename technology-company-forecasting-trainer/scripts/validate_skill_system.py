#!/usr/bin/env python3
"""Validate the five-skill forecasting system and its shared handoffs."""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path


FRONTMATTER_NAME = re.compile(r"(?m)^name:\s*([^\s]+)\s*$")
IGNORED_PARTS = {"__pycache__", ".pytest_cache", ".cache"}
SPECIALIST_POLICY_WORDS = ("trainer", "run_mode", "sealed_historical", "cutoff", "actuals")
FIXED_FORBIDDEN_INPUTS = {
    "unaccepted_orchestrator_bundle",
    "unrestricted_source_access",
    "raw_actuals_channel",
}


def _load(path: Path) -> object:
    return json.loads(path.read_text(encoding="utf-8"))


def _tree_hash(root: Path) -> str:
    digest = hashlib.sha256()
    for path in sorted(item for item in root.rglob("*") if item.is_file()):
        rel = path.relative_to(root)
        if any(part in IGNORED_PARTS for part in rel.parts) or path.suffix in {".pyc", ".pyo"}:
            continue
        digest.update(rel.as_posix().encode("utf-8"))
        digest.update(b"\0")
        digest.update(hashlib.sha256(path.read_bytes()).digest())
    return "sha256:" + digest.hexdigest()


def validate(system_root: Path, trainer_root: Path) -> list[str]:
    errors: list[str] = []
    source_root = trainer_root / "assets" / "skill_system"
    manifest_path = source_root / "manifest.json"
    if not manifest_path.is_file():
        return [f"missing system manifest: {manifest_path}"]
    try:
        manifest = _load(manifest_path)
        method = _load(trainer_root / "assets" / "method_system.json")
    except (OSError, json.JSONDecodeError) as exc:
        return [f"cannot load system authority: {exc}"]

    if not isinstance(manifest, dict) or manifest.get("schema_version") != "forecast-skill-system/v1":
        errors.append("manifest must use forecast-skill-system/v1")
        return errors
    capabilities = manifest.get("capabilities")
    if not isinstance(capabilities, dict) or len(capabilities) != 3:
        errors.append("system must have exactly three capability skills")
        return errors

    stages = method.get("stages") if isinstance(method, dict) else None
    stage_ids = {
        row.get("id") for row in stages or []
        if isinstance(row, dict) and isinstance(row.get("id"), str)
    }
    owners = manifest.get("stage_owners")
    if not isinstance(owners, dict) or set(owners) != stage_ids:
        errors.append("stage_owners must cover the canonical method stages exactly once")
    allowed_owners = set(capabilities) | {manifest.get("coordinators", {}).get("live")}
    if isinstance(owners, dict) and not set(owners.values()) <= allowed_owners:
        errors.append("stage_owners contains a non-capability/non-live-coordinator owner")

    profile_stage_ids: set[str] = set()
    for name, contract in capabilities.items():
        source = source_root / "skills" / name
        generated = system_root / name
        if not source.is_dir() or not generated.is_dir():
            errors.append(f"{name}: source and generated skill directories are required")
            continue
        if _tree_hash(source) != _tree_hash(generated):
            errors.append(f"{name}: generated skill differs from promotion-bound source")
        skill_path = generated / "SKILL.md"
        profile_path = generated / "assets" / "capability.json"
        evals_path = generated / "evals" / "evals.json"
        try:
            skill_text = skill_path.read_text(encoding="utf-8")
            profile = _load(profile_path)
            evals = _load(evals_path)
        except (OSError, json.JSONDecodeError) as exc:
            errors.append(f"{name}: invalid generated package: {exc}")
            continue
        match = FRONTMATTER_NAME.search(skill_text.split("---", 2)[1] if skill_text.startswith("---") else "")
        if match is None or match.group(1) != name:
            errors.append(f"{name}: frontmatter name must match directory")
        if not isinstance(profile, dict) or profile.get("skill_name") != name:
            errors.append(f"{name}: capability profile skill_name mismatch")
            continue
        if profile.get("schema_version") != "forecast-capability-profile/v2":
            errors.append(f"{name}: capability profile must use forecast-capability-profile/v2")
        for field in ("capability_id", "input_bundle_kinds", "output_bundle_kind", "owned_stage_ids"):
            if profile.get(field) != contract.get(field):
                errors.append(f"{name}: profile {field} differs from system manifest")
        if "allowed_modes" in profile or "forbidden_inputs_by_mode" in profile:
            errors.append(f"{name}: specialist profile must not own mode policy")
        if set(profile.get("forbidden_inputs") or []) != FIXED_FORBIDDEN_INPUTS:
            errors.append(f"{name}: specialist profile must use the fixed input boundary")
        lower_skill = skill_text.lower()
        leaked = [word for word in SPECIALIST_POLICY_WORDS if word in lower_skill]
        if leaked:
            errors.append(f"{name}: specialist instructions contain coordinator policy: {', '.join(leaked)}")
        if "accepted" not in lower_skill or "orchestrator" not in lower_skill:
            errors.append(f"{name}: specialist instructions must consume accepted orchestrator bundles")
        owned = profile.get("owned_stage_ids") or []
        if profile_stage_ids.intersection(owned):
            errors.append(f"{name}: stage ownership overlaps another capability")
        profile_stage_ids.update(owned)
        if not isinstance(evals, dict) or evals.get("skill_name") != name or len(evals.get("evals") or []) < 2:
            errors.append(f"{name}: at least two realistic skill evals are required")
        if "../forecasting-system-contracts/" not in skill_text:
            errors.append(f"{name}: SKILL.md must route through the shared contract kernel")

    contracts_source = source_root / "contracts"
    contracts_generated = system_root / "forecasting-system-contracts"
    if not contracts_generated.is_dir() or _tree_hash(contracts_source) != _tree_hash(contracts_generated):
        errors.append("generated forecasting-system-contracts differs from promotion-bound source")
    if (contracts_generated / "SKILL.md").exists():
        errors.append("shared contracts must not be an invokable skill")
    try:
        protocol = _load(contracts_generated / "protocol_manifest.json")
        handoff = _load(contracts_generated / "schemas" / "capability_handoff.schema.json")
    except (OSError, json.JSONDecodeError) as exc:
        errors.append(f"shared protocol is invalid: {exc}")
    else:
        required_records = {
            "source_asset", "evidence_record", "evidence_use", "action_log",
            "evidence_request", "forecast_snapshot",
        }
        if set(protocol.get("records") or {}) != required_records:
            errors.append("protocol records must stay at the six independent lifecycle objects")
        boundary = protocol.get("bundle_boundary")
        if not isinstance(boundary, dict) or boundary.get("input_policy") != (
            "specialists_consume_only_orchestrator_accepted_handoffs"
        ):
            errors.append("protocol must require accepted orchestrator handoffs")
        if handoff.get("$id") != "forecast-capability-handoff/v2":
            errors.append("handoff schema id mismatch")
        handoff_required = set(handoff.get("required") or [])
        handoff_properties = handoff.get("properties") or {}
        if not {"snapshot_at", "orchestrator_acceptance_ref"} <= handoff_required:
            errors.append("handoff must bind audit snapshot and orchestrator acceptance")
        if "as_of" in handoff_required or "as_of" in handoff_properties:
            errors.append("handoff time must be audit snapshot identity, not eligibility policy")

    live_name = manifest.get("coordinators", {}).get("live")
    if not isinstance(live_name, str) or not (system_root / live_name / "SKILL.md").is_file():
        errors.append("generated live coordinator is missing")
    if "training_contract" in manifest:
        errors.append("shared system manifest must not own coordinator evaluation policy")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--system-root", required=True)
    parser.add_argument("--trainer-root", required=True)
    args = parser.parse_args()
    errors = validate(Path(args.system_root).resolve(), Path(args.trainer_root).resolve())
    payload = {"status": "FAIL" if errors else "PASS", "errors": errors}
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 2 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
