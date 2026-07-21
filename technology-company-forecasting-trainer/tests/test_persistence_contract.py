"""Value-investing persistence claims must be equations and evidence, not prose rows."""
from __future__ import annotations

import importlib.util
from pathlib import Path


SKILL = Path(__file__).resolve().parents[1]
MODULE_PATH = SKILL / "scripts" / "validate_persistence_contract.py"
SPEC = importlib.util.spec_from_file_location("validate_persistence_contract", MODULE_PATH)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
SPEC.loader.exec_module(MODULE)


KNOWN_NODES = {"ai_units", "competitive_supply", "asp_break", "sga_cost"}
KNOWN_SOURCES = {"S0", "S6"}
INDEPENDENT_SOURCES = {"S6"}
SCENARIOS = {"bear", "base", "bull"}


def valid_persistence() -> dict:
    return {
        "mean_reversion": {
            "status": "accepted",
            "object": "normalized_operating_margin",
            "unit": "ratio",
            "reference_class": "same qualification stage, capital intensity and cycle state",
            "reference_class_source_ids": ["S0", "S6"],
            "target_median": 0.18,
            "target_low": 0.12,
            "target_high": 0.24,
            "sample_selection_limits": "Survivors and firms without comparable qualification gates are excluded.",
            "company_departure": "Five-year customer qualification delays competitive capacity response.",
            "speed_driver_node_ids": ["competitive_supply"],
            "fade_horizon_periods": 5,
            "falsification_node_ids": ["asp_break"],
            "scenario_ids": ["bear", "base", "bull"],
        },
        "cost_behavior": [
            {
                "cost_line": "selling_general_and_administrative",
                "status": "accepted",
                "materiality": "high",
                "activity_driver_node_id": "ai_units",
                "activity_unit": "unit",
                "elasticity_up": 0.55,
                "elasticity_down": 0.25,
                "adjustment_lag_periods": 2,
                "committed_resource_floor": 30.0,
                "floor_unit": "USDm",
                "exit_or_adjustment_cost": 5.0,
                "estimation_method": "company history plus named scenario sensitivity",
                "source_ids": ["S0", "S6"],
                "scenario_ids": ["bear", "base", "bull"],
                "notes": "Down-state elasticity reflects severance and committed facilities.",
            }
        ],
    }


def validate(payload: dict) -> list[str]:
    return MODULE.validate_persistence_analysis(
        payload,
        known_node_ids=KNOWN_NODES,
        main_line_relevant_node_ids={"ai_units", "competitive_supply"},
        falsification_node_ids={"asp_break"},
        known_source_ids=KNOWN_SOURCES,
        independent_source_ids=INDEPENDENT_SOURCES,
        scenario_ids=SCENARIOS,
        strict=True,
    )


def test_complete_conditional_mean_reversion_and_cost_asymmetry_pass():
    assert validate(valid_persistence()) == []


def test_mean_reversion_requires_distribution_evidence_lineage_and_causal_speed():
    payload = valid_persistence()
    row = payload["mean_reversion"]
    row["target_low"] = 0.30
    row["reference_class_source_ids"] = ["BAD"]
    row["speed_driver_node_ids"] = ["unrelated"]
    errors = " ".join(validate(payload)).lower()
    assert "distribution" in errors
    assert "unknown source" in errors
    assert "speed_driver" in errors


def test_reference_class_authority_is_reviewed_not_reduced_to_an_independent_source_quota():
    payload = valid_persistence()
    payload["mean_reversion"]["reference_class_source_ids"] = ["S0"]
    assert validate(payload) == []


def test_fade_horizon_is_an_optional_model_output_not_a_fixed_numeric_gate():
    payload = valid_persistence()
    payload["mean_reversion"].pop("fade_horizon_periods")
    assert validate(payload) == []


def test_unresolved_reference_class_is_preserved_for_independent_review():
    payload = valid_persistence()
    row = payload["mean_reversion"]
    row.update({
        "status": "human_required",
        "reference_class": None,
        "reference_class_source_ids": [],
        "target_median": None,
        "target_low": None,
        "target_high": None,
        "sample_selection_limits": None,
        "company_departure": None,
        "limitations": "No economically comparable public cohort is observable at the cutoff.",
    })
    assert validate(payload) == []


def test_persistence_does_not_force_an_unrelated_cost_schedule():
    payload = valid_persistence()
    payload["cost_behavior"] = []
    assert validate(payload) == []


def test_unresolved_material_cost_behavior_is_preserved_without_fabricated_elasticities():
    payload = valid_persistence()
    row = payload["cost_behavior"][0]
    row.update({
        "status": "human_required",
        "activity_driver_node_id": None,
        "elasticity_up": None,
        "elasticity_down": None,
        "adjustment_lag_periods": None,
        "committed_resource_floor": None,
        "exit_or_adjustment_cost": None,
        "source_ids": [],
        "scenario_ids": [],
        "limitations": "The disclosure does not separate committed from adjustable resources.",
    })
    assert validate(payload) == []


