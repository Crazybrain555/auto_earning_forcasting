"""Profitability persistence must be modeled, not asserted by a growth default."""
import csv
import json
import re
import sys
from pathlib import Path


SKILL = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SKILL / "scripts"))
from validate_delivery import validate_earnings_power_rows


LAYERS = (
    ("revenue", 100.0, 0.0, "revenue"),
    ("core_operating_profit", 20.0, -80.0, "profit"),
    ("gaap_operating_profit", 18.0, -2.0, "profit"),
    ("pretax_profit", 17.0, -1.0, "profit"),
    ("gaap_net_income_attributable", 12.0, -5.0, "profit"),
)


def accepted_rows():
    rows = [
        {
            "period": "FY2027",
            "profit_layer": layer,
            "reported_amount": str(amount),
            "bridge_from_prior_layer": str(bridge),
            "normalization_adjustment": "0",
            "normalized_amount": str(amount),
            "cash_support": str(amount),
            "accrual_component": "0",
            "investment_adjustment": "0",
            "cycle_adjustment": "0",
            "persistence_driver": "named operating equations",
            "competitive_response": "qualified supply response",
            "fade_target": str(amount),
            "fade_horizon": "3",
            "source_ids": "SRC1",
            "driver_node_ids": node,
            "status": "accepted",
            "notes": "fixture",
        }
        for layer, amount, bridge, node in LAYERS
    ]
    operating_row = next(row for row in rows if row["profit_layer"] == "gaap_operating_profit")
    operating_row.update({
        "cash_support": "15",
        "operating_tax_expense": "3",
        "nopat": "15",
        "noa_bridge_residual": "0",
    })
    rows[-1]["tax_expense"] = "5"
    rows[-1]["net_income_attributable_to_noncontrolling_interests"] = "0"
    return rows


def forecast_snapshot(*, operating_profit=18.0):
    return {
        "outputs": {
            "year_1": {
                "period": "FY2027",
                "revenue_point": 100.0,
                "operating_profit_point": operating_profit,
                "pretax_profit_point": 17.0,
                "tax_expense_point": 5.0,
                "noncontrolling_interest_net_income_point": 0.0,
                "net_income_point": 12.0,
                "profit_point": 12.0,
            }
        },
        "integrated_model": {
            "periods": [{
                "period": "FY2027",
                "income_statement": {
                    "revenue": 100.0,
                    "operating_costs_and_expenses": 82.0,
                    "operating_profit": 18.0,
                    "nonoperating_income_expense_net": -1.0,
                    "pretax_profit": 17.0,
                    "tax_expense": 5.0,
                    "net_income": 12.0,
                    "net_income_attributable_to_noncontrolling_interests": 0.0,
                    "net_income_attributable": 12.0,
                },
            }]
        },
        "human_required": [],
    }


def problems(rows, *, snapshot=None, readiness="research-grade", materiality_threshold=None):
    kwargs = {}
    if materiality_threshold is not None:
        kwargs["material_profit_impact_pct"] = materiality_threshold
    return validate_earnings_power_rows(
        rows,
        source_ids={"SRC1"},
        graph_node_ids={"revenue", "profit"},
        snapshot=snapshot or forecast_snapshot(),
        readiness_target=readiness,
        **kwargs,
    )


def test_earnings_power_reference_and_schedule_are_first_class():
    reference = SKILL / "references/earnings-power-and-mean-reversion.md"
    template = SKILL / "assets/templates/earnings_power_bridge_template.csv"
    assert reference.is_file()
    assert template.is_file()

    text = reference.read_text(encoding="utf-8").lower()
    for concept in (
        "reported earnings",
        "normalized earnings",
        "cash",
        "accrual",
        "investment",
        "cycle",
        "competitive response",
        "conditional",
        "base rate",
        "misuse boundary",
        "not_material_with_reason",
        "each measured immaterial",
        "material_profit_impact_pct",
        "measured bridge",
        "research-grade",
        "explicit zero",
        "integrated_model",
        "forecast_snapshot",
    ):
        assert concept in text, concept

    with template.open(encoding="utf-8-sig", newline="") as handle:
        header = set(next(csv.reader(handle)))
    required = {
        "period", "profit_layer", "reported_amount", "normalization_adjustment",
        "normalized_amount", "bridge_from_prior_layer", "cash_support", "accrual_component",
        "investment_adjustment", "cycle_adjustment", "persistence_driver",
        "competitive_response", "fade_target", "fade_horizon",
        "tax_expense", "net_income_attributable_to_noncontrolling_interests",
        "operating_tax_expense", "nopat", "noa_bridge_residual",
        "source_ids", "driver_node_ids", "status", "notes",
    }
    assert required <= header, required - header


