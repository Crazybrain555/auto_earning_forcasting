"""Orthogonal diagnostics protect causal forecast construction, not a score."""
import json
import subprocess
import sys
import tempfile
from pathlib import Path

SKILL = Path(__file__).resolve().parents[1]

BASE_SNAPSHOT = {
    "historical_base": {"trailing_organic_growth_pct": 20.0},
    "growth_challenger_review": [
        {
            "challenger": "trailing_organic_growth",
            "horizon": "year_2",
            "status": "accepted",
            "challenger_growth_pct": 20.0,
            "driver_tree_growth_pct": 30.0,
            "difference_direction": "acceleration",
            "material_difference": True,
            "materiality_basis": "The 10 percentage-point gap changes FY+2 revenue materially.",
            "transition_driver_node_ids": ["ai_units"],
            "named_state_ids": ["terminal_demand_up", "capacity_available"],
            "bridge": [
                {"driver_node_id": "ai_units", "delta_growth_pct": 10.0}
            ],
            "notes": "Demand and qualified capacity jointly support the transition.",
        },
    ],
    "error_budget": {h: {"expected_revenue_error_pct": 6, "expected_margin_error_pp": 2,
                         "dominant_risk": "margin", "why": "spread"}
                     for h in ("year_1", "year_2", "year_3_distribution")},
    "outputs": {
        "year_1": {
            "period": "FY2027", "revenue_point": 1000.0,
            "operating_profit_point": 180.0, "pretax_profit_point": 170.0,
            "tax_expense_point": 40.0, "noncontrolling_interest_net_income_point": 0.0,
            "net_income_point": 130.0, "profit_point": 130.0,
        },
        "year_2": {
            "period": "FY2028", "revenue_point": 1300.0,
            "revenue_low": 1150.0, "revenue_high": 1450.0,
            "operating_profit_point": 230.0, "pretax_profit_point": 215.0,
            "tax_expense_point": 50.0, "noncontrolling_interest_net_income_point": 0.0,
            "net_income_point": 165.0, "profit_point": 165.0,
            "profit_low": 130.0, "profit_high": 200.0,
        },
        "year_3_distribution": {
            "period": "FY2029", "revenue_point": 1600.0,
            "revenue_low": 1280.0, "revenue_high": 1920.0,
            "operating_profit_point": 275.0, "pretax_profit_point": 255.0,
            "tax_expense_point": 60.0, "noncontrolling_interest_net_income_point": 0.0,
            "net_income_point": 195.0, "profit_point": 195.0,
            "profit_low": 140.0, "profit_high": 250.0,
        },
    },
}
FULL_REPORT = ("# R\n\nTax rate normalized; no valuation allowance. Interest income modeled, no FX exposure. "
               "No impairment or restructuring. Share count flat, no buyback.\n")


def run(snapshot, report=FULL_REPORT, manifest=None, *, strict=False):
    with tempfile.TemporaryDirectory() as td:
        ws = Path(td)
        (ws / "run_manifest.json").write_text(json.dumps(manifest or {"entity": "T", "as_of": "2026-07-18"}), encoding="utf-8")
        (ws / "forecast_snapshot.json").write_text(json.dumps(snapshot), encoding="utf-8")
        (ws / "report.md").write_text(report, encoding="utf-8")
        command = [sys.executable, str(SKILL / "scripts/validate_delivery.py"), "--workspace", str(ws)]
        if strict:
            command.append("--strict")
        subprocess.run(command,
                       capture_output=True, text=True)
        result = json.loads((ws / "delivery_validation.json").read_text(encoding="utf-8"))
    return {c["check"]: c for c in result["checks"]}


def test_narrow_intervals_are_not_rejected_by_a_universal_floor():
    """Interval width follows named states/calibration, never a four-case floor."""
    snap = json.loads(json.dumps(BASE_SNAPSHOT))
    snap["outputs"]["year_2"].update({"revenue_low": 1250.0, "revenue_high": 1350.0})
    assert "accuracy:interval-width" not in run(snap)


