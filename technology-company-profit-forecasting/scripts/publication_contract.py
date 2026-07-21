#!/usr/bin/env python3
"""Self-described hashing and file-integrity contracts for live publication."""
from __future__ import annotations

import datetime as dt
import hashlib
import json
import os
import re
import stat
from pathlib import Path, PurePosixPath
from typing import Any, Iterable, Mapping

from artifact_registry import load_registry, resolve_active_artifacts, validate_registry


class PublicationContractError(ValueError):
    pass


REGISTRY_CONTRACT_VERSION = "forecast-publication-registry/v1"
REQUIRED_BUNDLE_IDS = {
    "evidence_bundle",
    "operating_model_bundle",
    "financial_forecast_bundle",
}
REQUIRED_SEALED_PATHS = {
    "run_manifest.json",
    "forecast_snapshot.json",
    "delivery_validation.json",
}
FILE_RECORD_FIELDS = {
    "artifact_id",
    "path",
    "stage",
    "artifact_role",
    "sha256",
    "size_bytes",
}
ARTIFACT_IDENTITY_FIELDS = {"artifact_id", "path", "stage", "artifact_role"}
REGISTRY_CONTRACT_FIELDS = {
    "contract_version",
    "profile",
    "schema_version",
    "sha256",
    "publication_bundles",
    "artifacts",
}
SEAL_FIELDS = {
    "schema_version",
    "seal_kind",
    "status",
    "forecast_id",
    "run_id",
    "frozen_at",
    "registry",
    "bundle_hashes",
    "supersedes",
    "validated_input_pack_hash",
    "snapshot_hash",
    "delivery_receipt_hash",
    "files",
    "pack_hash",
}
HASH_RE = re.compile(r"^sha256:[0-9a-f]{64}$")


def canonical_bytes(value: object) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")


def sha256_bytes(value: bytes) -> str:
    return "sha256:" + hashlib.sha256(value).hexdigest()


def _hash_regular_file(path: Path) -> tuple[str, int]:
    """Hash one stable regular file and reject replacement during the read."""

    before_path = os.lstat(path)
    if not stat.S_ISREG(before_path.st_mode):
        kind = "symlink" if stat.S_ISLNK(before_path.st_mode) else "non-regular file"
        raise PublicationContractError(f"publication artifact is a {kind}: {path}")
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        before_fd = os.fstat(handle.fileno())
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
        after_fd = os.fstat(handle.fileno())
    after_path = os.lstat(path)
    signatures = {
        (
            item.st_dev,
            item.st_ino,
            item.st_size,
            item.st_mtime_ns,
        )
        for item in (before_path, before_fd, after_fd, after_path)
    }
    if len(signatures) != 1:
        raise PublicationContractError(f"publication artifact changed while hashing: {path}")
    return "sha256:" + digest.hexdigest(), after_fd.st_size


def sha256_file(path: Path) -> str:
    return _hash_regular_file(path)[0]


def registry_hash(registry: Mapping[str, Any]) -> str:
    return sha256_bytes(canonical_bytes(registry))


def parse_aware_timestamp(value: object, *, label: str) -> dt.datetime:
    raw = str(value or "").strip()
    if not raw:
        raise PublicationContractError(f"{label} must be an ISO timestamp with a timezone")
    candidate = raw[:-1] + "+00:00" if raw.endswith("Z") else raw
    try:
        parsed = dt.datetime.fromisoformat(candidate)
    except ValueError as exc:
        raise PublicationContractError(
            f"{label} must be an ISO timestamp with a timezone"
        ) from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise PublicationContractError(f"{label} must include a timezone")
    return parsed.astimezone(dt.timezone.utc)


def normalize_utc_timestamp(value: object, *, label: str) -> str:
    parsed = parse_aware_timestamp(value, label=label)
    timespec = "microseconds" if parsed.microsecond else "seconds"
    return parsed.isoformat(timespec=timespec).replace("+00:00", "Z")


def _safe_relative_path(value: object, *, label: str) -> PurePosixPath:
    if not isinstance(value, str) or not value.strip() or "\\" in value:
        raise PublicationContractError(f"{label} must be a safe relative path")
    relative = PurePosixPath(value)
    if relative.is_absolute() or any(part in {"", ".", ".."} for part in relative.parts):
        raise PublicationContractError(f"{label} must be a safe relative path")
    return relative


