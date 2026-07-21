"""Research readiness follows thesis evidence, not collection-volume quotas."""
from __future__ import annotations

import csv
import hashlib
import json
import sys
from pathlib import Path

SKILL = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SKILL / "scripts"))

from validate_research_completeness import validate_research_workspace


DATA_HEADER = [
    "series_id", "metric_name", "metric_construct_id", "observation_value",
    "observation_type", "available_at", "vintage_id", "revision_of_series_id",
    "classification_version", "input_series_ids", "source_id",
    "original_source_id", "independence_cluster", "measurement_method_id",
    "published_at", "retrieved_at", "vintage_at", "revision_at",
    "period_start", "period_end", "frequency", "unit", "currency",
    "metric_definition", "entity_scope", "product_scope", "geography_scope",
    "population_coverage", "transformation", "revision_policy", "lag_days",
    "known_bias", "cross_check_series_ids", "cross_check_result",
    "cross_check_bridge_json", "allowed_model_use", "driver_node_ids",
    "conclusion_critical", "status", "notes",
]

SUPPORT_HEADER = [
    "assumption_id", "claim", "driver_link", "test_delta",
    "revenue_impact_pct", "profit_impact_pct", "changes_conclusion",
    "support_status", "source_ids", "lanes", "falsification_trigger",
    "horizon", "scenario", "notes",
]


def _write_csv(path: Path, header: list[str], rows: list[dict[str, object]]) -> None:
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=header)
        writer.writeheader()
        writer.writerows(rows)


def _sha256(path: Path) -> str:
    return "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()


def _source(source_id: str, publisher: str, team: str, method: str, cluster: str) -> dict:
    return {
        "source_id": source_id,
        "source_type": "direct_measurement",
        "origin_record_kind": "original_measurement_observation",
        "epistemic_class": "independent_external_observation",
        "publisher": publisher,
        "authors": [team],
        "root_original_source_id": source_id,
        "derived_from_source_id": None,
        "common_origin": False,
        "independence_cluster": cluster,
        "measurement_method_id": method,
        "authority": "third_party",
        "independence": "independent",
        "directness": "direct",
        "published_at": "2026-07-01T00:00:00Z",
        "version_at": "2026-07-01T00:00:00Z",
        "decision_status": "accepted",
        # Deliberately tiny.  Depth/count metadata may be diagnostic, but may
        # not veto a close, directly measured thesis chain.
        "document_depth": "summary_only",
        "word_count": 1,
    }


def _series(
    series_id: str,
    source_id: str,
    root: str,
    cluster: str,
    method: str,
    cross_check: str,
) -> dict[str, object]:
    return {
        "series_id": series_id,
        "metric_name": "accepted end demand",
        "metric_construct_id": "accepted_customer_units_flow",
        "observation_value": "100",
        "observation_type": "flow",
        "available_at": "2026-07-15T00:00:00Z",
        "vintage_id": f"{series_id}-v1",
        "revision_of_series_id": "none",
        "classification_version": "2026Q2-v1",
        "input_series_ids": "none",
        "source_id": source_id,
        "original_source_id": root,
        "independence_cluster": cluster,
        "measurement_method_id": method,
        "published_at": "2026-07-01T00:00:00Z",
        "retrieved_at": "2026-07-18T00:00:00Z",
        "vintage_at": "2026-07-01T00:00:00Z",
        "revision_at": "2026-07-01T00:00:00Z",
        "period_start": "2026-04-01",
        "period_end": "2026-06-30",
        "frequency": "quarterly",
        "unit": "unit",
        "currency": "N/A",
        "metric_definition": "units accepted by the end customer",
        "entity_scope": "addressable market",
        "product_scope": "named product family",
        "geography_scope": "global",
        "population_coverage": "declared sampling frame",
        "transformation": "none",
        "revision_policy": "retain every vintage",
        "lag_days": "15",
        "known_bias": "declared small-customer undercoverage",
        "cross_check_series_ids": cross_check,
        "cross_check_result": "same construct and period; residual investigated",
        "cross_check_bridge_json": "",
        "allowed_model_use": "base_parameter",
        "driver_node_ids": "demand",
        "conclusion_critical": "true",
        "status": "accepted",
        "notes": "",
    }


