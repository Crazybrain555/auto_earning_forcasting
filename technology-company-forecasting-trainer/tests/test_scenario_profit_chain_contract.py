"""Named scenarios must recompute one joint, auditable reported-profit chain."""

from __future__ import annotations

import copy
import importlib.util
import json
from pathlib import Path


SKILL = Path(__file__).resolve().parents[1]
MODULE_PATH = SKILL / "scripts" / "validate_delivery.py"
SPEC = importlib.util.spec_from_file_location("delivery_scenario_profit_chain", MODULE_PATH)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
SPEC.loader.exec_module(MODULE)


CHAIN_FIELDS = (
    "revenue",
    "operating_costs_and_expenses",
    "operating_profit",
    "nonoperating_income_expense_net",
    "pretax_profit",
    "tax_expense",
    "net_income",
    "net_income_attributable_to_noncontrolling_interests",
    "net_income_attributable",
)


def _chain_row(
    scenario: str,
    period: str,
    revenue: float,
    operating_profit: float,
    pretax_profit: float,
    tax_expense: float,
    nci_net_income: float,
    *,
    shock_nodes: list[str],
) -> dict:
    consolidated_net_income = pretax_profit - tax_expense
    attributable_net_income = consolidated_net_income - nci_net_income
    row_number = {"FY2027": 12, "FY2028": 13}[period]
    columns = dict(zip(CHAIN_FIELDS, "BCDEFGHIJ"))
    return {
        "period": period,
        "revenue": revenue,
        "operating_costs_and_expenses": revenue - operating_profit,
        "operating_profit": operating_profit,
        "nonoperating_income_expense_net": pretax_profit - operating_profit,
        "pretax_profit": pretax_profit,
        "tax_expense": tax_expense,
        "net_income": consolidated_net_income,
        "net_income_attributable_to_noncontrolling_interests": nci_net_income,
        "net_income_attributable": attributable_net_income,
        "model_cells": {
            field: f"Scenario_PnL!{columns[field]}{row_number}"
            for field in CHAIN_FIELDS
        },
        "applied_shock_node_ids": shock_nodes,
        "joint_state_id": f"{scenario}-joint-path",
    }


def _scenarios() -> list[dict]:
    paths = {
        "demand_contraction": [
            _chain_row("demand_contraction", "FY2027", 90, 12, 10, 2, 1, shock_nodes=["asp"]),
            _chain_row("demand_contraction", "FY2028", 100, 14, 12, 2, 1, shock_nodes=["asp"]),
        ],
        "central_operating_path": [
            _chain_row("central_operating_path", "FY2027", 100, 20, 18, 4, 1, shock_nodes=[]),
            _chain_row("central_operating_path", "FY2028", 120, 25, 23, 5, 1, shock_nodes=[]),
        ],
        "supply_tightness": [
            _chain_row("supply_tightness", "FY2027", 110, 26, 24, 5, 1, shock_nodes=["asp"]),
            _chain_row("supply_tightness", "FY2028", 140, 35, 33, 7, 1, shock_nodes=["asp"]),
        ],
    }
    return [
        {
            "id": scenario_id,
            "role": role,
            "probability": probability,
            "narrative": f"{scenario_id} joint path",
            "shocks": [] if role == "reference" else [{
                "node_id": "asp",
                "operation": "set",
                "value": 40 if scenario_id == "demand_contraction" else 60,
                "unit": "USD/unit",
                "model_cell_or_formula": "Drivers!F18",
                "effective_period": "FY2027",
                "lag_periods": 0,
            }],
            "profit_chain_periods": paths[scenario_id],
        }
        for scenario_id, role, probability in (
            ("demand_contraction", "alternative", 0.25),
            ("central_operating_path", "reference", 0.50),
            ("supply_tightness", "alternative", 0.25),
        )
    ]


def _integrated_periods() -> list[dict]:
    reference = next(s for s in _scenarios() if s["role"] == "reference")
    return [
        {"period": row["period"], "income_statement": {
            field: row[field] for field in CHAIN_FIELDS
        }}
        for row in reference["profit_chain_periods"]
    ]