def test_cost_behavior_cannot_be_a_prose_only_shell():
    payload = valid_persistence()
    row = payload["cost_behavior"][0]
    for field in (
        "elasticity_up",
        "elasticity_down",
        "adjustment_lag_periods",
        "committed_resource_floor",
        "exit_or_adjustment_cost",
    ):
        row[field] = None
    errors = " ".join(validate(payload)).lower()
    assert "elasticity_up" in errors
    assert "adjustment_lag_periods" in errors
    assert "committed_resource_floor" in errors


def test_cost_rows_bind_known_driver_sources_and_scenarios():
    payload = valid_persistence()
    row = payload["cost_behavior"][0]
    row["activity_driver_node_id"] = "unknown"
    row["source_ids"] = ["BAD"]
    row["scenario_ids"] = ["fantasy"]
    errors = " ".join(validate(payload)).lower()
    assert "activity_driver_node_id" in errors
    assert "unknown source" in errors
    assert "unknown scenario" in errors


def test_moat_rows_bind_sources_nodes_fade_value_and_kill_trigger():
    rows = [
        {
            "dimension": "customer_stickiness_switching_costs",
            "status": "accepted",
            "evidence_source_ids": "S0;S6",
            "independent_clusters": "2",
            "claim": "Qualification creates a measured replacement delay.",
            "driver_node_ids": "competitive_supply",
            "forecast_permission": "margin persistence through FY2030",
            "roic_or_cash_effect": "normalized ROIC +3pp",
            "reinvestment_runway": "5 years",
            "competitor_response": "Rival qualified capacity arrives in FY2031.",
            "downside_or_falsification": "kill if replacement qualification falls below 12 months",
            "fade_schedule_link": "value_creation.fade.schedule",
            "valuation_sensitivity": "2-year faster fade lowers intrinsic value 18%",
            "monitor_driver_node_ids": "asp_break",
            "monitor_or_kill_trigger": "asp_break <= 0.80 by FY2028",
        }
    ]
    assert MODULE.validate_moat_rows(
        rows,
        known_source_ids=KNOWN_SOURCES,
        independent_source_ids=INDEPENDENT_SOURCES,
        known_node_ids=KNOWN_NODES,
        monitor_node_ids={"asp_break"},
    ) == []


def test_moat_unknown_lineage_and_links_fail_without_prose_length_scoring():
    rows = [
        {
            "dimension": "customer_stickiness_switching_costs",
            "status": "accepted",
            "evidence_source_ids": "BAD",
            "independent_clusters": "2",
            "claim": "good moat",
            "driver_node_ids": "unknown",
            "forecast_permission": "persistent",
            "roic_or_cash_effect": "strong",
            "reinvestment_runway": "long",
            "competitor_response": "competition",
            "downside_or_falsification": "bad things",
            "fade_schedule_link": "",
            "valuation_sensitivity": "important",
            "monitor_driver_node_ids": "unknown",
            "monitor_or_kill_trigger": "watch",
        }
    ]
    errors = " ".join(
        MODULE.validate_moat_rows(
            rows,
            known_source_ids=KNOWN_SOURCES,
            independent_source_ids=INDEPENDENT_SOURCES,
            known_node_ids=KNOWN_NODES,
            monitor_node_ids={"asp_break"},
        )
    ).lower()
    assert "unknown source" in errors
    assert "unknown driver" in errors
    assert "monitor" in errors


def test_concise_moat_claim_with_executable_links_is_not_rejected_by_word_or_digit_count():
    rows = [{
        "dimension": "switching_cost",
        "status": "accepted",
        "evidence_source_ids": "S6",
        "claim": "qualified replacement delay",
        "driver_node_ids": "competitive_supply",
        "forecast_permission": "bounded persistence",
        "roic_or_cash_effect": "linked sensitivity",
        "reinvestment_runway": "fade schedule",
        "competitor_response": "qualification response",
        "downside_or_falsification": "linked falsifier",
        "fade_schedule_link": "value_creation.fade.schedule",
        "valuation_sensitivity": "linked valuation case",
        "monitor_driver_node_ids": "asp_break",
        "monitor_or_kill_trigger": "linked monitor",
    }]
    assert MODULE.validate_moat_rows(
        rows,
        known_source_ids=KNOWN_SOURCES,
        independent_source_ids=INDEPENDENT_SOURCES,
        known_node_ids=KNOWN_NODES,
        monitor_node_ids={"asp_break"},
    ) == []


def test_moat_source_sufficiency_is_not_an_independent_source_count_gate():
    rows = [{
        "dimension": "switching_cost",
        "status": "accepted",
        "evidence_source_ids": "S0",
        "claim": "qualification delay",
        "driver_node_ids": "competitive_supply",
        "forecast_permission": "bounded persistence",
        "roic_or_cash_effect": "linked sensitivity",
        "reinvestment_runway": "fade schedule",
        "competitor_response": "qualification response",
        "downside_or_falsification": "linked falsifier",
        "fade_schedule_link": "value_creation.fade.schedule",
        "valuation_sensitivity": "linked valuation case",
        "monitor_driver_node_ids": "asp_break",
        "monitor_or_kill_trigger": "linked monitor",
    }]
    assert MODULE.validate_moat_rows(
        rows,
        known_source_ids=KNOWN_SOURCES,
        independent_source_ids=INDEPENDENT_SOURCES,
        known_node_ids=KNOWN_NODES,
        monitor_node_ids={"asp_break"},
    ) == []