def _write_review(workspace: Path, *, reviewer_id: str = "reviewer:independent") -> None:
    frozen = {
        name: _sha256(workspace / name)
        for name in (
            "source_manifest.json", "source_independence_map.csv",
            "forward_signal_cards.csv", "model_graph.json",
            "scenario_set.json",
            "data_series_register.csv", "material_assumption_support.csv",
            "claim_ledger.jsonl",
        )
    }
    review = {
        "schema_version": "research-quality-review/v1",
        "review_id": "research-review://TEST/20260718/1",
        "reviewed_at": "2026-07-18T20:00:00Z",
        "builder_id": "builder:case",
        "reviewer_id": reviewer_id,
        "independent_of_builder": True,
        "orchestration_receipt": {
            "assurance_boundary": "orchestration_receipt_only_not_cryptographic_identity",
            "receipt_id": "orchestration-receipt://research-fixture",
            "orchestrator": "pytest-fixture",
            "reviewer_session_id": "session:research-reviewer",
            "reviewer_task_id": "task:research-quality-review",
            "builder_session_id": "session:case-builder",
            "frozen_inputs_delivered_at": "2026-07-18T19:50:00Z",
            "review_started_at": "2026-07-18T19:52:00Z",
            "initial_conclusion_at": "2026-07-18T19:58:00Z",
            "review_completed_at": "2026-07-18T20:00:00Z",
            "receipt_issued_at": "2026-07-18T20:01:00Z",
            "builder_rebuttal": {"status": "not_provided", "provided_at": None},
        },
        "frozen_artifacts": frozen,
        "principal_contradiction": {
            "carrier_node_ids": ["demand"],
            "falsification_node_ids": ["demand_break"],
            "rival_hypothesis": "reported sell-in is channel inventory rather than end demand",
            "judgment": "adequate",
            "reasoning": "Two definition-compatible measurements distinguish sell-through from sell-in.",
            "source_ids": ["S1", "S2"],
        },
        "claim_authority_judgments": [],
        # The list is open-ended and routed by materiality.  It is not a fixed
        # topic checklist or a minimum finding count.
        "material_judgments": [{
            "judgment_id": "J-CYCLE",
            "question": "Could channel stock explain the observed demand signal?",
            "status": "resolved",
            "reasoning": "The independent acceptance series measures the same end-demand construct.",
            "source_ids": ["S1", "S2"],
            "model_node_ids": ["demand"],
            "forecast_consequence": "Base demand remains admitted; inventory divergence is monitored.",
            "readiness_effect": "none",
        }],
        "overall": {
            "research_sufficiency": "adequate",
            "readiness_cap": "research-grade",
            "rationale": "The thesis carrier and serious rival are measured on compatible bases.",
            "unresolved_material_disagreements": [],
        },
    }
    (workspace / "research_quality_review.json").write_text(
        json.dumps(review, indent=2), encoding="utf-8"
    )


def _valid_workspace(tmp_path: Path) -> Path:
    manifest = {
        "contract_version": "2.0",
        "run_id": "run://TEST/20260718/v2",
        "entity": "TEST",
        "as_of": "2026-07-18T23:59:59Z",
        "run_mode": "live_forecast",
        "readiness_target": "research-grade",
        "readiness_result": "research-grade",
        # Legacy collection-volume settings must have no gate effect.
        "research_depth_thresholds": {
            "minimum_accepted_words": 999999,
            "minimum_substantial_sources": 999,
            "minimum_substantial_official_sources": 999,
            "minimum_company_quality_dimensions": 999,
            "minimum_material_technology_rows": 999,
        },
    }
    (tmp_path / "run_manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    sources = [
        _source("S1", "Measurement Agency A", "Census Team A", "acceptance_census", "C1"),
        _source("S2", "Industry Body B", "Panel Team B", "sell_through_panel", "C2"),
    ]
    (tmp_path / "source_manifest.json").write_text(
        json.dumps({"as_of": manifest["as_of"], "sources": sources}), encoding="utf-8"
    )
    graph = {
        "schema_version": "2.0",
        "graph_id": "graph://TEST/20260718/v2",
        "as_of": manifest["as_of"],
        "nodes": [
            {"id": "demand", "kind": "observable", "unit": "unit", "data_series_ids": ["D1", "D2"]},
            {"id": "revenue", "kind": "derived", "unit": "USD", "financial_role": "revenue"},
            {"id": "demand_break", "kind": "falsification", "unit": "ratio"},
        ],
        "equations": [{"id": "eq:revenue", "output": "revenue", "operation": "identity", "inputs": ["demand"]}],
        "main_line": {
            "carrier_node_ids": ["demand"], "target_node_ids": ["revenue"],
            "falsification_ids": ["demand_break"], "competitor_response_node_ids": [],
        },
    }
    (tmp_path / "model_graph.json").write_text(json.dumps(graph), encoding="utf-8")
    (tmp_path / "scenario_set.json").write_text(json.dumps({
        "schema_version": "2.0",
        "scenarios": [{
            "id": "central_operating_path",
            "role": "reference",
            "probability": 1.0,
            "shocks": [],
            "profit_chain_periods": [],
            "narrative": "reference path for the research-contract fixture",
        }],
    }), encoding="utf-8")
    _write_csv(tmp_path / "data_series_register.csv", DATA_HEADER, [
        _series("D1", "S1", "S1", "C1", "acceptance_census", "D2"),
        _series("D2", "S2", "S2", "C2", "sell_through_panel", "D1"),
    ])
    with (tmp_path / "source_independence_map.csv").open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow([
            "source_id", "cluster_id", "root_original_source_id", "derived_from_source_id",
            "relationship", "common_origin", "publisher", "authors",
            "measurement_method_id", "independence_basis", "notes",
        ])
        writer.writerows([
            ["S1", "C1", "S1", "", "root", "false", "Measurement Agency A", "Census Team A", "acceptance_census", "direct census", ""],
            ["S2", "C2", "S2", "", "root", "false", "Industry Body B", "Panel Team B", "sell_through_panel", "independent panel", ""],
        ])
    _write_csv(
        tmp_path / "forward_signal_cards.csv",
        ["signal_id", "source_id", "claim_ids"],
        [],
    )
    _write_csv(tmp_path / "material_assumption_support.csv", SUPPORT_HEADER, [{
        "assumption_id": "A1", "claim": "accepted customer units persist",
        "driver_link": "demand", "test_delta": "demand -10%",
        "revenue_impact_pct": "10", "profit_impact_pct": "18",
        "changes_conclusion": "yes", "support_status": "corroborated",
        "source_ids": "S1;S2", "lanes": "", "falsification_trigger": "demand_break",
        "horizon": "FY+2", "scenario": "central_operating_path", "notes": "",
    }])
    (tmp_path / "claim_ledger.jsonl").write_text("", encoding="utf-8")
    _write_review(tmp_path)
    return tmp_path