def _outputs() -> dict:
    scenarios = {scenario["id"]: scenario for scenario in _scenarios()}
    by_scenario_period = {
        scenario_id: {row["period"]: row for row in scenario["profit_chain_periods"]}
        for scenario_id, scenario in scenarios.items()
    }
    outputs = {}
    for horizon, period in (("year_1", "FY2027"), ("year_2", "FY2028")):
        low = by_scenario_period["demand_contraction"][period]
        reference = by_scenario_period["central_operating_path"][period]
        high = by_scenario_period["supply_tightness"][period]
        outputs[horizon] = {
            "period": period,
            "low_scenario_id": "demand_contraction",
            "high_scenario_id": "supply_tightness",
            "revenue_point": reference["revenue"],
            "operating_profit_point": reference["operating_profit"],
            "pretax_profit_point": reference["pretax_profit"],
            "tax_expense_point": reference["tax_expense"],
            "noncontrolling_interest_net_income_point": reference[
                "net_income_attributable_to_noncontrolling_interests"
            ],
            "net_income_point": reference["net_income_attributable"],
            "profit_point": reference["net_income_attributable"],
            "revenue_low": low["revenue"],
            "revenue_high": high["revenue"],
            "operating_profit_low": low["operating_profit"],
            "operating_profit_high": high["operating_profit"],
            "pretax_profit_low": low["pretax_profit"],
            "pretax_profit_high": high["pretax_profit"],
            "tax_expense_low": low["tax_expense"],
            "tax_expense_high": high["tax_expense"],
            "noncontrolling_interest_net_income_low": low[
                "net_income_attributable_to_noncontrolling_interests"
            ],
            "noncontrolling_interest_net_income_high": high[
                "net_income_attributable_to_noncontrolling_interests"
            ],
            "net_income_low": low["net_income_attributable"],
            "net_income_high": high["net_income_attributable"],
            "profit_low": low["net_income_attributable"],
            "profit_high": high["net_income_attributable"],
            "point_evaluable": True,
        }
    return outputs


def _validate(scenarios: list[dict], *, outputs: dict | None = None, integrated: list[dict] | None = None) -> list[str]:
    validator = getattr(MODULE, "validate_scenario_profit_chains", None)
    if validator is None:
        return []
    return validator(
        scenarios,
        forecast_periods={"FY2027", "FY2028"},
        snapshot_outputs=outputs if outputs is not None else _outputs(),
        integrated_periods=integrated if integrated is not None else _integrated_periods(),
    )


def test_each_scenario_period_recomputes_the_full_profit_chain():
    mutations = {
        "operating profit": ("operating_profit", 999),
        "pretax profit": ("pretax_profit", 999),
        "tax to consolidated net income": ("net_income", 999),
        "NCI to attributable net income": ("net_income_attributable", 999),
    }
    for label, (field, value) in mutations.items():
        scenarios = copy.deepcopy(_scenarios())
        scenarios[0]["profit_chain_periods"][0][field] = value
        problems = _validate(scenarios)
        assert any(label in item for item in problems), (field, problems)


def test_profit_chain_authored_numbers_are_never_coerced_from_strings():
    scenarios = copy.deepcopy(_scenarios())
    for scenario in scenarios:
        for row in scenario["profit_chain_periods"]:
            for field in CHAIN_FIELDS:
                row[field] = str(row[field])
    problems = _validate(scenarios)
    assert problems
    for field in CHAIN_FIELDS:
        assert any(field in problem for problem in problems), (field, problems)


def test_profit_chain_rejects_bool_and_non_finite_authored_numbers():
    for value in (True, float("nan"), float("inf"), float("-inf")):
        scenarios = copy.deepcopy(_scenarios())
        scenarios[0]["profit_chain_periods"][0]["revenue"] = value
        problems = _validate(scenarios)
        assert any("revenue" in problem for problem in problems), (value, problems)


def test_every_scenario_must_cover_every_forecast_period():
    scenarios = copy.deepcopy(_scenarios())
    scenarios[2]["profit_chain_periods"].pop()
    problems = _validate(scenarios)
    assert any("period coverage" in item and "supply_tightness" in item for item in problems), problems


def test_scenario_chain_binds_shocks_and_every_layer_to_model_cells():
    scenarios = copy.deepcopy(_scenarios())
    scenarios[0]["profit_chain_periods"][0]["applied_shock_node_ids"] = []
    problems = _validate(scenarios)
    assert any("shock asp" in item and "not linked" in item for item in problems), problems

    scenarios = copy.deepcopy(_scenarios())
    scenarios[0]["profit_chain_periods"][0]["model_cells"]["pretax_profit"] = "some place"
    problems = _validate(scenarios)
    assert any("model_cells.pretax_profit" in item for item in problems), problems


def test_scenario_shock_cannot_affect_profit_before_effective_period_and_lag():
    scenarios = copy.deepcopy(_scenarios())
    contraction = next(item for item in scenarios if item["id"] == "demand_contraction")
    contraction["shocks"][0]["effective_period"] = "FY2028"
    # The fixture declares the shock on both years. FY2027 is now premature.
    problems = _validate(scenarios)
    assert any("FY2027" in item and "before" in item and "shock asp" in item for item in problems), problems


