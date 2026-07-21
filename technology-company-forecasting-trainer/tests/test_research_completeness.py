"""CLI surface for the causal research-readiness contract."""
from __future__ import annotations

import csv
import json
import subprocess
import sys
from pathlib import Path


SKILL = Path(__file__).resolve().parents[1]
VALIDATOR = SKILL / "scripts/validate_research_completeness.py"


def test_empty_collection_cannot_pass_by_declaring_large_depth_counts(tmp_path):
    (tmp_path / "run_manifest.json").write_text(json.dumps({
        "contract_version": "2.0",
        "as_of": "2026-07-18T23:59:59Z",
        "readiness_target": "research-grade",
        "research_depth_thresholds": {
            "minimum_accepted_words": 0,
            "minimum_substantial_sources": 0,
        },
    }), encoding="utf-8")
    (tmp_path / "source_manifest.json").write_text(
        json.dumps({"sources": []}), encoding="utf-8"
    )
    (tmp_path / "model_graph.json").write_text(json.dumps({
        "nodes": [], "equations": [],
        "main_line": {
            "carrier_node_ids": [], "target_node_ids": [],
            "falsification_ids": [], "competitor_response_node_ids": [],
        },
    }), encoding="utf-8")
    (tmp_path / "source_independence_map.csv").write_text(
        "source_id,cluster_id,root_original_source_id\n", encoding="utf-8"
    )
    (tmp_path / "data_series_register.csv").write_text(
        "series_id,status\n", encoding="utf-8"
    )
    (tmp_path / "material_assumption_support.csv").write_text(
        "assumption_id,driver_link\n", encoding="utf-8"
    )

    result = subprocess.run(
        [sys.executable, str(VALIDATOR), "--workspace", str(tmp_path), "--strict"],
        capture_output=True,
        text=True,
    )

    assert result.returncode != 0
    output = (result.stdout + result.stderr).lower()
    assert "main-line" in output
    assert "research_quality_review.json" in output
    assert "accepted research corpus" not in output
    assert "minimum_substantial" not in output


def test_method_states_that_validator_cannot_certify_subjective_quality():
    text = (
        SKILL / "references/research-completeness-and-company-quality.md"
    ).read_text(encoding="utf-8").lower()
    for phrase in (
        "not sufficient because",
        "independent research-quality review",
        "no minimum finding count",
        "counts may describe a package",
        "proven predictive accuracy",
    ):
        assert phrase in text


def test_material_technology_file_is_validated_only_when_route_is_active(tmp_path):
    workspace = tmp_path / "route-gated-research"
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

    technology_path = workspace / "technology_commercialization_register.csv"
    with technology_path.open(encoding="utf-8-sig", newline="") as handle:
        fieldnames = next(csv.reader(handle))
    row = dict.fromkeys(fieldnames, "")
    row.update({
        "technology_or_product": "main-line accelerator",
        "materiality": "high",
        "current_stage": "qualification",
        "paper_source_ids": "PAPER-1",
        "allowed_model_use": "base_parameter",
    })
    with technology_path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerow(row)

    def run_validator() -> str:
        result = subprocess.run(
            [sys.executable, str(VALIDATOR), "--workspace", str(workspace), "--strict"],
            capture_output=True,
            text=True,
        )
        return (result.stdout + result.stderr).lower()

    inactive_output = run_validator()
    assert "missing technical evidence record for main-line accelerator / paper-1" not in inactive_output

    manifest_path = workspace / "run_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["materiality_routes"] = {"technology_ip": "material"}
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

    active_output = run_validator()
    assert "missing technical evidence record for main-line accelerator / paper-1" in active_output