def workspace_artifact_path(
    workspace: Path | str,
    relative: object,
    *,
    require_file: bool,
) -> Path:
    """Resolve a declared artifact without following a workspace symlink."""

    root = Path(workspace).resolve()
    relative_path = _safe_relative_path(relative, label="artifact path")
    path = root.joinpath(*relative_path.parts)
    cursor = root
    for part in relative_path.parts:
        cursor = cursor / part
        if cursor.is_symlink():
            raise PublicationContractError(
                f"publication artifact path contains a symlink: {relative_path.as_posix()}"
            )
    if require_file:
        if not path.is_file():
            raise PublicationContractError(
                f"active publication artifact is missing: {relative_path.as_posix()}"
            )
    elif path.exists() and not path.is_file():
        raise PublicationContractError(
            f"publication artifact path is not a regular file: {relative_path.as_posix()}"
        )
    try:
        resolved = path.resolve(strict=require_file)
        resolved.relative_to(root)
    except (FileNotFoundError, ValueError) as exc:
        raise PublicationContractError(
            f"publication artifact escapes its workspace: {relative_path.as_posix()}"
        ) from exc
    return path


def active_artifacts(
    registry: Mapping[str, Any],
    manifest: Mapping[str, Any],
    *,
    profile: str,
) -> list[dict[str, Any]]:
    return resolve_active_artifacts(registry, manifest, profile=profile)


def _load_context(
    workspace: Path,
    *,
    skill_root: Path,
    profile: str = "live",
) -> tuple[dict[str, Any], dict[str, Any], list[dict[str, Any]]]:
    registry = load_registry(skill_root / "assets" / "artifact_registry.json")
    problems = validate_registry(registry, skill_root=skill_root)
    if problems:
        raise PublicationContractError("invalid artifact registry: " + "; ".join(problems))
    manifest_path = workspace_artifact_path(workspace, "run_manifest.json", require_file=True)
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise PublicationContractError(f"cannot read run_manifest.json: {exc}") from exc
    if not isinstance(manifest, dict):
        raise PublicationContractError("run_manifest.json must be an object")
    try:
        active = active_artifacts(registry, manifest, profile=profile)
    except ValueError as exc:
        raise PublicationContractError(str(exc)) from exc
    return registry, manifest, active


def _artifact_identity(artifact: Mapping[str, Any]) -> dict[str, str]:
    return {
        "artifact_id": str(artifact.get("artifact_id") or artifact.get("id") or ""),
        "path": str(artifact.get("path") or ""),
        "stage": str(artifact.get("stage") or ""),
        "artifact_role": str(artifact.get("artifact_role") or ""),
    }


def publication_registry_contract(
    workspace: Path | str,
    *,
    skill_root: Path | str,
    profile: str = "live",
) -> dict[str, Any]:
    workspace = Path(workspace).resolve()
    skill_root = Path(skill_root).resolve()
    registry, _manifest, active = _load_context(
        workspace,
        skill_root=skill_root,
        profile=profile,
    )
    contract = {
        "contract_version": REGISTRY_CONTRACT_VERSION,
        "profile": profile,
        "schema_version": str(registry["schema_version"]),
        "sha256": registry_hash(registry),
        "publication_bundles": sorted(
            (
                {
                    "id": str(bundle["id"]),
                    "stages": list(bundle["stages"]),
                }
                for bundle in registry.get("publication_bundles", [])
            ),
            key=lambda row: row["id"],
        ),
        "artifacts": sorted(
            (
                _artifact_identity(artifact)
                for artifact in active
                if artifact.get("path") != "forecast_seal.json"
            ),
            key=lambda row: row["path"],
        ),
    }
    validate_publication_registry_contract(contract)
    return contract


