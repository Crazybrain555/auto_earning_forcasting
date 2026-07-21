#!/usr/bin/env python3
"""Project a Trainer-controlled case into a capability-safe input view.

The specialist processes only this projected directory.  Historical source
eligibility, unrestricted retrieval, case roles, seal state and the outcome
channel remain outside the view and under Trainer control.
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Callable


CAPABILITY_FILES = {
    "evidence_research": (),
    "operating_model": (
        "claim_ledger.jsonl",
        "data_series_register.csv",
        "financial_fact_ledger.csv",
        "source_independence_map.csv",
        "forward_signal_cards.csv",
        "technical_evidence_records.jsonl",
        "research_quality_review.json",
        "research_completeness.json",
        "historical_segment_bridge.csv",
    ),
    "financial_forecast": (
        "claim_ledger.jsonl",
        "data_series_register.csv",
        "financial_fact_ledger.csv",
        "source_independence_map.csv",
        "forward_signal_cards.csv",
        "technical_evidence_records.jsonl",
        "research_quality_review.json",
        "research_completeness.json",
        "historical_segment_bridge.csv",
        "assumption_register.csv",
        "product_customer_driver_schedule.csv",
        "model_graph.json",
        "scenario_set.json",
        "model_checks.json",
        "driver_monitoring.csv",
    ),
}

DECISION_FIELDS = (
    "contract_version",
    "method_version",
    "run_id",
    "entity",
    "security",
    "purpose",
    "fiscal_calendar",
    "currency",
    "accounting_basis",
    "horizons",
    "intended_decision",
    "analysis_primitives",
    "materiality_routes",
    "readiness_target",
    "narrow_scope_exception",
)

SOURCE_ELIGIBILITY_FIELDS = {
    "as_of_valid",
    "source_time_status",
    "forecast_permission",
    "eligibility_status",
    "cutoff",
}


class ProjectionError(ValueError):
    pass


def _read_object(path: Path) -> dict:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        raise ProjectionError(f"cannot read {path.name}: {exc}") from exc
    if not isinstance(value, dict):
        raise ProjectionError(f"{path.name} must contain an object")
    return value


def _sha256_bytes(value: bytes) -> str:
    return "sha256:" + hashlib.sha256(value).hexdigest()


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return "sha256:" + digest.hexdigest()


def _canonical_bytes(value: object) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")


def require_pre_outcome_phase(workspace: Path) -> tuple[dict, dict, dict]:
    mode = _read_object(workspace / "mode_config.json")
    state = _read_object(workspace / "training_state.json")
    manifest = _read_object(workspace / "run_manifest.json")
    errors: list[str] = []
    if mode.get("run_mode") != "historical_train":
        errors.append("workspace is not owned by the historical evaluation coordinator")
    if mode.get("phase") != "forecast" or state.get("phase") != "forecast":
        errors.append("capability projection is allowed only during the forecast phase")
    if mode.get("actuals_retrieval_allowed") is not False:
        errors.append("outcome retrieval must remain closed")
    if (workspace / "forecast_seal.json").exists():
        errors.append("a sealed case cannot re-enter a forecasting capability")
    for protected in ("actuals_vault", "evaluation"):
        directory = workspace / protected
        if directory.exists() and any(directory.rglob("*")):
            errors.append(f"{protected} is not empty")
    if errors:
        raise ProjectionError("; ".join(errors))
    return mode, state, manifest


def _default_boundary_validator(workspace: Path) -> str:
    script = Path(__file__).resolve().parent / "validate_time_boundary.py"
    result = subprocess.run(
        [
            sys.executable,
            str(script),
            "--workspace",
            str(workspace),
            "--strict",
        ],
        capture_output=True,
        text=True,
    )
    if result.returncode:
        raise ProjectionError(
            "historical eligibility validation failed: "
            + (result.stdout + result.stderr).strip()
        )
    return result.stdout


def _sanitize_sources(source_manifest: dict, *, projection_at: str) -> dict:
    sources = []
    for raw in source_manifest.get("sources", []):
        if not isinstance(raw, dict):
            continue
        source = {
            key: value
            for key, value in raw.items()
            if key not in SOURCE_ELIGIBILITY_FIELDS
        }
        sources.append(source)
    return {
        "schema_version": "forecast-capability-source-view/v1",
        "assembled_at": projection_at,
        "entity": source_manifest.get("entity"),
        "security": source_manifest.get("security"),
        "sources": sources,
        "conflicts": source_manifest.get("conflicts", []),
    }


def project_view(
    workspace: Path | str,
    output: Path | str,
    capability_id: str,
    *,
    boundary_validator: Callable[[Path], str] = _default_boundary_validator,
) -> dict:
    workspace = Path(workspace).resolve()
    output = Path(output).resolve()
    if capability_id not in CAPABILITY_FILES:
        raise ProjectionError(f"unknown capability_id {capability_id!r}")
    if output.exists():
        raise ProjectionError(f"projection output already exists: {output}")
    _mode, state, manifest = require_pre_outcome_phase(workspace)
    boundary_receipt = boundary_validator(workspace)
    source_manifest = _read_object(workspace / "source_manifest.json")
    projection_at = dt.datetime.now(dt.timezone.utc).isoformat().replace("+00:00", "Z")
    decision_bundle = {
        key: manifest[key]
        for key in DECISION_FIELDS
        if key in manifest
    }
    decision_bundle.update(
        {
            "protocol_version": "forecast-capability-handoff/v2",
            "bundle_kind": "decision_bundle",
            "snapshot_at": projection_at,
            "orchestrator_acceptance_ref": "pending",
        }
    )
    source_view = _sanitize_sources(source_manifest, projection_at=projection_at)
    acceptance_payload = {
        "case_id": state.get("case_id"),
        "capability_id": capability_id,
        "method_version": manifest.get("method_version"),
        "boundary_receipt_sha256": _sha256_bytes(boundary_receipt.encode("utf-8")),
        "source_view_sha256": _sha256_bytes(_canonical_bytes(source_view)),
    }
    acceptance_ref = _sha256_bytes(_canonical_bytes(acceptance_payload))
    decision_bundle["orchestrator_acceptance_ref"] = acceptance_ref

    output.mkdir(parents=True)
    try:
        (output / "decision_bundle.json").write_text(
            json.dumps(decision_bundle, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        (output / "source_records.json").write_text(
            json.dumps(source_view, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        copied = []
        for relative in CAPABILITY_FILES[capability_id]:
            source = workspace / relative
            if not source.is_file():
                continue
            destination = output / relative
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, destination)
            copied.append(relative)

        artifacts = []
        for path in sorted(item for item in output.rglob("*") if item.is_file()):
            artifacts.append(
                {
                    "path": path.relative_to(output).as_posix(),
                    "sha256": _sha256_file(path),
                }
            )
        projection = {
            "schema_version": "forecast-capability-input-view/v1",
            "capability_id": capability_id,
            "snapshot_at": projection_at,
            "orchestrator_acceptance_ref": acceptance_ref,
            "artifact_refs": artifacts,
            "specialist_access": "projected_files_only",
            "unrestricted_retrieval": False,
        }
        (output / "projection_manifest.json").write_text(
            json.dumps(projection, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        for path in output.rglob("*"):
            if path.is_file():
                os.chmod(path, 0o444)
        return projection
    except Exception:
        shutil.rmtree(output, ignore_errors=True)
        raise


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Create a read-only capability input view from a controlled historical case."
    )
    parser.add_argument("--workspace", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--capability", required=True, choices=sorted(CAPABILITY_FILES))
    args = parser.parse_args()
    try:
        result = project_view(args.workspace, args.output, args.capability)
    except ProjectionError as exc:
        print(json.dumps({"status": "FAIL", "error": str(exc)}, indent=2))
        return 2
    print(json.dumps({"status": "PASS", **result}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
