#!/usr/bin/env python3
"""Atomically commit a validated current-company forecast publication."""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Callable

_SCRIPT_DIR = Path(__file__).resolve().parent
if str(_SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPT_DIR))

from publication_contract import (
    PublicationContractError,
    final_pack_records_from_contract,
    normalize_utc_timestamp,
    parse_aware_timestamp,
    publication_bundle_hashes_from_contract,
    publication_bundle_hashes_from_records,
    publication_registry_contract,
    seal_pack_hash,
    validate_live_seal_structure,
    validated_input_pack_hash_from_contract,
    validated_input_pack_hash_from_records,
    verify_file_records,
    verify_records_match_registry,
    workspace_artifact_path,
)
from runtime_context import skill_root_from_script


class PublicationError(RuntimeError):
    pass


ValidatorRunner = Callable[[Path, Path], None]


def _read_json(path: Path, label: str) -> dict:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise PublicationError(f"cannot read {label}: {exc}") from exc
    if not isinstance(value, dict):
        raise PublicationError(f"{label} must be an object")
    return value


def _atomic_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    file_descriptor, temporary_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    temporary = Path(temporary_name)
    try:
        with os.fdopen(file_descriptor, "wb") as handle:
            handle.write(json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8") + b"\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
        directory_fd = os.open(path.parent, os.O_RDONLY)
        try:
            os.fsync(directory_fd)
        finally:
            os.close(directory_fd)
    finally:
        if temporary.exists():
            temporary.unlink()


def _default_validator(workspace: Path, validator: Path) -> None:
    result = subprocess.run(
        [sys.executable, str(validator), "--workspace", str(workspace), "--strict"],
        capture_output=True,
        text=True,
    )
    if result.returncode:
        detail = (result.stdout + "\n" + result.stderr).strip()
        raise PublicationError("strict delivery validation failed: " + detail[-8000:])


def _receipt_backups(
    workspace: Path,
    *,
    registry_contract: dict,
) -> dict[Path, bytes | None]:
    backups: dict[Path, bytes | None] = {}
    for artifact in registry_contract["artifacts"]:
        if artifact.get("artifact_role") != "receipt":
            continue
        path = workspace_artifact_path(
            workspace,
            artifact["path"],
            require_file=False,
        )
        backups[path] = path.read_bytes() if path.is_file() else None
    return backups


def _restore(path: Path, original: bytes | None) -> None:
    if original is None:
        if path.exists():
            path.unlink()
        return
    file_descriptor, temporary_name = tempfile.mkstemp(prefix=f".{path.name}.restore.", dir=path.parent)
    temporary = Path(temporary_name)
    try:
        with os.fdopen(file_descriptor, "wb") as handle:
            handle.write(original)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        if temporary.exists():
            temporary.unlink()


def verify(workspace: Path | str, *, skill_root: Path | str | None = None) -> dict:
    workspace = Path(workspace).resolve()
    # ``skill_root`` remains in the public API for callers upgrading in place,
    # but verification deliberately uses only the contract frozen in the seal.
    _ = skill_root
    try:
        seal_path = workspace_artifact_path(
            workspace,
            "forecast_seal.json",
            require_file=True,
        )
        seal = _read_json(seal_path, "forecast_seal.json")
        validate_live_seal_structure(seal)
        if seal_pack_hash(seal) != seal.get("pack_hash"):
            raise PublicationContractError("forecast seal pack_hash mismatch")
        records = verify_file_records(workspace, seal.get("files"))
        registry_contract = seal["registry"]
        verify_records_match_registry(records, registry_contract)

        current_input_hash = validated_input_pack_hash_from_records(
            records,
            registry_contract,
        )
        if current_input_hash != seal["validated_input_pack_hash"]:
            raise PublicationContractError("validated input pack hash mismatch")
        current_bundles = publication_bundle_hashes_from_records(
            records,
            registry_contract,
        )
        if current_bundles != seal["bundle_hashes"]:
            raise PublicationContractError("published capability bundle hash mismatch")

        records_by_path = {record["path"]: record for record in records}
        if records_by_path["forecast_snapshot.json"]["sha256"] != seal["snapshot_hash"]:
            raise PublicationContractError("snapshot hash mismatch")
        if (
            records_by_path["delivery_validation.json"]["sha256"]
            != seal["delivery_receipt_hash"]
        ):
            raise PublicationContractError("delivery receipt hash mismatch")

        manifest = _read_json(
            workspace_artifact_path(
                workspace,
                "run_manifest.json",
                require_file=True,
            ),
            "run_manifest.json",
        )
        snapshot = _read_json(
            workspace_artifact_path(
                workspace,
                "forecast_snapshot.json",
                require_file=True,
            ),
            "forecast_snapshot.json",
        )
        receipt = _read_json(
            workspace_artifact_path(
                workspace,
                "delivery_validation.json",
                require_file=True,
            ),
            "delivery_validation.json",
        )
        if manifest.get("run_id") != seal["run_id"]:
            raise PublicationContractError("sealed manifest run_id differs from seal")
        if snapshot.get("forecast_id") != seal["forecast_id"]:
            raise PublicationContractError("sealed snapshot forecast_id differs from seal")
        publication = snapshot.get("publication")
        if not isinstance(publication, dict):
            raise PublicationContractError("sealed snapshot publication metadata is missing")
        if publication.get("bundle_hashes") != seal["bundle_hashes"]:
            raise PublicationContractError("snapshot publication bundle hashes differ from seal")
        if publication.get("supersedes") != seal["supersedes"]:
            raise PublicationContractError("snapshot supersedes differs from seal")
        if parse_aware_timestamp(
            publication.get("frozen_at"),
            label="snapshot publication frozen_at",
        ) != parse_aware_timestamp(seal["frozen_at"], label="forecast seal frozen_at"):
            raise PublicationContractError("snapshot frozen_at differs from seal")
        if snapshot.get("source_pack_hash") != seal["bundle_hashes"]["evidence_bundle"]:
            raise PublicationContractError("snapshot source_pack_hash differs from evidence bundle")
        if not (
            receipt.get("passed") is True
            and receipt.get("strict") is True
            and receipt.get("errors") == 0
            and receipt.get("validated_input_pack_hash")
            == seal["validated_input_pack_hash"]
        ):
            raise PublicationContractError("delivery receipt does not bind the sealed input pack")
    except PublicationError:
        raise
    except (PublicationContractError, OSError, ValueError, KeyError) as exc:
        raise PublicationError(str(exc)) from exc
    return seal


def _verified_supersedes(
    prior_workspace: Path,
    *,
    current_manifest: dict,
    current_frozen_at: dt.datetime,
    skill_root: Path,
) -> dict:
    prior_seal = verify(prior_workspace, skill_root=skill_root)
    try:
        prior_manifest_path = workspace_artifact_path(
            prior_workspace,
            "run_manifest.json",
            require_file=True,
        )
    except PublicationContractError as exc:
        raise PublicationError(str(exc)) from exc
    prior_manifest = _read_json(prior_manifest_path, "prior run_manifest.json")
    current_identity = (
        str(current_manifest.get("entity") or "").strip().casefold(),
        str(current_manifest.get("security") or "").strip().upper(),
    )
    prior_identity = (
        str(prior_manifest.get("entity") or "").strip().casefold(),
        str(prior_manifest.get("security") or "").strip().upper(),
    )
    if current_identity != prior_identity:
        raise PublicationError("superseded forecast has a different entity or security")
    if str(prior_seal.get("forecast_id") or "") == str(current_manifest.get("forecast_id") or ""):
        raise PublicationError("a new publication must use a new forecast identity")
    prior_frozen_at = parse_aware_timestamp(
        prior_seal.get("frozen_at"),
        label="superseded forecast frozen_at",
    )
    if prior_frozen_at >= current_frozen_at:
        raise PublicationError("new publication must freeze after the superseded version")
    return {
        "forecast_id": prior_seal["forecast_id"],
        "pack_hash": prior_seal["pack_hash"],
        "frozen_at": prior_seal["frozen_at"],
    }


def publish(
    workspace: Path | str,
    *,
    skill_root: Path | str | None = None,
    supersedes_workspace: Path | str | None = None,
    frozen_at: str | None = None,
    validator_runner: ValidatorRunner | None = None,
) -> dict:
    workspace = Path(workspace).resolve()
    skill_root = Path(skill_root).resolve() if skill_root else skill_root_from_script(__file__)
    try:
        seal_path = workspace_artifact_path(
            workspace,
            "forecast_seal.json",
            require_file=False,
        )
        manifest_path = workspace_artifact_path(
            workspace,
            "run_manifest.json",
            require_file=True,
        )
        snapshot_path = workspace_artifact_path(
            workspace,
            "forecast_snapshot.json",
            require_file=True,
        )
    except PublicationContractError as exc:
        raise PublicationError(str(exc)) from exc
    if seal_path.exists():
        raise PublicationError("workspace is already published; create a new forecast workspace")
    manifest = _read_json(manifest_path, "run_manifest.json")
    original_snapshot = snapshot_path.read_bytes() if snapshot_path.is_file() else None
    if original_snapshot is None:
        raise PublicationError("forecast_snapshot.json is missing")
    snapshot = _read_json(snapshot_path, "forecast_snapshot.json")
    forecast_id = str(snapshot.get("forecast_id") or "").strip()
    run_id = str(manifest.get("run_id") or "").strip()
    if not forecast_id or not run_id:
        raise PublicationError("forecast_id and run_id are required")
    frozen_at = frozen_at or dt.datetime.now(dt.timezone.utc).isoformat()
    try:
        frozen_at = normalize_utc_timestamp(frozen_at, label="frozen_at")
        frozen_at_instant = parse_aware_timestamp(frozen_at, label="frozen_at")
    except PublicationContractError as exc:
        raise PublicationError(str(exc)) from exc

    prior: dict | None = None
    if supersedes_workspace is not None:
        prior = _verified_supersedes(
            Path(supersedes_workspace).resolve(),
            current_manifest={**manifest, "forecast_id": forecast_id},
            current_frozen_at=frozen_at_instant,
            skill_root=skill_root,
        )

    lock_path = workspace / ".publish.lock"
    try:
        lock_descriptor = os.open(lock_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    except FileExistsError as exc:
        raise PublicationError("another publisher holds the workspace lock") from exc
    validator_runner = validator_runner or _default_validator
    receipt_backups: dict[Path, bytes | None] = {}
    seal_committed = False
    try:
        os.close(lock_descriptor)
        registry_contract = publication_registry_contract(
            workspace,
            skill_root=skill_root,
            profile="live",
        )
        receipt_backups = _receipt_backups(
            workspace,
            registry_contract=registry_contract,
        )
        before_bundles = publication_bundle_hashes_from_contract(
            workspace,
            registry_contract,
        )
        snapshot["publication"] = {
            "contract_version": "forecast-live-publication/v1",
            "frozen_at": frozen_at,
            "bundle_hashes": before_bundles,
            "supersedes": prior,
        }
        snapshot["source_pack_hash"] = before_bundles["evidence_bundle"]
        _atomic_json(snapshot_path, snapshot)

        expected_input_hash = validated_input_pack_hash_from_contract(
            workspace,
            registry_contract,
        )
        validator_runner(workspace, skill_root / "scripts" / "validate_delivery.py")
        receipt_path = workspace_artifact_path(
            workspace,
            "delivery_validation.json",
            require_file=True,
        )
        receipt = _read_json(receipt_path, "delivery_validation.json")
        if not (
            receipt.get("passed") is True
            and receipt.get("strict") is True
            and receipt.get("errors") == 0
        ):
            raise PublicationError("strict delivery validation failed")
        if receipt.get("validated_input_pack_hash") != expected_input_hash:
            raise PublicationError("delivery receipt does not bind the final input pack")
        after_registry_contract = publication_registry_contract(
            workspace,
            skill_root=skill_root,
            profile="live",
        )
        if after_registry_contract != registry_contract:
            raise PublicationError("artifact registry contract changed during validation")
        after_bundles = publication_bundle_hashes_from_contract(
            workspace,
            registry_contract,
        )
        if after_bundles != before_bundles:
            raise PublicationError("capability bundle changed during validation")
        if (
            validated_input_pack_hash_from_contract(workspace, registry_contract)
            != expected_input_hash
        ):
            raise PublicationError("validated input pack changed during validation")

        files = final_pack_records_from_contract(workspace, registry_contract)
        files_by_path = {record["path"]: record for record in files}
        seal: dict = {
            "schema_version": "forecast-seal/v1",
            "seal_kind": "live_publication",
            "status": "published",
            "forecast_id": forecast_id,
            "run_id": run_id,
            "frozen_at": frozen_at,
            "registry": registry_contract,
            "bundle_hashes": after_bundles,
            "supersedes": prior,
            "validated_input_pack_hash": expected_input_hash,
            "snapshot_hash": files_by_path["forecast_snapshot.json"]["sha256"],
            "delivery_receipt_hash": files_by_path["delivery_validation.json"]["sha256"],
            "files": files,
        }
        seal["pack_hash"] = seal_pack_hash(seal)
        _atomic_json(seal_path, seal)
        verify(workspace, skill_root=skill_root)
        seal_committed = True
        return seal
    except PublicationError:
        raise
    except (PublicationContractError, OSError, ValueError) as exc:
        raise PublicationError(str(exc)) from exc
    except Exception as exc:
        raise PublicationError(str(exc)) from exc
    finally:
        try:
            if not seal_committed:
                if seal_path.is_file() or seal_path.is_symlink():
                    seal_path.unlink()
                _restore(snapshot_path, original_snapshot)
                for path, original in receipt_backups.items():
                    _restore(path, original)
        finally:
            if lock_path.is_file() or lock_path.is_symlink():
                lock_path.unlink()


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Publish or verify a workspace drift-evident live forecast"
    )
    parser.add_argument("--workspace", required=True)
    parser.add_argument("--supersedes-workspace")
    parser.add_argument("--verify", action="store_true")
    args = parser.parse_args()
    try:
        if args.verify:
            result = verify(args.workspace)
        else:
            result = publish(
                args.workspace,
                supersedes_workspace=args.supersedes_workspace,
            )
    except PublicationError as exc:
        print(json.dumps({"status": "FAIL", "error": str(exc)}, ensure_ascii=False, indent=2))
        return 2
    print(json.dumps({"status": "PASS", "seal": result}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
