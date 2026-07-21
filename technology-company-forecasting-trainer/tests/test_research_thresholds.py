"""Collection-volume settings are not research-readiness controls."""
from __future__ import annotations

import json
import importlib.util
from pathlib import Path


SKILL = Path(__file__).resolve().parents[1]


DELIVERY_SPEC = importlib.util.spec_from_file_location(
    "delivery_scenario_presence_test", SKILL / "scripts/validate_delivery.py"
)
DELIVERY = importlib.util.module_from_spec(DELIVERY_SPEC)
assert DELIVERY_SPEC and DELIVERY_SPEC.loader
DELIVERY_SPEC.loader.exec_module(DELIVERY)

FORWARD_SPEC = importlib.util.spec_from_file_location(
    "forward_evidence_anchor_test", SKILL / "scripts/validate_forward_evidence_workspace.py"
)
FORWARD = importlib.util.module_from_spec(FORWARD_SPEC)
assert FORWARD_SPEC and FORWARD_SPEC.loader
FORWARD_SPEC.loader.exec_module(FORWARD)


def test_run_manifest_has_no_research_depth_count_thresholds():
    manifest = json.loads(
        (SKILL / "assets/templates/run_manifest_template.json").read_text(encoding="utf-8")
    )
    assert "research_depth_thresholds" not in manifest
    assert "research_depth_override_reason" not in manifest


def test_delivery_rubric_uses_causal_invariants_not_source_or_word_floors():
    rubric = json.loads(
        (SKILL / "assets/templates/delivery_quality_rubric.json").read_text(encoding="utf-8")
    )
    forbidden = {
        "minimum_official_sources",
        "minimum_accepted_research_words",
        "minimum_substantial_sources",
        "minimum_historical_filing_periods",
    }
    assert not forbidden & set(rubric)
    assert "definition-compatible main-line measurements" in rubric["hard_research_invariants"]


def test_optional_research_templates_do_not_prepopulate_topic_or_dimension_quotas():
    for name in (
        "research_coverage_matrix_template.csv",
        "company_quality_moat_template.csv",
        "technology_commercialization_template.csv",
    ):
        lines = [
            line for line in (SKILL / "assets/templates" / name).read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]
        assert len(lines) == 1, f"{name} prepopulates a universal row taxonomy"


def test_independent_review_template_is_open_ended_and_count_free():
    review = json.loads(
        (SKILL / "assets/templates/research_quality_review_template.json").read_text(encoding="utf-8")
    )
    assert review["material_judgments"] == []
    assert review["claim_authority_judgments"] == []
    assert not any("minimum" in key or "count" in key for key in review)
    receipt = review["orchestration_receipt"]
    assert receipt["assurance_boundary"] == (
        "orchestration_receipt_only_not_cryptographic_identity"
    )
    assert receipt["builder_rebuttal"]["status"] == "not_provided"
    assert set(review["frozen_artifacts"]) == {
        "source_manifest.json",
        "source_independence_map.csv",
        "forward_signal_cards.csv",
        "model_graph.json",
        "scenario_set.json",
        "data_series_register.csv",
        "material_assumption_support.csv",
        "claim_ledger.jsonl",
    }


def test_scenario_contract_requires_an_authored_path_not_a_universal_rival_count():
    schema = json.loads(
        (SKILL / "assets/schemas/scenario_set.schema.json").read_text(encoding="utf-8")
    )
    assert schema["properties"]["scenarios"].get("minItems") == 1

    validate_presence = getattr(DELIVERY, "validate_scenario_collection_presence", None)
    assert validate_presence is not None
    assert validate_presence([
        {"id": "base", "probability": 1.0, "shocks": []},
    ]) == []
    assert validate_presence([])

    snapshot_schema = json.loads(
        (SKILL / "assets/schemas/forecast_snapshot.schema.json").read_text(
            encoding="utf-8"
        )
    )
    assert snapshot_schema["properties"]["scenario_probabilities"]["minProperties"] == 1
    snapshot_template = json.loads(
        (SKILL / "assets/templates/forecast_snapshot_template.json").read_text(
            encoding="utf-8"
        )
    )
    valuation = snapshot_template["valuation_summary"]
    assert "reference_scenario_id" in valuation
    assert "fair_value_by_scenario_id" in valuation
    assert "not_valued_scenario_ids" in valuation
    assert "valuation_completeness" in valuation
    assert not {"bear", "base", "bull"} & set(valuation)