def test_complete_growth_challenger_review_passes():
    assert run(BASE_SNAPSHOT)["accuracy:growth-challengers"]["passed"]


def test_schema_does_not_turn_case_selected_challengers_or_costs_into_count_quotas():
    schema = json.loads(
        (SKILL / "assets/schemas/forecast_snapshot.schema.json").read_text(encoding="utf-8")
    )
    assert "minItems" not in schema["properties"]["growth_challenger_review"]
    persistence = schema["properties"]["persistence_analysis"]["properties"]
    assert "minItems" not in persistence["cost_behavior"]


def test_company_specific_outside_view_is_not_rejected_by_a_fixed_taxonomy():
    snap = json.loads(json.dumps(BASE_SNAPSHOT))
    snap["growth_challenger_review"][0]["challenger"] = "installed_base_renewal_runoff"
    assert run(snap)["accuracy:growth-challengers"]["passed"]


def test_material_deceleration_without_named_driver_states_is_rejected():
    snap = json.loads(json.dumps(BASE_SNAPSHOT))
    row = snap["growth_challenger_review"][0]
    row.update({"driver_tree_growth_pct": 5.0, "difference_direction": "deceleration"})
    row["transition_driver_node_ids"] = []
    row["named_state_ids"] = []
    c = run(snap)["accuracy:growth-challengers"]
    assert not c["passed"] and "named transition_driver_node_ids" in c["detail"], c["detail"]


def test_material_acceleration_without_named_driver_states_is_rejected():
    snap = json.loads(json.dumps(BASE_SNAPSHOT))
    row = snap["growth_challenger_review"][0]
    row["transition_driver_node_ids"] = []
    row["named_state_ids"] = []
    c = run(snap)["accuracy:growth-challengers"]
    assert not c["passed"] and "named transition_driver_node_ids" in c["detail"], c["detail"]


def test_unavailable_challenger_requires_a_named_status_and_reason():
    snap = json.loads(json.dumps(BASE_SNAPSHOT))
    snap["growth_challenger_review"].append({
        "challenger": "supplier_capacity_reference_class",
        "horizon": "year_2",
        "status": "not_available_with_reason",
        "notes": "",
    })
    c = run(snap)["accuracy:growth-challengers"]
    assert not c["passed"] and "requires notes" in c["detail"], c["detail"]


def test_named_transition_ids_must_be_strings_not_embedded_objects():
    snap = json.loads(json.dumps(BASE_SNAPSHOT))
    snap["growth_challenger_review"][0]["transition_driver_node_ids"] = [{"id": "ai_units"}]
    c = run(snap)["accuracy:growth-challengers"]
    assert not c["passed"] and "named transition_driver_node_ids" in c["detail"], c["detail"]


def test_quantified_growth_bridge_must_use_the_named_transition_drivers():
    snap = json.loads(json.dumps(BASE_SNAPSHOT))
    snap["growth_challenger_review"][0]["bridge"][0]["driver_node_id"] = "unlisted_driver"
    c = run(snap)["accuracy:growth-challengers"]
    assert not c["passed"] and "not named in transition_driver_node_ids" in c["detail"], c["detail"]


def test_strict_full_company_output_requires_the_complete_profit_chain():
    snap = json.loads(json.dumps(BASE_SNAPSHOT))
    del snap["outputs"]["year_2"]["operating_profit_point"]
    c = run(snap, strict=True)["snapshot:canonical-year_2"]
    assert not c["passed"] and "operating_profit_point" in c["detail"], c["detail"]


def test_missing_error_budget_is_rejected():
    snap = json.loads(json.dumps(BASE_SNAPSHOT))
    del snap["error_budget"]
    c = run(snap)["accuracy:error-budget"]
    assert not c["passed"] and "error_budget missing" in c["detail"]


def test_report_keywords_are_not_used_as_a_proxy_for_below_the_line_modeling():
    checks = run(BASE_SNAPSHOT, report="# R\n\nRevenue grows. Margins expand.\n")
    assert "accuracy:below-the-line-screen" not in checks
