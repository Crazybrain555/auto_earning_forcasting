#!/usr/bin/env python3
"""Seal a training forecast BEFORE its actuals are retrieved.

Runs the three delivery validators, stamps the workspace state, then writes a
seal over every file except the seal-exempt subtrees (evaluation/,
actuals_vault/). After sealing, any modified, removed, or ADDED file outside
those subtrees makes verification fail (see _seal_core).
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _seal_core as core
from runtime_context import skill_root_from_script
from training_runtime_policy import load_training_profile


def _json_object(path: Path) -> dict:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        raise SystemExit(f"historical_train preflight cannot read {path.name}: {exc}")
    if not isinstance(value, dict):
        raise SystemExit(f"historical_train preflight requires an object in {path.name}")
    return value


def require_historical_training_workspace(workspace: Path) -> None:
    """Reject live/audit workspaces before validators or state mutation."""

    load_training_profile(skill_root_from_script(__file__))
    mode = _json_object(workspace / "mode_config.json")
    manifest = _json_object(workspace / "run_manifest.json")
    state = _json_object(workspace / "training_state.json")
    snapshot = _json_object(workspace / "forecast_snapshot.json")
    errors: list[str] = []
    for label, value in (
        ("mode_config.run_mode", mode.get("run_mode")),
        ("run_manifest.run_mode", manifest.get("run_mode")),
        ("forecast_snapshot.run_mode", snapshot.get("run_mode")),
    ):
        if value != "historical_train":
            errors.append(f"{label} must be historical_train, got {value!r}")
    if mode.get("enforce_source_cutoff") is not True:
        errors.append("mode_config.enforce_source_cutoff must be true")
    if manifest.get("time_boundary_enforced") is not True:
        errors.append("run_manifest.time_boundary_enforced must be true")
    timestamps = {
        str(mode.get("as_of") or ""),
        str(manifest.get("as_of") or ""),
        str(snapshot.get("as_of") or ""),
    }
    if "" in timestamps or len(timestamps) != 1:
        errors.append("mode, manifest and snapshot must share one explicit historical as_of")
    if mode.get("phase") != "forecast" or state.get("phase") != "forecast":
        errors.append("mode_config and training_state must both be in forecast phase")
    if mode.get("actuals_retrieval_allowed") is not False:
        errors.append("actuals_retrieval_allowed must be false before seal")
    if not str(state.get("case_id") or "").strip():
        errors.append("training_state.case_id is required")
    if state.get("case_role") not in {"development", "validation", "regression"}:
        errors.append("training_state.case_role is invalid")
    manifest_round = str(manifest.get("training_round_id") or "").strip()
    state_round = str(state.get("round_id") or "").strip()
    if manifest_round or state_round:
        if not manifest_round or manifest_round != state_round:
            errors.append("training round identity differs between manifest and training_state")
    if errors:
        raise SystemExit("historical_train preflight failed: " + "; ".join(errors))


def group_lock_hash(round_dir: Path):
    """Lock the round's group membership: sha256 over round id, base commit and
    both groups' case identities. Sealed cases whose receipts carry different
    lock hashes reveal a mid-round company swap. None for ad-hoc cases."""
    round_json = round_dir / "round.json"
    if not round_json.is_file():
        return None
    try:
        plan = json.loads(round_json.read_text(encoding="utf-8"))
    except Exception:
        return None
    def ids(group):
        out = []
        for case in plan.get(group) or []:
            if isinstance(case, dict):
                out.append(case.get("case_id") or f"{case.get('security')}@{case.get('as_of')}")
        return sorted(str(x) for x in out)
    locked = {"round_id": plan.get("round_id"), "base_method_commit": plan.get("base_method_commit"),
              "group_a": ids("group_a"), "group_b": ids("group_b")}
    canon = json.dumps(locked, sort_keys=True, separators=(",", ":")).encode()
    return "sha256:" + hashlib.sha256(canon).hexdigest()


def run(cmd):
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode:
        print(result.stdout + result.stderr)
        raise SystemExit(result.returncode)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--workspace", required=True)
    args = parser.parse_args()
    workspace = Path(args.workspace).resolve()
    scripts = Path(__file__).resolve().parent
    if (workspace / "forecast_seal.json").exists():
        raise SystemExit("forecast already sealed")

    require_historical_training_workspace(workspace)

    run([sys.executable, str(scripts / "validate_time_boundary.py"), "--workspace", str(workspace), "--strict"])
    run([sys.executable, str(scripts / "validate_research_completeness.py"), "--workspace", str(workspace), "--strict"])
    run([sys.executable, str(scripts / "validate_delivery.py"), "--workspace", str(workspace), "--strict"])

    now = dt.datetime.now(dt.timezone.utc).isoformat()
    mode = json.loads((workspace / "mode_config.json").read_text(encoding="utf-8"))
    mode.update({"phase": "sealed", "actuals_retrieval_allowed": True})
    (workspace / "mode_config.json").write_text(json.dumps(mode, indent=2) + "\n", encoding="utf-8")
    state = json.loads((workspace / "training_state.json").read_text(encoding="utf-8"))
    state.update({"phase": "sealed", "forecast_sealed_at": now})
    (workspace / "training_state.json").write_text(json.dumps(state, indent=2) + "\n", encoding="utf-8")
    snap = json.loads((workspace / "forecast_snapshot.json").read_text(encoding="utf-8"))
    snap["forecast_sealed_before_actuals"] = True
    snap["run_mode"] = "historical_train"
    (workspace / "forecast_snapshot.json").write_text(json.dumps(snap, indent=2) + "\n", encoding="utf-8")

    try:
        seal = core.build_seal(workspace, sealed_at=now)
    except core.SealError as exc:
        raise SystemExit(f"seal failed: {exc}")
    (workspace / "forecast_seal.json").write_text(json.dumps(seal, indent=2) + "\n", encoding="utf-8")

    # External seal receipt: recorded OUTSIDE the workspace before any actual is
    # retrieved. Closes the rewrite-the-whole-workspace hole: the scorer refuses
    # to score without a receipt whose pack_hash matches the in-workspace seal.
    receipt_dir = workspace.parent / "seal_receipts"
    receipt_path = receipt_dir / f"{workspace.name}.json"
    if receipt_path.exists():
        (workspace / "forecast_seal.json").unlink()
        raise SystemExit(
            f"seal receipt already exists for {workspace.name} - this case was sealed once "
            "before; a reseal after possible actuals exposure is not clean validation. "
            "Use a fresh case workspace (new case id) instead.")
    receipt = {
        "schema_version": 1,
        "round_id": workspace.parent.name,
        "case_id": workspace.name,
        "forecast_workspace": str(workspace),
        "pack_hash": seal["pack_hash"],
        "file_count": len(seal["files"]),
        "sealed_at": now,
        "recorded_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "recorded_before_actuals": True,
        "group_lock_hash": group_lock_hash(workspace.parent),
    }
    try:
        receipt_dir.mkdir(exist_ok=True)
        receipt_path.write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
        os.chmod(receipt_path, 0o444)
    except Exception as exc:
        (workspace / "forecast_seal.json").unlink()   # transactional: no receipt -> no seal
        raise SystemExit(f"failed to record external seal receipt, seal rolled back: {exc}")
    print(json.dumps({"status": seal["status"], "sealed_at": now,
                      "pack_hash": seal["pack_hash"], "files": len(seal["files"]),
                      "seal_receipt": str(receipt_path)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