def test_base_anchor_uses_typed_directness_not_a_source_family_whitelist():
    validate_anchor = getattr(FORWARD, "validate_base_anchor_permissions", None)
    assert validate_anchor is not None
    novel_family_signal = [{
        "signal_id": "F1",
        "source_id": "S1",
        "source_family": "customer-accepted-invoice-ledger",
        "evidence_role": "fact_anchor",
        "claim_ids": "C1",
        "model_driver": "accepted_units",
    }]
    claim = {
        "claim_id": "C1",
        "claim_type": "reported_fact",
        "proposition_scope": "current_observed_state",
        "source_ids": ["S1"],
        "evidence_links": [{
            "source_id": "S1",
            "relation": "support",
            "evidence_function": "direct_anchor",
            "observation_ids": ["O1"],
        }],
        "allowed_use": "base_parameter",
        "driver_node_ids": ["accepted_units"],
        "status": "accepted",
    }
    source = {
        "source_id": "S1",
        "source_type": "unseen_measurement_format",
        "origin_record_kind": "original_measurement_observation",
        "epistemic_class": "independent_external_observation",
        "authority": "third_party",
        "independence": "independent",
        "directness": "direct",
        "root_original_source_id": "S1",
        "derived_from_source_id": None,
        "common_origin": False,
        "measurement_method_id": "accepted-invoice-method",
        "independence_cluster": "accepted-invoice-cluster",
        "publisher": "Independent Invoice Ledger",
        "authors": ["Ledger Measurement Team"],
        "content_hash": "sha256:" + "c" * 64,
        "location": "https://example.test/accepted-invoices",
        "role": "operating_measurement",
    }
    observation = {
        "series_id": "O1", "metric_construct_id": "accepted_units",
        "observation_value": "100", "observation_type": "count",
        "available_at": "2026-07-15T00:00:00Z", "vintage_id": "O1-v1",
        "source_id": "S1", "original_source_id": "S1",
        "measurement_method_id": "accepted-invoice-method",
        "period_start": "2026-04-01", "period_end": "2026-06-30",
        "frequency": "quarterly", "unit": "units", "currency": "N/A",
        "entity_scope": "named customers", "product_scope": "named product",
        "geography_scope": "global", "population_coverage": "accepted invoice ledger",
        "allowed_model_use": "base_parameter", "driver_node_ids": "accepted_units",
        "status": "accepted",
    }
    review = {
        "claim_id": "C1", "authority_sufficiency": "adequate",
        "permitted_use": "base_parameter", "reviewed_source_ids": ["S1"],
        "reviewed_source_epistemic_classes": {
            "S1": "independent_external_observation"
        },
        "reviewed_source_origin_record_kinds": {
            "S1": "original_measurement_observation"
        },
        "reviewed_observation_bindings": {
            "O1": {
                **DELIVERY.external_observation_review_binding(observation, source),
                "classification_rationale": "Reviewed the original ledger measurement and locator.",
            }
        },
        "rationale": "Independent review accepts the bounded measurement.",
    }
    assert validate_anchor(
        novel_family_signal,
        {"S1": source},
        {"C1": claim},
        {"C1": review},
        {"O1": observation},
    ) == []
    assert validate_anchor(
        novel_family_signal,
        {"S1": {
            "source_id": "S1",
            "source_type": "expert_interpretation",
            "origin_record_kind": "expert_or_analyst_interpretation",
            "epistemic_class": "expert_or_analyst_opinion",
            "authority": "third_party",
            "independence": "independent",
            "directness": "proxy",
            "role": "assumption_support",
        }},
        {"C1": claim},
        {},
        {},
    )
