import importlib.util
import json
import re
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _build_system(output_parent: Path) -> None:
    result = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts/build_skill_system.py"),
            "--trainer-skill-root",
            str(ROOT),
            "--output-parent",
            str(output_parent),
            "--self-test",
        ],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stdout + result.stderr


def test_production_workspace_has_one_current_evidence_state(tmp_path):
    _build_system(tmp_path)
    live = tmp_path / "technology-company-profit-forecasting"
    registry = json.loads((live / "assets/artifact_registry.json").read_text())
    profile = json.loads((live / "assets/profile.json").read_text())

    assert "allowed_modes" not in profile
    assert all("profiles" not in artifact for artifact in registry["artifacts"])
    assert all(artifact["path"] != "mode_config.json" for artifact in registry["artifacts"])
    assert not (live / "assets/templates/mode_config_template.json").exists()

    workspace = tmp_path / "workspace"
    result = subprocess.run(
        [
            sys.executable,
            str(live / "scripts/scaffold_delivery.py"),
            "--workspace",
            str(workspace),
            "--entity",
            "TEST",
        ],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    manifest = json.loads((workspace / "run_manifest.json").read_text())
    snapshot = json.loads((workspace / "forecast_snapshot.json").read_text())
    assert "run_mode" not in manifest
    assert "baseline_skill_version" not in manifest
    assert "run_mode" not in snapshot
    assert not (workspace / "mode_config.json").exists()

    rejected = subprocess.run(
        [
            sys.executable,
            str(live / "scripts/scaffold_delivery.py"),
            "--workspace",
            str(tmp_path / "forbidden-mode"),
            "--entity",
            "TEST",
            "--mode",
            "historical_train",
        ],
        capture_output=True,
        text=True,
    )
    assert rejected.returncode != 0
    assert "unrecognized arguments" in (rejected.stdout + rejected.stderr)


def test_production_source_records_keep_audit_dates_not_training_eligibility(tmp_path):
    _build_system(tmp_path)
    live = tmp_path / "technology-company-profit-forecasting"
    schema = json.loads((live / "assets/schemas/source_record.schema.json").read_text())
    template = json.loads((live / "assets/templates/source_manifest_template.json").read_text())
    source = template["sources"][0]

    assert "as_of_valid" not in schema["properties"]
    assert "source_time_status" not in source
    assert "forecast_permission" not in source
    assert {"published_at", "available_at", "retrieved_at", "version_at"} <= set(source)


def test_production_surface_cannot_express_training_authority(tmp_path):
    _build_system(tmp_path)
    package_names = (
        "technology-company-profit-forecasting",
        "company-evidence-research",
        "company-operating-modeling",
        "company-financial-forecasting",
        "forecasting-system-contracts",
    )
    forbidden = re.compile(
        r"technology-company-forecasting-trainer|sealed_historical|historical_train"
        r"|post[_ -]?cutoff|time[_ -]?boundary|training_state|target actuals",
        re.I,
    )
    violations = []
    for package_name in package_names:
        package = tmp_path / package_name
        for path in sorted(package.rglob("*")):
            if path.suffix.lower() not in {".md", ".json", ".yaml", ".yml", ".py"}:
                continue
            match = forbidden.search(path.read_text(encoding="utf-8"))
            if match:
                violations.append(f"{path.relative_to(tmp_path)}: {match.group(0)}")
    assert not violations, "; ".join(violations)


def test_accounting_basis_effective_after_workspace_creation_is_not_rejected():
    module = _load_module("delivery_boundary_v3", ROOT / "scripts/validate_delivery.py")
    manifest = {
        "as_of": "2026-07-20T00:00:00Z",
        "currency": "USD",
        "accounting_basis": {
            "forecast_basis_id": "US-NEW",
            "historical_basis_ids": ["US-NEW"],
            "bases": [
                {
                    "basis_id": "US-NEW",
                    "framework": "US_GAAP",
                    "jurisdiction": "US",
                    "version": "newly effective guidance",
                    "effective_at": "2026-07-21T00:00:00Z",
                    "presentation_currency": "USD",
                    "major_policy_choices": [
                        {
                            "policy_id": "revenue",
                            "policy_area": "revenue_recognition",
                            "choice": "adopt the guidance for applicable forecast periods",
                            "source_ids": ["SRC-NEW"],
                        }
                    ],
                }
            ],
            "comparability_bridges": [],
        },
    }
    problems = module.validate_accounting_basis_contract(
        manifest,
        snapshot={"accounting_basis_id": "US-NEW"},
        financial_fact_rows=[],
        source_ids={"SRC-NEW"},
    )
    assert not any("model snapshot" in problem or "manifest.as_of" in problem for problem in problems)


def test_manifest_phase_contract_matches_method_registry():
    method = json.loads((ROOT / "assets/method_system.json").read_text())
    template = json.loads((ROOT / "assets/templates/run_manifest_template.json").read_text())
    schema = json.loads((ROOT / "assets/schemas/run_manifest.schema.json").read_text())
    expected = [stage["id"] for stage in method["stages"]]
    phase_schema = schema["properties"]["phase_status"]

    assert list(template["phase_status"]) == expected
    assert phase_schema["required"] == expected
    assert list(phase_schema["properties"]) == expected