def validate_publication_registry_contract(
    value: object,
    *,
    required_profile: str | None = None,
) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise PublicationContractError("seal registry must be an object")
    unknown = sorted(set(value) - REGISTRY_CONTRACT_FIELDS)
    missing = sorted(REGISTRY_CONTRACT_FIELDS - set(value))
    if unknown:
        raise PublicationContractError("unknown seal registry field: " + ", ".join(unknown))
    if missing:
        raise PublicationContractError("missing seal registry field: " + ", ".join(missing))
    if value.get("contract_version") != REGISTRY_CONTRACT_VERSION:
        raise PublicationContractError("unsupported seal registry contract_version")
    if not isinstance(value.get("profile"), str) or not value["profile"].strip():
        raise PublicationContractError("seal registry profile must be a non-empty identifier")
    if required_profile is not None and value.get("profile") != required_profile:
        raise PublicationContractError(
            f"seal registry profile must be {required_profile}"
        )
    if not isinstance(value.get("schema_version"), str) or not value["schema_version"]:
        raise PublicationContractError("seal registry schema_version is invalid")
    if not HASH_RE.fullmatch(str(value.get("sha256") or "")):
        raise PublicationContractError("seal registry sha256 is invalid")

    bundles = value.get("publication_bundles")
    if not isinstance(bundles, list):
        raise PublicationContractError("seal registry publication_bundles must be an array")
    seen_bundles: set[str] = set()
    seen_stages: set[str] = set()
    for index, bundle in enumerate(bundles):
        if not isinstance(bundle, dict) or set(bundle) != {"id", "stages"}:
            raise PublicationContractError(f"seal registry bundle {index} is invalid")
        bundle_id = bundle.get("id")
        stages = bundle.get("stages")
        if not isinstance(bundle_id, str) or not bundle_id or bundle_id in seen_bundles:
            raise PublicationContractError(f"seal registry bundle {index} has invalid id")
        if (
            not isinstance(stages, list)
            or not stages
            or any(not isinstance(stage, str) or not stage for stage in stages)
            or len(stages) != len(set(stages))
        ):
            raise PublicationContractError(f"seal registry bundle {bundle_id} has invalid stages")
        overlap = seen_stages.intersection(stages)
        if overlap:
            raise PublicationContractError("seal registry bundle stages overlap")
        seen_bundles.add(bundle_id)
        seen_stages.update(stages)
    if seen_bundles != REQUIRED_BUNDLE_IDS:
        raise PublicationContractError("seal registry must define the three capability bundles")

    artifacts = value.get("artifacts")
    if not isinstance(artifacts, list) or not artifacts:
        raise PublicationContractError("seal registry artifacts must be a non-empty array")
    seen_paths: set[str] = set()
    seen_ids: set[str] = set()
    for index, artifact in enumerate(artifacts):
        if not isinstance(artifact, dict) or set(artifact) != ARTIFACT_IDENTITY_FIELDS:
            raise PublicationContractError(f"seal registry artifact {index} is invalid")
        for field in ("artifact_id", "stage", "artifact_role"):
            if not isinstance(artifact.get(field), str) or not artifact[field]:
                raise PublicationContractError(
                    f"seal registry artifact {index} has invalid {field}"
                )
        relative = _safe_relative_path(
            artifact.get("path"),
            label=f"seal registry artifact {index} path",
        ).as_posix()
        if relative == "forecast_seal.json":
            raise PublicationContractError("seal cannot list itself as a sealed artifact")
        if relative in seen_paths:
            raise PublicationContractError(f"duplicate seal registry artifact path: {relative}")
        if artifact["artifact_id"] in seen_ids:
            raise PublicationContractError(
                f"duplicate seal registry artifact id: {artifact['artifact_id']}"
            )
        seen_paths.add(relative)
        seen_ids.add(artifact["artifact_id"])
    missing_required = sorted(REQUIRED_SEALED_PATHS - seen_paths)
    if missing_required:
        raise PublicationContractError(
            "seal registry missing required publication artifact: "
            + ", ".join(missing_required)
        )
    return value


def artifact_record(workspace: Path, artifact: Mapping[str, Any]) -> dict[str, Any]:
    identity = _artifact_identity(artifact)
    path = workspace_artifact_path(workspace, identity["path"], require_file=True)
    sha256, size_bytes = _hash_regular_file(path)
    return {
        **identity,
        "sha256": sha256,
        "size_bytes": size_bytes,
    }


