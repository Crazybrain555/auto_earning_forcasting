from __future__ import annotations

import importlib.util
import json
import shutil
import sys
from pathlib import Path

import pytest


SKILL = Path(__file__).resolve().parents[1]
SCRIPTS = SKILL / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))


def _load(name: str):
    path = SKILL / "scripts" / f"{name}.py"
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


contract = _load("publication_contract")
publisher = _load("publish_live_forecast")


def _workspace(tmp_path: Path, *, run_mode: str = "live_forecast", security: str = "TEST") -> Path:
    workspace = tmp_path / f"{security}-case"
    workspace.mkdir(parents=True)
    version = tmp_path.name
    registry = json.loads((SKILL / "assets/artifact_registry.json").read_text(encoding="utf-8"))
    manifest = {
        "contract_version": "2.0",
        "run_id": f"run://technology/{security}/{version}/v2",
        "entity": f"{security} Inc.",
        "security": security,
        "run_mode": run_mode,
        "materiality_routes": {},
    }
    snapshot = {
        "contract_version": "2.0",
        "forecast_id": f"fcst://technology/{security}/{version}/v2",
        "run_mode": run_mode,
    }
    (workspace / "run_manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    (workspace / "forecast_snapshot.json").write_text(json.dumps(snapshot), encoding="utf-8")
    for artifact in contract.active_artifacts(registry, manifest, profile="live"):
        path = workspace / artifact["path"]
        if path.exists() or artifact["path"] == "forecast_seal.json":
            continue
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("{}\n" if artifact["format"] in {"json", "jsonl"} else "fixture\n", encoding="utf-8")
    return workspace


def _validator_for(skill_root: Path):
    def passing_validator(workspace: Path, _validator: Path) -> None:
        fingerprint = contract.validated_input_pack_hash(
            workspace,
            skill_root=skill_root,
        )
        (workspace / "delivery_validation.json").write_text(
            json.dumps({
                "passed": True,
                "strict": True,
                "errors": 0,
                "warnings": 0,
                "validated_input_pack_hash": fingerprint,
                "checks": [],
            }),
            encoding="utf-8",
        )

    return passing_validator


_passing_validator = _validator_for(SKILL)


def _changed_registry_skill(tmp_path: Path) -> Path:
    changed = tmp_path / "changed-skill"
    shutil.copytree(SKILL / "assets", changed / "assets")
    registry_path = changed / "assets" / "artifact_registry.json"
    registry = json.loads(registry_path.read_text(encoding="utf-8"))
    registry["materiality_routes"][0]["description"] += " Changed in a later release."
    registry_path.write_text(json.dumps(registry), encoding="utf-8")
    return changed


def _rewrite_seal(workspace: Path, mutator) -> dict:
    path = workspace / "forecast_seal.json"
    seal = json.loads(path.read_text(encoding="utf-8"))
    mutator(seal)
    seal["pack_hash"] = contract.seal_pack_hash(seal)
    path.write_text(json.dumps(seal), encoding="utf-8")
    return seal


def test_bundle_membership_is_registry_stage_driven_and_receipts_do_not_change_it(tmp_path):
    workspace = _workspace(tmp_path)
    before = contract.publication_bundle_hashes(workspace, skill_root=SKILL)
    (workspace / "delivery_validation.json").write_text('{"changed":true}', encoding="utf-8")
    (workspace / "README.md").write_text("not a registry artifact", encoding="utf-8")
    assert contract.publication_bundle_hashes(workspace, skill_root=SKILL) == before

    manifest_path = workspace / "run_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["materiality_routes"] = {"technology_ip": "material"}
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    for name in ("technical_evidence_records.jsonl", "technology_commercialization_register.csv"):
        (workspace / name).write_text("routed\n", encoding="utf-8")
    after = contract.publication_bundle_hashes(workspace, skill_root=SKILL)
    assert after["evidence_bundle"] != before["evidence_bundle"]
    assert after["operating_model_bundle"] != before["operating_model_bundle"]
    assert after["financial_forecast_bundle"] == before["financial_forecast_bundle"]


def test_successful_publication_commits_one_immutable_verified_seal(tmp_path):
    workspace = _workspace(tmp_path)
    seal = publisher.publish(
        workspace,
        skill_root=SKILL,
        validator_runner=_passing_validator,
        frozen_at="2026-07-21T12:00:00Z",
    )
    assert seal["status"] == "published"
    assert (workspace / "forecast_seal.json").is_file()
    assert publisher.verify(workspace, skill_root=SKILL)["pack_hash"] == seal["pack_hash"]
    snapshot = json.loads((workspace / "forecast_snapshot.json").read_text(encoding="utf-8"))
    assert snapshot["publication"]["frozen_at"] == "2026-07-21T12:00:00Z"
    assert set(snapshot["publication"]["bundle_hashes"]) == {
        "evidence_bundle", "operating_model_bundle", "financial_forecast_bundle"
    }
    with pytest.raises(publisher.PublicationError, match="already published"):
        publisher.publish(workspace, skill_root=SKILL, validator_runner=_passing_validator)


def test_failed_validation_restores_draft_and_never_commits_seal(tmp_path):
    workspace = _workspace(tmp_path)
    original_snapshot = (workspace / "forecast_snapshot.json").read_bytes()

    def fail_validation(workspace: Path, _validator: Path) -> None:
        (workspace / "delivery_validation.json").write_text(
            json.dumps({"passed": False, "strict": True, "errors": 1}), encoding="utf-8"
        )

    with pytest.raises(publisher.PublicationError, match="strict delivery validation failed"):
        publisher.publish(workspace, skill_root=SKILL, validator_runner=fail_validation)
    assert not (workspace / "forecast_seal.json").exists()
    assert (workspace / "forecast_snapshot.json").read_bytes() == original_snapshot


def test_drift_after_validation_aborts_before_seal(tmp_path):
    workspace = _workspace(tmp_path)

    def drift(workspace: Path, validator: Path) -> None:
        _passing_validator(workspace, validator)
        with (workspace / "model_graph.json").open("a", encoding="utf-8") as handle:
            handle.write("drift")

    with pytest.raises(publisher.PublicationError, match="changed during validation"):
        publisher.publish(workspace, skill_root=SKILL, validator_runner=drift)
    assert not (workspace / "forecast_seal.json").exists()


def test_supersedes_is_verified(tmp_path):
    prior = _workspace(tmp_path / "prior", security="TEST")
    prior_seal = publisher.publish(
        prior, skill_root=SKILL, validator_runner=_passing_validator,
        frozen_at="2026-07-21T10:00:00Z",
    )
    current = _workspace(tmp_path / "current", security="TEST")
    current_seal = publisher.publish(
        current, skill_root=SKILL, validator_runner=_passing_validator,
        supersedes_workspace=prior,
        frozen_at="2026-07-21T12:00:00Z",
    )
    assert current_seal["supersedes"]["forecast_id"] == prior_seal["forecast_id"]
    assert current_seal["supersedes"]["pack_hash"] == prior_seal["pack_hash"]

def test_prior_seal_remains_verifiable_and_supersedable_after_registry_upgrade(tmp_path):
    prior = _workspace(tmp_path / "prior", security="TEST")
    prior_seal = publisher.publish(
        prior,
        skill_root=SKILL,
        validator_runner=_passing_validator,
        frozen_at="2026-07-21T10:00:00Z",
    )
    changed_skill = _changed_registry_skill(tmp_path)

    assert publisher.verify(prior, skill_root=changed_skill)["pack_hash"] == prior_seal["pack_hash"]

    current = _workspace(tmp_path / "current", security="TEST")
    current_seal = publisher.publish(
        current,
        skill_root=changed_skill,
        validator_runner=_validator_for(changed_skill),
        supersedes_workspace=prior,
        frozen_at="2026-07-21T12:00:00Z",
    )
    assert current_seal["supersedes"]["pack_hash"] == prior_seal["pack_hash"]


def test_validated_input_hash_binds_registry_content(tmp_path):
    workspace = _workspace(tmp_path)
    changed_skill = _changed_registry_skill(tmp_path)

    assert contract.validated_input_pack_hash(
        workspace,
        skill_root=SKILL,
    ) != contract.validated_input_pack_hash(
        workspace,
        skill_root=changed_skill,
    )


def test_bundle_hashes_bind_registry_content(tmp_path):
    workspace = _workspace(tmp_path)
    changed_skill = _changed_registry_skill(tmp_path)

    assert contract.publication_bundle_hashes(
        workspace,
        skill_root=SKILL,
    ) != contract.publication_bundle_hashes(
        workspace,
        skill_root=changed_skill,
    )


def test_publish_rejects_naive_freeze_timestamp(tmp_path):
    workspace = _workspace(tmp_path)

    with pytest.raises(publisher.PublicationError, match="timezone"):
        publisher.publish(
            workspace,
            skill_root=SKILL,
            validator_runner=_passing_validator,
            frozen_at="2026-07-21T12:00:00",
        )


def test_supersedes_compares_instants_not_iso_strings(tmp_path):
    prior = _workspace(tmp_path / "prior", security="TEST")
    publisher.publish(
        prior,
        skill_root=SKILL,
        validator_runner=_passing_validator,
        frozen_at="2026-07-21T10:00:00-04:00",
    )
    current = _workspace(tmp_path / "current", security="TEST")

    with pytest.raises(publisher.PublicationError, match="freeze after"):
        publisher.publish(
            current,
            skill_root=SKILL,
            validator_runner=_passing_validator,
            supersedes_workspace=prior,
            frozen_at="2026-07-21T12:00:00Z",
        )


def test_publication_rejects_symlinked_artifact_even_when_content_matches(tmp_path):
    workspace = _workspace(tmp_path)
    report = workspace / "report.md"
    outside = tmp_path / "outside-report.md"
    outside.write_bytes(report.read_bytes())
    report.unlink()
    report.symlink_to(outside)

    with pytest.raises(contract.PublicationContractError, match="symlink"):
        contract.validated_input_pack_hash(workspace, skill_root=SKILL)


def test_backup_failure_after_lock_always_releases_lock(tmp_path, monkeypatch):
    workspace = _workspace(tmp_path)

    def fail_backup(*_args, **_kwargs):
        raise OSError("backup failure")

    monkeypatch.setattr(publisher, "_receipt_backups", fail_backup)
    with pytest.raises(Exception, match="backup failure"):
        publisher.publish(
            workspace,
            skill_root=SKILL,
            validator_runner=_passing_validator,
        )
    assert not (workspace / ".publish.lock").exists()


def test_rollback_failure_cannot_strand_publication_lock(tmp_path, monkeypatch):
    workspace = _workspace(tmp_path)

    def fail_validation(_workspace: Path, _validator: Path) -> None:
        raise RuntimeError("validation failure")

    def fail_restore(*_args, **_kwargs):
        raise OSError("restore failure")

    monkeypatch.setattr(publisher, "_restore", fail_restore)
    with pytest.raises(OSError, match="restore failure"):
        publisher.publish(
            workspace,
            skill_root=SKILL,
            validator_runner=fail_validation,
        )
    assert not (workspace / ".publish.lock").exists()


def test_verify_rejects_seal_with_omitted_active_file(tmp_path):
    workspace = _workspace(tmp_path)
    publisher.publish(workspace, skill_root=SKILL, validator_runner=_passing_validator)
    _rewrite_seal(
        workspace,
        lambda seal: seal.__setitem__(
            "files", [row for row in seal["files"] if row["path"] != "report.md"]
        ),
    )

    with pytest.raises(publisher.PublicationError, match="file set"):
        publisher.verify(workspace, skill_root=SKILL)


def test_verify_rejects_duplicate_sealed_path(tmp_path):
    workspace = _workspace(tmp_path)
    publisher.publish(workspace, skill_root=SKILL, validator_runner=_passing_validator)

    def duplicate_report(seal):
        report = next(row for row in seal["files"] if row["path"] == "report.md")
        seal["files"].append(dict(report))

    _rewrite_seal(workspace, duplicate_report)
    with pytest.raises(publisher.PublicationError, match="duplicate sealed path"):
        publisher.verify(workspace, skill_root=SKILL)


@pytest.mark.parametrize(
    "field",
    ["validated_input_pack_hash", "snapshot_hash", "delivery_receipt_hash"],
)
def test_verify_recomputes_declared_pack_and_file_hashes(tmp_path, field):
    workspace = _workspace(tmp_path)
    publisher.publish(workspace, skill_root=SKILL, validator_runner=_passing_validator)
    _rewrite_seal(
        workspace,
        lambda seal: seal.__setitem__(field, "sha256:" + "0" * 64),
    )

    with pytest.raises(publisher.PublicationError, match="hash"):
        publisher.verify(workspace, skill_root=SKILL)


def test_verify_rejects_unknown_seal_fields(tmp_path):
    workspace = _workspace(tmp_path)
    publisher.publish(workspace, skill_root=SKILL, validator_runner=_passing_validator)
    _rewrite_seal(workspace, lambda seal: seal.__setitem__("invented", True))

    with pytest.raises(publisher.PublicationError, match="unknown seal field"):
        publisher.verify(workspace, skill_root=SKILL)


def test_verify_requires_identity_snapshot_and_receipt_in_frozen_registry(tmp_path):
    workspace = _workspace(tmp_path)
    publisher.publish(workspace, skill_root=SKILL, validator_runner=_passing_validator)

    def remove_snapshot_from_contract(seal):
        seal["registry"]["artifacts"] = [
            row
            for row in seal["registry"]["artifacts"]
            if row["path"] != "forecast_snapshot.json"
        ]
        seal["files"] = [
            row for row in seal["files"] if row["path"] != "forecast_snapshot.json"
        ]

    _rewrite_seal(workspace, remove_snapshot_from_contract)
    with pytest.raises(publisher.PublicationError, match="required publication artifact"):
        publisher.verify(workspace, skill_root=SKILL)
