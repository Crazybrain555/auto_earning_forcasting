"""The delivery artifact inventory has one validated, profile-aware source."""

from __future__ import annotations

import copy
import importlib.util
import json
import subprocess
import sys
from pathlib import Path

import pytest


SKILL = Path(__file__).resolve().parents[1]
REGISTRY_PATH = SKILL / "assets" / "artifact_registry.json"
MODULE_PATH = SKILL / "scripts" / "artifact_registry.py"


def _load_module():
    spec = importlib.util.spec_from_file_location("forecast_artifact_registry", MODULE_PATH)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _registry() -> dict:
    return json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))


def test_repository_registry_is_valid_and_covers_core_materiality_routes():
    module = _load_module()
    registry = module.load_registry()

    assert module.validate_registry(registry, skill_root=SKILL) == []
    routes = {row["id"] for row in registry["materiality_routes"]}
    assert {"technology_ip", "operating_cycle", "internal_intangible"} <= routes

    artifacts = registry["artifacts"]
    scenario_set = next(row for row in artifacts if row["id"] == "scenario_set")
    assert scenario_set["artifact_role"] == "input"
    assert {row["requirement"] for row in artifacts} == {"core", "conditional"}
    conditional = [row for row in artifacts if row["requirement"] == "conditional"]
    assert conditional
    assert all(set(row["activation"]) == {"route_any"} for row in conditional)
    assert {row["path"] for row in artifacts if row["requirement"] == "core"} >= {
        "run_manifest.json",
        "source_manifest.json",
        "financial_fact_ledger.csv",
        "model_graph.json",
        "scenario_set.json",
        "forecast_snapshot.json",
        "model/model.xlsx",
        "report.md",
        "industry_profit_pool.csv",
    }


def test_registry_rejects_duplicate_ids_paths_missing_templates_and_unknown_fields(tmp_path):
    module = _load_module()
    registry = _registry()

    duplicate = copy.deepcopy(registry)
    duplicate["artifacts"].append(copy.deepcopy(duplicate["artifacts"][0]))
    problems = module.validate_registry(duplicate, skill_root=SKILL)
    assert any("duplicate artifact id" in item for item in problems), problems
    assert any("duplicate artifact path" in item for item in problems), problems

    missing_template = copy.deepcopy(registry)
    missing_template["artifacts"][0]["template"] = "assets/templates/not-there.json"
    problems = module.validate_registry(missing_template, skill_root=SKILL)
    assert any("template does not exist" in item for item in problems), problems

    unknown = copy.deepcopy(registry)
    unknown["artifacts"][0]["invented_flag"] = True
    problems = module.validate_registry(unknown, skill_root=SKILL)
    assert any("unknown declaration field" in item for item in problems), problems


def test_registry_rejects_invalid_or_unsafe_declarations():
    module = _load_module()
    registry = _registry()

    invalid = copy.deepcopy(registry)
    row = invalid["artifacts"][0]
    row.update({
        "path": "../outside.json",
        "requirement": "sometimes",
        "artifact_role": "mystery",
        "stage": "made_up_stage",
        "format": "binary_blob",
        "profiles": [""],
        "scaffold": "yes",
    })
    problems = module.validate_registry(invalid, skill_root=SKILL)
    for phrase in (
        "safe relative path",
        "requirement must be core or conditional",
        "invalid artifact_role",
        "invalid stage",
        "invalid format",
        "profiles values must be non-empty strings",
        "scaffold must be boolean",
    ):
        assert any(phrase in item for item in problems), (phrase, problems)


def test_profiles_are_optional_and_accept_arbitrary_nonempty_identifiers():
    module = _load_module()
    registry = _registry()

    arbitrary = copy.deepcopy(registry)
    arbitrary["artifacts"][0]["profiles"] = ["research-sandbox-v3"]
    assert module.validate_registry(arbitrary, skill_root=SKILL) == []

    unprofiled = copy.deepcopy(registry)
    for artifact in unprofiled["artifacts"]:
        artifact.pop("profiles", None)
    assert module.validate_registry(unprofiled, skill_root=SKILL) == []

    resolved = module.resolve_active_paths(
        unprofiled,
        {"run_mode": "a-runtime-mode-that-is-not-a-profile", "materiality_routes": {}},
    )
    assert "run_manifest.json" in resolved
    assert "training_state.json" in resolved


