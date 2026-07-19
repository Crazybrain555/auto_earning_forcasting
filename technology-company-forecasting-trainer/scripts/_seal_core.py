#!/usr/bin/env python3
"""Shared seal integrity core for freeze_training_forecast and score_training_forecast.

The seal covers every regular file in the case workspace EXCEPT the excluded
subtrees (`evaluation/`, `actuals_vault/`) and `forecast_seal.json` itself.
Those two subtrees are the only places post-seal artifacts may be written, so
verification can demand an exact file-set match everywhere else: a file that
was modified, removed, OR ADDED after sealing fails verification, and the
pack hash is recomputed from both the stored records and the current disk
state so a hand-edited seal cannot pass.

Deliberately lighter than a full pre-registered score contract: integrity is
enforced by hashes; judgment about whether a score is "good enough" stays
with the human loop (没大问题就 push).
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

EXCLUDED_SUBDIRS = {"evaluation", "actuals_vault"}


class SealError(ValueError):
    pass


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def is_excluded(relative: Path) -> bool:
    return bool(set(relative.parts[:-1]) & EXCLUDED_SUBDIRS) or relative.name == "forecast_seal.json"


def canonical_records(workspace: Path) -> list[dict]:
    workspace = workspace.resolve()
    if not workspace.is_dir():
        raise SealError(f"workspace does not exist: {workspace}")
    records = []
    for path in sorted(workspace.rglob("*")):
        relative = path.relative_to(workspace)
        if is_excluded(relative):
            continue
        if path.is_symlink():
            raise SealError(f"sealed workspace may not contain symlinks: {relative.as_posix()}")
        if not path.is_file():
            continue
        records.append({
            "path": relative.as_posix(),
            "sha256": sha256_file(path),
            "size_bytes": path.stat().st_size,
        })
    return records


def pack_hash(records: list[dict]) -> str:
    payload = json.dumps(records, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return "sha256:" + hashlib.sha256(payload).hexdigest()


def build_seal(workspace: Path, sealed_at: str, extra: dict | None = None) -> dict:
    records = canonical_records(workspace)
    if not any(r["path"] == "forecast_snapshot.json" for r in records):
        raise SealError("forecast_snapshot.json must exist before sealing")
    seal = {
        "status": "sealed_before_actuals",
        "sealed_at": sealed_at,
        "pack_hash": pack_hash(records),
        "excluded_subdirs": sorted(EXCLUDED_SUBDIRS),
        "files": records,
    }
    if extra:
        seal.update(extra)
    return seal


def verify_seal(workspace: Path) -> dict:
    """Full verification; raises SealError on any integrity breach."""
    workspace = workspace.resolve()
    seal_path = workspace / "forecast_seal.json"
    if not seal_path.is_file():
        raise SealError("forecast_seal.json is missing")
    try:
        seal = json.loads(seal_path.read_text(encoding="utf-8"))
    except Exception as exc:
        raise SealError(f"cannot read forecast_seal.json: {exc}")
    stored = seal.get("files")
    stored_pack = seal.get("pack_hash")
    if not isinstance(stored, list) or not stored:
        raise SealError("seal has no file records")
    # 1) the stored records must reproduce the stored pack hash (forged-seal check)
    if pack_hash(stored) != stored_pack:
        raise SealError("seal pack_hash does not match its own file records (seal was edited)")
    # 2) the disk file set must match the sealed set exactly (modified/removed/ADDED)
    current = canonical_records(workspace)
    stored_by_path = {r["path"]: r for r in stored}
    current_by_path = {r["path"]: r for r in current}
    missing = sorted(set(stored_by_path) - set(current_by_path))
    unlisted = sorted(set(current_by_path) - set(stored_by_path))
    if missing or unlisted:
        parts = []
        if missing:
            parts.append("missing=" + ",".join(missing))
        if unlisted:
            parts.append("added=" + ",".join(unlisted))
        raise SealError("sealed file set changed: " + "; ".join(parts))
    changed = sorted(p for p in stored_by_path
                     if stored_by_path[p]["sha256"] != current_by_path[p]["sha256"])
    if changed:
        raise SealError("sealed files changed: " + ", ".join(changed))
    # 3) belt and braces: current disk state reproduces the pack hash
    if pack_hash(current) != stored_pack:
        raise SealError("current workspace does not reproduce the sealed pack_hash")
    return seal


def assert_outside_sealed_area(workspace: Path, path: Path) -> None:
    """Actuals and other post-seal inputs must not sit in the sealed tree."""
    workspace = workspace.resolve()
    resolved = path.resolve()
    try:
        relative = resolved.relative_to(workspace)
    except ValueError:
        return  # outside the workspace entirely - fine
    if not is_excluded(relative):
        raise SealError(
            f"{relative.as_posix()} sits inside the sealed area; put post-seal artifacts "
            f"outside the workspace or under {sorted(EXCLUDED_SUBDIRS)}"
        )