def test_accepted_layers_reconcile_across_the_profit_chain_and_snapshot():
    assert problems(accepted_rows()) == []


def test_operating_earnings_quality_bridge_recomputes_nopat_and_delta_noa():
    rows = accepted_rows()
    operating_row = next(row for row in rows if row["profit_layer"] == "gaap_operating_profit")
    operating_row.update({
        "cash_support": "10",
        "accrual_component": "5",
        "noa_bridge_residual": "0",
    })
    assert problems(rows) == []

    operating_row["accrual_component"] = "7"
    found = problems(rows)
    assert any("nopat must equal cash_support plus accrual_component" in item for item in found), found


def test_declared_noa_residual_must_equal_the_recomputed_residual():
    rows = accepted_rows()
    operating_row = next(row for row in rows if row["profit_layer"] == "gaap_operating_profit")
    operating_row["noa_bridge_residual"] = "2"
    found = problems(rows)
    assert any("noa_bridge_residual" in item for item in found), found


def test_cross_layer_bridge_mismatch_is_rejected():
    rows = accepted_rows()
    rows[2]["bridge_from_prior_layer"] = "-1"
    found = problems(rows)
    assert any("prior reported + bridge" in problem for problem in found), found


def test_accepted_layer_must_reconcile_to_snapshot_output():
    found = problems(accepted_rows(), snapshot=forecast_snapshot(operating_profit=19.0))
    assert any("does not reconcile to snapshot operating_profit_point" in problem for problem in found), found


def test_bridge_must_reconcile_to_same_period_integrated_statements():
    snapshot = forecast_snapshot()
    snapshot["integrated_model"]["periods"][0]["income_statement"]["pretax_profit"] = 16.0
    found = problems(accepted_rows(), snapshot=snapshot)
    assert any("integrated statement pretax_profit" in problem for problem in found), found


def test_every_snapshot_period_needs_an_integrated_statement_period():
    rows = accepted_rows()
    rows += [{**row, "period": "FY2028"} for row in accepted_rows()]
    snapshot = forecast_snapshot()
    snapshot["outputs"]["year_2"] = {
        **snapshot["outputs"]["year_1"],
        "period": "FY2028",
    }
    found = problems(rows, snapshot=snapshot)
    assert any("FY2028" in problem and "integrated statement" in problem for problem in found), found


def test_tax_and_noncontrolling_interest_bridge_must_be_explicit_and_reconcile():
    rows = accepted_rows()
    rows[-1]["net_income_attributable_to_noncontrolling_interests"] = "2"
    found = problems(rows)
    assert any("pretax less tax and non-controlling interest" in problem for problem in found), found


def test_all_human_required_layers_cannot_pass_as_research_grade():
    rows = accepted_rows()
    for row in rows:
        row["status"] = "human_required"
        row["notes"] = "Conclusion-critical layer cannot be observed independently."
    snapshot = forecast_snapshot()
    snapshot["human_required"] = ["FY2027 earnings-power bridge"]
    found = problems(rows, snapshot=snapshot, readiness="research-grade")
    assert any("all earnings-power layers are human_required" in problem for problem in found), found


def test_all_human_required_layers_are_allowed_only_when_not_decision_ready():
    rows = accepted_rows()
    for row in rows:
        row["status"] = "human_required"
        row["notes"] = "Conclusion-critical layer cannot be observed independently."
    snapshot = forecast_snapshot()
    snapshot["human_required"] = ["FY2027 earnings-power bridge"]
    found = problems(rows, snapshot=snapshot, readiness="not-decision-ready")
    assert not any("readiness" in problem for problem in found), found


def test_all_not_material_layers_cannot_form_a_research_grade_shell():
    rows = accepted_rows()
    for row in rows:
        row.update({
            "reported_amount": "N/A", "bridge_from_prior_layer": "N/A",
            "normalization_adjustment": "N/A", "normalized_amount": "N/A",
            "cash_support": "N/A", "accrual_component": "N/A",
            "investment_adjustment": "N/A", "cycle_adjustment": "N/A",
            "fade_target": "N/A", "fade_horizon": "N/A",
            "source_ids": "", "driver_node_ids": "",
            "status": "not_material_with_reason",
            "notes": "Claimed immaterial without a measured bridge.",
        })
    found = problems(rows, materiality_threshold=5.0)
    assert any("all earnings-power layers are not_material_with_reason" in item for item in found), found
    assert any("non-numeric" in item for item in found), found
    assert any("source_ids missing" in item for item in found), found
    assert any("driver_node_ids missing" in item for item in found), found