def test_multi_profile_registry_requires_explicit_caller_profile():
    module = _load_module()
    registry = _registry()

    with pytest.raises(ValueError, match="multiple artifact profiles"):
        module.resolve_active_paths(registry, {"run_mode": "historical_train"})
    with pytest.raises(ValueError, match="unknown artifact profile"):
        module.resolve_active_paths(registry, {}, profile="not-declared")

    live_paths = set(module.resolve_active_paths(registry, {}, profile="live"))
    trainer_paths = set(module.resolve_active_paths(registry, {}, profile="trainer"))
    assert "training_state.json" not in live_paths
    assert "training_state.json" in trainer_paths


def test_conditional_artifacts_resolve_only_from_materiality_routes():
    module = _load_module()
    registry = _registry()

    base = {
        "run_mode": "live_forecast",
        "analysis_primitives": ["unit-volume-price-cost"],
        "materiality_routes": {},
    }
    base_paths = set(module.resolve_active_paths(registry, base, profile="live"))
    assert "run_manifest.json" in base_paths
    assert "technical_evidence_records.jsonl" not in base_paths
    assert "operating_cycle_register.csv" not in base_paths
    assert "internal_intangible_investment.json" not in base_paths

    technology = copy.deepcopy(base)
    technology["materiality_routes"] = {"technology_ip": {"status": "material"}}
    technology_paths = set(module.resolve_active_paths(registry, technology, profile="live"))
    assert {
        "technical_evidence_records.jsonl",
        "technology_commercialization_register.csv",
    } <= technology_paths

    primitive_only = copy.deepcopy(base)
    primitive_only["analysis_primitives"] = [
        "cycle-state-regime",
        "program-stage-conversion",
    ]
    primitive_paths = set(module.resolve_active_paths(registry, primitive_only, profile="live"))
    assert "operating_cycle_register.csv" not in primitive_paths
    assert "technical_evidence_records.jsonl" not in primitive_paths

    cycle = copy.deepcopy(base)
    cycle["materiality_routes"] = {"operating_cycle": "active"}
    cycle_paths = set(module.resolve_active_paths(registry, cycle, profile="live"))
    assert {"industry_profit_pool.csv", "operating_cycle_register.csv"} <= cycle_paths

    intangible = copy.deepcopy(base)
    intangible["materiality_routes"] = ["internal_intangible"]
    intangible_paths = set(module.resolve_active_paths(registry, intangible, profile="live"))
    assert "internal_intangible_investment.json" in intangible_paths


def test_explicit_profile_resolution_keeps_training_artifacts_out_of_live_runs():
    module = _load_module()
    registry = _registry()

    live_paths = set(module.resolve_active_paths(registry, {}, profile="live"))
    trainer_paths = set(module.resolve_active_paths(registry, {}, profile="trainer"))

    assert "training_state.json" not in live_paths
    assert "training_state.json" in trainer_paths


def test_conditional_declaration_must_name_a_known_route():
    module = _load_module()
    registry = _registry()
    conditional = next(
        row for row in registry["artifacts"] if row["requirement"] == "conditional"
    )

    missing_activation = copy.deepcopy(registry)
    target = next(row for row in missing_activation["artifacts"] if row["id"] == conditional["id"])
    target["activation"] = {}
    problems = module.validate_registry(missing_activation, skill_root=SKILL)
    assert any("conditional artifact requires activation" in item for item in problems), problems

    unknown_route = copy.deepcopy(registry)
    target = next(row for row in unknown_route["artifacts"] if row["id"] == conditional["id"])
    target["activation"] = {"route_any": ["not_declared"]}
    problems = module.validate_registry(unknown_route, skill_root=SKILL)
    assert any("unknown materiality route" in item for item in problems), problems