def test_small_high_quality_pack_passes_even_when_legacy_counts_are_impossible(tmp_path):
    workspace = _valid_workspace(tmp_path)

    result = validate_research_workspace(workspace, strict=True)

    assert result["passed"], result["errors"]
    assert result["diagnostics"]["accepted_source_count"] == 2
    assert "research_depth_thresholds" not in result["hard_gate_inputs"]


def test_many_hollow_sources_cannot_fake_main_line_support(tmp_path):
    workspace = _valid_workspace(tmp_path)
    payload = json.loads((workspace / "source_manifest.json").read_text(encoding="utf-8"))
    payload["sources"] = [
        _source(f"S{i}", "Wrapper Publisher", "Shared Team", "copied_press_release", "same-root")
        for i in range(30)
    ]
    (workspace / "source_manifest.json").write_text(json.dumps(payload), encoding="utf-8")
    # A large collection with no conclusion-critical measurement remains empty
    # evidence.  Update the review hash so the failure cannot be attributed
    # merely to the frozen-artifact check.
    _write_csv(workspace / "data_series_register.csv", DATA_HEADER, [])
    _write_review(workspace)

    result = validate_research_workspace(workspace, strict=True)

    assert not result["passed"]
    assert "main-line" in " ".join(result["errors"]).lower() or "data series" in " ".join(result["errors"]).lower()


def test_independent_review_is_bound_to_frozen_inputs(tmp_path):
    workspace = _valid_workspace(tmp_path)
    graph = json.loads((workspace / "model_graph.json").read_text(encoding="utf-8"))
    graph["nodes"][0]["unit"] = "thousand_units"
    (workspace / "model_graph.json").write_text(json.dumps(graph), encoding="utf-8")

    result = validate_research_workspace(workspace, strict=True)

    assert not result["passed"]
    assert "frozen" in " ".join(result["errors"]).lower()


def test_forward_signal_and_provenance_changes_stale_the_independent_review(tmp_path):
    for name in ("forward_signal_cards.csv", "source_independence_map.csv"):
        workspace = tmp_path / name.replace(".", "-")
        workspace.mkdir()
        _valid_workspace(workspace)
        path = workspace / name
        path.write_text(path.read_text(encoding="utf-8-sig") + "\n", encoding="utf-8-sig")

        result = validate_research_workspace(workspace, strict=True)

        assert not result["passed"], (name, result)
        assert "frozen" in " ".join(result["errors"]).lower(), (name, result)


def test_reviewer_role_label_cannot_claim_independence_from_itself(tmp_path):
    workspace = _valid_workspace(tmp_path)
    _write_review(workspace, reviewer_id="builder:case")

    result = validate_research_workspace(workspace, strict=True)

    assert not result["passed"]
    assert "reviewer" in " ".join(result["errors"]).lower()


def test_research_review_requires_orchestration_receipt_beyond_role_labels(tmp_path):
    workspace = _valid_workspace(tmp_path)
    path = workspace / "research_quality_review.json"
    review = json.loads(path.read_text(encoding="utf-8"))
    del review["orchestration_receipt"]
    path.write_text(json.dumps(review), encoding="utf-8")

    result = validate_research_workspace(workspace, strict=True)

    assert not result["passed"]
    assert "orchestration_receipt" in " ".join(result["errors"])


def test_research_review_cannot_start_before_frozen_inputs_are_delivered(tmp_path):
    workspace = _valid_workspace(tmp_path)
    path = workspace / "research_quality_review.json"
    review = json.loads(path.read_text(encoding="utf-8"))
    receipt = review["orchestration_receipt"]
    receipt["frozen_inputs_delivered_at"] = "2026-07-18T19:55:00Z"
    receipt["review_started_at"] = "2026-07-18T19:52:00Z"
    path.write_text(json.dumps(review), encoding="utf-8")

    result = validate_research_workspace(workspace, strict=True)

    assert not result["passed"]
    assert "frozen inputs" in " ".join(result["errors"]).lower()