def _records_for_artifacts(
    workspace: Path,
    artifacts: Iterable[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    return sorted(
        (artifact_record(workspace, artifact) for artifact in artifacts),
        key=lambda row: row["path"],
    )


def records_hash(
    records: Iterable[Mapping[str, Any]],
    *,
    contract_version: str,
    registry_schema_version: str,
    registry_sha256: str,
    bundle_id: str | None = None,
) -> str:
    payload: dict[str, Any] = {
        "contract_version": contract_version,
        "registry_schema_version": registry_schema_version,
        "registry_sha256": registry_sha256,
        "records": sorted((dict(record) for record in records), key=lambda row: row["path"]),
    }
    if bundle_id is not None:
        payload["bundle_id"] = bundle_id
    return sha256_bytes(canonical_bytes(payload))


def publication_bundle_hashes_from_records(
    records: Iterable[Mapping[str, Any]],
    registry_contract: Mapping[str, Any],
) -> dict[str, str]:
    validate_publication_registry_contract(registry_contract)
    materialized = [dict(record) for record in records]
    result: dict[str, str] = {}
    for bundle in registry_contract["publication_bundles"]:
        stages = set(bundle["stages"])
        selected = [
            record
            for record in materialized
            if record.get("stage") in stages and record.get("artifact_role") != "receipt"
        ]
        result[bundle["id"]] = records_hash(
            selected,
            contract_version="forecast-publication-bundle/v1",
            registry_schema_version=str(registry_contract["schema_version"]),
            registry_sha256=str(registry_contract["sha256"]),
            bundle_id=bundle["id"],
        )
    return result


def publication_bundle_hashes_from_contract(
    workspace: Path | str,
    registry_contract: Mapping[str, Any],
) -> dict[str, str]:
    validate_publication_registry_contract(registry_contract)
    bundle_stages = {
        stage
        for bundle in registry_contract["publication_bundles"]
        for stage in bundle["stages"]
    }
    records = _records_for_artifacts(
        Path(workspace).resolve(),
        (
            artifact
            for artifact in registry_contract["artifacts"]
            if artifact["artifact_role"] != "receipt" and artifact["stage"] in bundle_stages
        ),
    )
    return publication_bundle_hashes_from_records(records, registry_contract)


def publication_bundle_hashes(
    workspace: Path | str,
    *,
    skill_root: Path | str,
) -> dict[str, str]:
    registry_contract = publication_registry_contract(
        workspace,
        skill_root=skill_root,
        profile="live",
    )
    return publication_bundle_hashes_from_contract(workspace, registry_contract)


def validated_input_pack_hash_from_records(
    records: Iterable[Mapping[str, Any]],
    registry_contract: Mapping[str, Any],
) -> str:
    validate_publication_registry_contract(registry_contract)
    selected = [
        dict(record)
        for record in records
        if record.get("artifact_role") != "receipt"
    ]
    return records_hash(
        selected,
        contract_version="forecast-validated-input-pack/v1",
        registry_schema_version=str(registry_contract["schema_version"]),
        registry_sha256=str(registry_contract["sha256"]),
    )


def validated_input_pack_hash_from_contract(
    workspace: Path | str,
    registry_contract: Mapping[str, Any],
) -> str:
    validate_publication_registry_contract(registry_contract)
    records = _records_for_artifacts(
        Path(workspace).resolve(),
        (
            artifact
            for artifact in registry_contract["artifacts"]
            if artifact["artifact_role"] != "receipt"
        ),
    )
    return validated_input_pack_hash_from_records(records, registry_contract)


def validated_input_pack_hash(
    workspace: Path | str,
    *,
    skill_root: Path | str,
    profile: str = "live",
) -> str:
    registry_contract = publication_registry_contract(
        workspace,
        skill_root=skill_root,
        profile=profile,
    )
    return validated_input_pack_hash_from_contract(workspace, registry_contract)


def final_pack_records_from_contract(
    workspace: Path | str,
    registry_contract: Mapping[str, Any],
) -> list[dict[str, Any]]:
    validate_publication_registry_contract(registry_contract)
    return _records_for_artifacts(
        Path(workspace).resolve(),
        registry_contract["artifacts"],
    )


def final_pack_records(
    workspace: Path | str,
    *,
    skill_root: Path | str,
) -> list[dict[str, Any]]:
    registry_contract = publication_registry_contract(
        workspace,
        skill_root=skill_root,
        profile="live",
    )
    return final_pack_records_from_contract(workspace, registry_contract)


def seal_pack_hash(seal_without_hash: Mapping[str, Any]) -> str:
    payload = dict(seal_without_hash)
    payload.pop("pack_hash", None)
    return sha256_bytes(canonical_bytes(payload))


def _require_hash(value: object, *, label: str) -> None:
    if not HASH_RE.fullmatch(str(value or "")):
        raise PublicationContractError(f"{label} must be a sha256 hash")


def validate_live_seal_structure(seal: object) -> dict[str, Any]:
    if not isinstance(seal, dict):
        raise PublicationContractError("forecast seal must be an object")
    unknown = sorted(set(seal) - SEAL_FIELDS)
    missing = sorted(SEAL_FIELDS - set(seal))
    if unknown:
        raise PublicationContractError("unknown seal field: " + ", ".join(unknown))
    if missing:
        raise PublicationContractError("missing seal field: " + ", ".join(missing))
    if seal.get("schema_version") != "forecast-seal/v1":
        raise PublicationContractError("forecast seal schema_version is invalid")
    if seal.get("seal_kind") != "live_publication" or seal.get("status") != "published":
        raise PublicationContractError("forecast seal is not a published live publication")
    for field in ("forecast_id", "run_id"):
        if not isinstance(seal.get(field), str) or not seal[field].strip():
            raise PublicationContractError(f"forecast seal {field} is required")
    parse_aware_timestamp(seal.get("frozen_at"), label="forecast seal frozen_at")
    validate_publication_registry_contract(seal.get("registry"), required_profile="live")
    bundle_hashes = seal.get("bundle_hashes")
    if not isinstance(bundle_hashes, dict) or set(bundle_hashes) != REQUIRED_BUNDLE_IDS:
        raise PublicationContractError("forecast seal bundle_hashes are invalid")
    for bundle_id, value in bundle_hashes.items():
        _require_hash(value, label=f"forecast seal {bundle_id}")
    supersedes = seal.get("supersedes")
    if supersedes is not None:
        if not isinstance(supersedes, dict) or set(supersedes) != {
            "forecast_id", "pack_hash", "frozen_at"
        }:
            raise PublicationContractError("forecast seal supersedes is invalid")
        if not isinstance(supersedes.get("forecast_id"), str) or not supersedes["forecast_id"]:
            raise PublicationContractError("forecast seal supersedes forecast_id is invalid")
        _require_hash(supersedes.get("pack_hash"), label="forecast seal supersedes pack_hash")
        parse_aware_timestamp(
            supersedes.get("frozen_at"),
            label="forecast seal supersedes frozen_at",
        )
    for field in (
        "validated_input_pack_hash",
        "snapshot_hash",
        "delivery_receipt_hash",
        "pack_hash",
    ):
        _require_hash(seal.get(field), label=f"forecast seal {field}")
    if not isinstance(seal.get("files"), list) or not seal["files"]:
        raise PublicationContractError("forecast seal files must be a non-empty array")
    return seal


def verify_file_records(workspace: Path, records: object) -> list[dict[str, Any]]:
    if not isinstance(records, list) or not records:
        raise PublicationContractError("seal files must be a non-empty array")
    verified: list[dict[str, Any]] = []
    seen_paths: set[str] = set()
    for index, record in enumerate(records):
        if not isinstance(record, dict) or set(record) != FILE_RECORD_FIELDS:
            raise PublicationContractError(f"seal file record {index} is invalid")
        for field in ("artifact_id", "stage", "artifact_role"):
            if not isinstance(record.get(field), str) or not record[field]:
                raise PublicationContractError(f"seal file record {index} has invalid {field}")
        relative = _safe_relative_path(
            record.get("path"),
            label=f"seal file record {index} path",
        ).as_posix()
        if relative in seen_paths:
            raise PublicationContractError(f"duplicate sealed path: {relative}")
        seen_paths.add(relative)
        _require_hash(record.get("sha256"), label=f"seal file record {index} sha256")
        size_bytes = record.get("size_bytes")
        if isinstance(size_bytes, bool) or not isinstance(size_bytes, int) or size_bytes < 0:
            raise PublicationContractError(f"seal file record {index} has invalid size_bytes")
        path = workspace_artifact_path(workspace, relative, require_file=True)
        sha256, current_size = _hash_regular_file(path)
        if sha256 != record["sha256"] or current_size != size_bytes:
            raise PublicationContractError(f"sealed file changed: {relative}")
        verified.append(dict(record))
    return verified


def verify_records_match_registry(
    records: Iterable[Mapping[str, Any]],
    registry_contract: Mapping[str, Any],
) -> None:
    validate_publication_registry_contract(registry_contract)
    actual = sorted(
        ({field: record.get(field) for field in ARTIFACT_IDENTITY_FIELDS} for record in records),
        key=lambda row: str(row["path"]),
    )
    expected = sorted(
        (dict(artifact) for artifact in registry_contract["artifacts"]),
        key=lambda row: row["path"],
    )
    if actual != expected:
        actual_paths = {str(row["path"]) for row in actual}
        expected_paths = {str(row["path"]) for row in expected}
        missing = sorted(expected_paths - actual_paths)
        extra = sorted(actual_paths - expected_paths)
        detail: list[str] = []
        if missing:
            detail.append("missing=" + ",".join(missing))
        if extra:
            detail.append("extra=" + ",".join(extra))
        if not detail:
            detail.append("artifact identity metadata differs")
        raise PublicationContractError("sealed file set differs from registry: " + "; ".join(detail))