def test_joint_state_path_is_stable_within_scenario_and_distinct_across_scenarios():
    scenarios = copy.deepcopy(_scenarios())
    scenarios[0]["profit_chain_periods"][1]["joint_state_id"] = "fragmented-contraction-path"
    problems = _validate(scenarios)
    assert any("demand_contraction" in item and "joint_state_id" in item and "stable" in item for item in problems), problems

    scenarios = copy.deepcopy(_scenarios())
    shared = scenarios[0]["profit_chain_periods"][0]["joint_state_id"]
    for row in scenarios[2]["profit_chain_periods"]:
        row["joint_state_id"] = shared
    problems = _validate(scenarios)
    assert any("joint_state_id" in item and "more than one scenario" in item for item in problems), problems


def test_snapshot_low_high_are_one_declared_joint_scenario_not_marginal_splices():
    outputs = _outputs()
    outputs["year_2"]["operating_profit_low"] = 25  # Reference OP spliced into an alternative tuple.
    problems = _validate(_scenarios(), outputs=outputs)
    assert any("joint low scenario demand_contraction" in item for item in problems), problems

    outputs = _outputs()
    outputs["year_2"].pop("operating_profit_high")
    problems = _validate(_scenarios(), outputs=outputs)
    assert any("operating_profit_high" in item for item in problems), problems


def test_reference_role_reconciles_to_integrated_statements_and_point_snapshot():
    integrated = _integrated_periods()
    integrated[1]["income_statement"]["pretax_profit"] = 999
    problems = _validate(_scenarios(), integrated=integrated)
    assert any("central_operating_path" in item and "integrated pretax_profit" in item for item in problems), problems

    outputs = _outputs()
    outputs["year_1"]["tax_expense_point"] = 999
    problems = _validate(_scenarios(), outputs=outputs)
    assert any("central_operating_path" in item and "tax_expense_point" in item for item in problems), problems


def test_profit_chain_reconciliation_never_coerces_other_json_views():
    integrated = _integrated_periods()
    integrated[0]["income_statement"]["revenue"] = str(
        integrated[0]["income_statement"]["revenue"]
    )
    problems = _validate(_scenarios(), integrated=integrated)
    assert any("integrated revenue" in item for item in problems), problems

    outputs = _outputs()
    outputs["year_1"]["revenue_low"] = str(outputs["year_1"]["revenue_low"])
    problems = _validate(_scenarios(), outputs=outputs)
    assert any("revenue_low" in item for item in problems), problems


def test_reference_role_not_id_selects_the_canonical_path():
    scenarios = _scenarios()
    assert not any(scenario["id"] == "base" for scenario in scenarios)
    assert _validate(scenarios) == []


def test_exactly_one_reference_role_is_required():
    scenarios = copy.deepcopy(_scenarios())
    scenarios[1]["role"] = "alternative"
    scenarios[1]["shocks"] = copy.deepcopy(scenarios[0]["shocks"])
    problems = _validate(scenarios)
    assert any("exactly one reference" in item for item in problems), problems

    scenarios = copy.deepcopy(_scenarios())
    scenarios[0]["role"] = "reference"
    scenarios[0]["shocks"] = []
    problems = _validate(scenarios)
    assert any("exactly one reference" in item for item in problems), problems


def test_valid_joint_scenario_profit_chains_pass():
    assert _validate(_scenarios()) == []


def test_scenario_template_schema_docs_and_delivery_publish_the_contract():
    template = json.loads(
        (SKILL / "assets/templates/scenario_set_template.json").read_text(encoding="utf-8")
    )
    assert all("profit_chain_periods" in scenario for scenario in template["scenarios"])
    assert len(template["scenarios"]) == 1
    assert [scenario["role"] for scenario in template["scenarios"]].count("reference") == 1
    assert "base" not in {scenario["id"].lower() for scenario in template["scenarios"]}
    assert template["scenarios"][0]["probability"] == "REPLACE"

    schema_text = (SKILL / "assets/schemas/scenario_set.schema.json").read_text(encoding="utf-8")
    schema = json.loads(schema_text)
    profit_properties = schema["$defs"]["profitChainPeriod"]["properties"]
    for field in CHAIN_FIELDS:
        assert profit_properties[field] == {"type": "number"}
    shock_value = schema["properties"]["scenarios"]["items"]["properties"][
        "shocks"
    ]["items"]["properties"]["value"]
    assert shock_value == {"type": "number"}
    for field in (*CHAIN_FIELDS, "role", "reference", "alternative", "model_cells", "applied_shock_node_ids", "joint_state_id"):
        assert field in schema_text

    doctrine = (SKILL / "references/model-mechanical-integrity.md").read_text(encoding="utf-8").lower()
    for phrase in ("joint scenario", "marginal intervals", "operating_profit_low"):
        assert phrase in doctrine

    delivery = (SKILL / "scripts/validate_delivery.py").read_text(encoding="utf-8")
    scenario_start = delivery.index('scenario_path = workspace / "scenario_set.json"')
    scenario_pipeline = delivery[scenario_start:]
    assert "parse_scenario_catalog(" in scenario_pipeline
    assert "validate_scenario_profit_chains(" in scenario_pipeline