def test_one_measured_immaterial_layer_may_be_conditionally_exempt():
    rows = accepted_rows()
    rows[2]["status"] = "not_material_with_reason"  # GAAP/core OP bridge is 2% of revenue.
    rows[2]["notes"] = "GAAP/core operating-profit difference is 2% of revenue, below the run's 5% threshold."
    assert problems(rows, materiality_threshold=5.0) == []


def test_each_not_material_layer_must_be_measured_and_below_case_threshold():
    rows = accepted_rows()
    rows[1]["status"] = "not_material_with_reason"  # 80% bridge is plainly material.
    rows[1]["notes"] = "Claimed immaterial."
    found = problems(rows, materiality_threshold=5.0)
    assert any("exceeds materiality threshold" in item for item in found), found

    rows = accepted_rows()
    for index in (2, 3):
        rows[index]["status"] = "not_material_with_reason"
        rows[index]["notes"] = "Small measured bridge."
    assert problems(rows, materiality_threshold=5.0) == []


def test_not_material_layer_still_needs_source_graph_and_reconciliation():
    rows = accepted_rows()
    row = rows[2]
    row["status"] = "not_material_with_reason"
    row["notes"] = "Small measured bridge."
    row["source_ids"] = "MISSING"
    row["driver_node_ids"] = "missing_node"
    row["reported_amount"] = "19"
    row["normalized_amount"] = "19"
    found = problems(rows, materiality_threshold=5.0)
    assert any("unknown source ids" in item for item in found), found
    assert any("unknown driver nodes" in item for item in found), found
    assert any("prior reported + bridge" in item for item in found), found
    assert any("does not reconcile to snapshot operating_profit_point" in item for item in found), found


def test_one_fully_unresolved_forecast_period_cannot_hide_behind_accepted_history():
    historical = accepted_rows()
    for row in historical:
        row["period"] = "FY2026"
    forecast = accepted_rows()
    for row in forecast:
        row["status"] = "human_required"
        row["notes"] = "Conclusion-critical forecast layer cannot be observed independently."
    snapshot = forecast_snapshot()
    snapshot["human_required"] = ["FY2027 earnings-power bridge"]
    found = problems(historical + forecast, snapshot=snapshot, readiness="screen-grade")
    assert any("FY2027" in problem and "not-decision-ready" in problem for problem in found), found


def test_production_workflow_routes_to_earnings_power_schedule():
    trainer = (SKILL / "SKILL.md").read_text(encoding="utf-8").lower()
    live = (SKILL / "assets/live_release/SKILL.md").read_text(encoding="utf-8").lower()
    for text in (trainer, live):
        assert "references/earnings-power-and-mean-reversion.md" in text
        assert "earnings_power_bridge.csv" in text

    registry = json.loads((SKILL / "assets/artifact_registry.json").read_text(encoding="utf-8"))
    earnings_artifact = next(
        row for row in registry["artifacts"] if row["path"] == "earnings_power_bridge.csv"
    )
    assert earnings_artifact["requirement"] == "core"
    assert earnings_artifact["scaffold"] is True
    assert earnings_artifact["template"] == "assets/templates/earnings_power_bridge_template.csv"

    method = json.loads((SKILL / "assets/method_system.json").read_text(encoding="utf-8"))
    statement_stage = next(stage for stage in method["stages"] if stage["id"] == "integrated_statements")
    assert "period_by_period_reported_profit_chain_reconciliation" in statement_stage["gates"]
    value_stage = next(stage for stage in method["stages"] if stage["id"] == "value_creation")
    assert "references/earnings-power-and-mean-reversion.md" in value_stage["files"]
    assert "conditional_earnings_persistence_and_fade" in value_stage["gates"]


def test_small_sample_underforecast_does_not_become_an_optimism_rule():
    doctrine = (SKILL / "references/profit-forecast-accuracy.md").read_text(encoding="utf-8").lower()
    assert "sample-limited" in doctrine
    assert "conditional mean reversion" in doctrine
    assert "company-specific guidance" in doctrine
    assert "round 1" not in doctrine
    assert "round-1" not in doctrine
    assert not re.search(r"\b\d+\s+of\s+\d+\s+horizons\b", doctrine)
    assert "management guidance is conservative for most" not in doctrine
    assert "absent that reason, deceleration is an unargued default and must be corrected" not in doctrine


def test_cash_accrual_identity_uses_a_consistent_after_tax_operating_basis():
    doctrine = (SKILL / "references/earnings-power-and-mean-reversion.md").read_text(encoding="utf-8").lower()
    assert "nopat = after-tax operating free cash flow + change in net operating assets" in doctrine
    assert "operating income = free cash flow + change in net operating assets" not in doctrine