def test_manifest_materiality_routes_reject_unknown_ids_and_invalid_statuses():
    module = _load_module()
    registry = _registry()

    unknown = {"materiality_routes": {"technlogy_ip": "material"}}
    problems = module.validate_manifest_routes(registry, unknown)
    assert any("unknown materiality route" in item for item in problems), problems
    with pytest.raises(ValueError, match="unknown materiality route"):
        module.resolve_active_paths(registry, unknown, profile="live")

    invalid_status = {"materiality_routes": {"technology_ip": "maybe"}}
    problems = module.validate_manifest_routes(registry, invalid_status)
    assert any("invalid materiality route status" in item for item in problems), problems

    valid = {
        "materiality_routes": {
            "technology_ip": {"status": "material", "reason": "main-line technology"},
            "operating_cycle": "not_applicable",
            "internal_intangible": False,
        }
    }
    assert module.validate_manifest_routes(registry, valid) == []


def test_required_artifacts_is_a_diagnostic_generated_view_not_an_authority():
    module = _load_module()
    registry = _registry()
    manifest = json.loads(
        (SKILL / "assets/templates/run_manifest_template.json").read_text(encoding="utf-8")
    )

    assert module.required_artifact_view_diagnostics(registry, manifest, profile="live") == []

    manifest["materiality_routes"] = {"technology_ip": "material"}
    active_paths = set(module.resolve_active_paths(registry, manifest, profile="live"))
    assert {
        "technical_evidence_records.jsonl",
        "technology_commercialization_register.csv",
    } <= active_paths
    diagnostics = module.required_artifact_view_diagnostics(registry, manifest, profile="live")
    assert any("stale generated view" in item for item in diagnostics), diagnostics

    manifest["required_artifacts"].append(manifest["required_artifacts"][0])
    diagnostics = module.required_artifact_view_diagnostics(registry, manifest, profile="live")
    assert any("duplicate required_artifacts" in item for item in diagnostics), diagnostics


def test_live_and_trainer_scaffolds_materialize_profile_specific_views(tmp_path):
    module = _load_module()
    registry = _registry()
    scaffold = SKILL / "scripts/scaffold_delivery.py"

    for mode, should_have_training_state in (
        ("live_forecast", False),
        ("historical_train", True),
    ):
        workspace = tmp_path / mode
        result = subprocess.run(
            [
                sys.executable,
                str(scaffold),
                "--workspace",
                str(workspace),
                "--entity",
                "TEST",
                "--as-of",
                "2026-07-20",
                "--mode",
                mode,
            ],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0, result.stdout + result.stderr
        manifest = json.loads((workspace / "run_manifest.json").read_text(encoding="utf-8"))
        selected_profile = "trainer" if mode == "historical_train" else "live"
        assert manifest["required_artifacts"] == module.resolve_active_paths(
            registry, manifest, profile=selected_profile
        )
        assert len(manifest["required_artifacts"]) == len(set(manifest["required_artifacts"]))
        assert (workspace / "training_state.json").exists() is should_have_training_state
        assert ("training_state.json" in manifest["required_artifacts"]) is should_have_training_state
        assert "forecast_seal.json" in manifest["required_artifacts"]


def test_registry_view_after_route_change_diagnoses_duplicates(tmp_path):
    module = _load_module()
    registry = _registry()
    workspace = tmp_path / "route-change"
    scaffold = subprocess.run(
        [
            sys.executable,
            str(SKILL / "scripts/scaffold_delivery.py"),
            "--workspace",
            str(workspace),
            "--entity",
            "TEST",
            "--as-of",
            "2026-07-20",
        ],
        capture_output=True,
        text=True,
    )
    assert scaffold.returncode == 0, scaffold.stdout + scaffold.stderr

    manifest_path = workspace / "run_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["materiality_routes"] = {"technology_ip": "material"}
    manifest["required_artifacts"].append(manifest["required_artifacts"][0])
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

    diagnostics = module.required_artifact_view_diagnostics(
        registry, manifest, profile="live"
    )
    assert any("stale generated view" in item for item in diagnostics), diagnostics
    assert any("duplicate required_artifacts" in item for item in diagnostics), diagnostics
