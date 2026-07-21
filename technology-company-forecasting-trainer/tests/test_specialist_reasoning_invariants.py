"""Cross-company specialist invariants exposed by the first blind evaluation.

These are capability contracts, not issuer fixtures or output-count targets.
They keep semantic judgment in the SOP while making capability ownership and
accounting bases unambiguous to every generated installation.
"""

from __future__ import annotations

import json
import re
from pathlib import Path


TRAINER = Path(__file__).resolve().parents[1]
CANONICAL = TRAINER / "assets" / "skill_system"


def _json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _invariants() -> dict:
    return _json(CANONICAL / "contracts" / "protocol_manifest.json")[
        "reasoning_invariants"
    ]


def _capability(name: str) -> dict:
    return _json(CANONICAL / "skills" / name / "assets" / "capability.json")


def test_evidence_normalization_preserves_the_source_proposition_boundary():
    contract = _invariants()["proposition_fidelity"]

    assert contract["owner"] == "company-evidence-research"
    assert {
        "direction",
        "magnitude",
        "period",
        "scope",
        "causal_relation",
    }.issubset(contract["protected_dimensions"])
    assert contract["normalization_permission"] == "representation_only"
    assert contract["missing_dimension_policy"] == "remain_unknown"
    assert contract["conflict_policy"] == "preserve_only_source_asserted_positions"
    assert contract["scenario_authorship"] == "forbidden"
    assert "proposition_fidelity" in _capability("company-evidence-research")[
        "reasoning_invariant_refs"
    ]


def test_mutually_exclusive_operating_paths_share_one_executable_output_contract():
    contract = _invariants()["alternative_path_closure"]

    assert contract["owner"] == "company-operating-modeling"
    assert contract["scope"] == "each_mutually_exclusive_construction_set"
    assert set(contract["execution_contract"]) == {
        "compile_each_path_to_one_declared_canonical_output_node",
        "select_exactly_one_path_for_execution",
        "selected_path_reaches_operating_profit_exactly_once",
        "unselected_paths_do_not_execute",
    }
    assert contract["handoff_boundary"] == "operating_profit"
    assert set(contract["downstream_execution_domains"]) == {
        "integrated_statements",
        "share_denominators",
        "joint_scenario_probabilities",
        "competitive_fade",
        "valuation",
    }
    assert "alternative_path_closure" in _capability("company-operating-modeling")[
        "reasoning_invariant_refs"
    ]


def test_share_denominators_are_three_distinct_economic_constructs():
    contract = _invariants()["share_basis_separation"]
    share_types = contract["share_types"]

    assert contract["owner"] == "company-financial-forecasting"
    assert set(share_types) == {
        "ending_basic_share_stock",
        "period_weighted_average_eps_shares",
        "valuation_date_fully_diluted_shares",
    }
    assert share_types["ending_basic_share_stock"]["time_semantics"] == "point_in_time_stock"
    assert share_types["period_weighted_average_eps_shares"]["time_semantics"] == "period_average"
    assert set(share_types["period_weighted_average_eps_shares"]["variants"]) == {
        "basic",
        "diluted",
    }
    assert share_types["valuation_date_fully_diluted_shares"]["time_semantics"] == "valuation_date_stock"
    assert len({item["permitted_use"] for item in share_types.values()}) == 3
    assert "share_basis_separation" in _capability("company-financial-forecasting")[
        "reasoning_invariant_refs"
    ]


def test_advanced_analysis_is_case_routed_and_presentation_is_proportionate():
    invariants = _invariants()
    routing = invariants["conditional_analysis_routing"]
    presentation = invariants["minimum_sufficient_presentation"]

    assert {
        "joint_scenarios_and_probabilities",
        "competitive_fade",
        "secondary_valuation_method",
        "technology_commercialization_gates",
    }.issubset(routing["conditional_modules"])
    assert set(routing["activation_reasons"]) == {
        "explicitly_requested",
        "material_to_requested_profit_output",
        "needed_to_discriminate_a_named_rival",
    }
    assert routing["inactive_module_policy"] == "omit_without_placeholder"
    assert presentation["machine_handoff"] == "complete_under_shared_schema"
    assert presentation["human_output"] == "minimum_sufficient_for_requested_decision"
    assert presentation["blocker_policy"] == "author_once_then_reference"
    assert presentation["originating_blocker_id_field"] == "blockers[].blocker_id"
    assert presentation["downstream_blocker_reference_field"] == "input_refs[]"

    handoff_schema = _json(
        CANONICAL / "contracts" / "schemas" / "capability_handoff.schema.json"
    )
    blocker_properties = handoff_schema["properties"]["blockers"]["items"][
        "properties"
    ]
    assert blocker_properties["blocker_id"]["type"] == "string"


def test_financial_references_do_not_roll_a_period_average_as_a_closing_stock():
    references = "\n".join(
        (TRAINER / "references" / name).read_text(encoding="utf-8")
        for name in (
            "model-mechanical-integrity.md",
            "core-output-and-valuation.md",
            "valuation-and-market-expectations.md",
        )
    ).lower()

    invalid_equations = (
        r"closing\s+basic\s*/\s*diluted\s+shares\s*=",
        r"basic\s+and\s+diluted\s+shares\s*:\s*opening.*=\s*closing",
    )
    assert not any(re.search(pattern, references) for pattern in invalid_equations)
