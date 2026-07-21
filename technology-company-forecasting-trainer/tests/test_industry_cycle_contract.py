"""Cycle assurance follows selected economics, not a universal row checklist."""
from __future__ import annotations

import csv
import importlib.util
from pathlib import Path


SKILL = Path(__file__).resolve().parents[1]
TEMPLATE = SKILL / "assets/templates/operating_cycle_template.csv"


def _load_delivery_module():
    path = SKILL / "scripts/validate_delivery.py"
    spec = importlib.util.spec_from_file_location("delivery_cycle_contract", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _template_header() -> list[str]:
    with TEMPLATE.open(encoding="utf-8-sig", newline="") as handle:
        return next(csv.reader(handle))


def _blank_row() -> dict[str, str]:
    return dict.fromkeys(_template_header(), "")


def _selected_state(
    *,
    family: str = "contracted_usage",
    source_ids: str = "S1",
    data_series_ids: str = "D1",
    driver_node_ids: str = "main_driver",
) -> dict[str, str]:
    row = _blank_row()
    row.update({
        "record_type": "state",
        "branch_id": "core",
        "state_family": family,
        "metric_name": "contracted production usage",
        "period": "2026Q2",
        "frequency": "quarterly",
        "value": "100",
        "unit": "unit",
        "ownership_or_location": "customer acceptance system",
        "lead_lag_days": "30",
        "source_ids": source_ids,
        "data_series_ids": data_series_ids,
        "driver_node_ids": driver_node_ids,
        "as_of": "2026-07-20",
        "data_vintage_at": "2026-07-01",
        "applicability": "material",
        "status": "accepted",
        "notes": "Selected because it carries recognized volume in the main line.",
    })
    return row


def _selected_revenue_equation(
    *,
    source_ids: str = "S1",
    data_series_ids: str = "D1",
    driver_node_ids: str = "main_driver",
) -> dict[str, str]:
    row = _blank_row()
    row.update({
        "record_type": "equation_check",
        "branch_id": "core",
        "equation_id": "recognized-revenue",
        "equation_type": "revenue_recognition",
        "metric_name": "recognized revenue equals accepted quantity times realized price",
        "period": "2026Q2",
        "frequency": "quarterly",
        "source_ids": source_ids,
        "data_series_ids": data_series_ids,
        "driver_node_ids": driver_node_ids,
        "as_of": "2026-07-20",
        "data_vintage_at": "2026-07-01",
        "model_cell_or_formula": "Checks!B22",
        "equation_status": "accepted",
        "lhs_value": "900",
        "rhs_1_value": "90",
        "rhs_2_value": "10",
        "lhs_unit": "USD",
        "rhs_1_unit": "unit",
        "rhs_2_unit": "USD/unit",
        "unit_conversion_factor": "1",
        "check_tolerance": "0.001",
        "check_residual": "0",
        "status": "accepted",
    })
    return row


def _cycle_context() -> dict:
    return {
        "strict": True,
        "readiness_target": "research-grade",
        "manifest_entity": "TEST",
        "source_ids": {"S1"},
        "data_series_ids": {"D1"},
        "graph_node_ids": {"minor_driver", "main_driver"},
        "main_line_carriers": {"main_driver"},
        "main_line_relevant_nodes": {"main_driver"},
        "profit_pool_rows": [{
            "boundary_id": "B1",
            "row_type": "component",
            "value_chain_node": "core",
            "driver_node_ids": "main_driver",
            "status": "accepted",
        }],
    }


def test_capacity_module_has_no_universal_utilization_threshold():
    text = (SKILL / "references/module-capacity-utilization-yield.md").read_text(
        encoding="utf-8"
    ).lower()
    assert "85%" not in text
    for concept in (
        "source-specific", "capacity definition", "revision", "demand",
        "qualification", "scenario",
    ):
        assert concept in text, concept

def test_profit_pool_template_carries_boundary_and_reconciliation_contract():
    path = SKILL / "assets/templates/industry_profit_pool_template.csv"
    with path.open(encoding="utf-8-sig", newline="") as handle:
        header = set(next(csv.reader(handle)))
    required = {
        "boundary_id", "row_type", "value_chain_node", "period", "geography",
        "product_scope", "currency", "revenue_pool", "profit_measure", "profit_pool",
        "invested_capital", "company_revenue_share", "company_profit_share",
        "pricing_mechanism", "competitor_response", "response_lead_time_days",
        "source_ids", "driver_node_ids", "data_vintage_at", "status", "notes",
    }
    assert required <= header, required - header


def test_operating_cycle_template_is_header_only_and_selects_no_universal_states():
    with TEMPLATE.open(encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.reader(handle))
    assert len(rows) == 1
    header = set(rows[0])
    assert {
        "branch_id", "state_family", "metric_name", "period", "frequency",
        "value", "unit", "source_ids", "data_series_ids", "driver_node_ids",
        "as_of", "data_vintage_at", "record_type", "equation_id",
        "equation_type", "lhs_value", "rhs_1_value", "rhs_2_value",
        "lhs_unit", "rhs_1_unit", "rhs_2_unit", "unit_conversion_factor",
        "check_tolerance", "check_residual", "model_cell_or_formula",
        "equation_status", "unavailable_reason",
    } <= header


def test_profit_pool_components_must_reconcile_to_total():
    module = _load_delivery_module()
    rows = [
        {"boundary_id": "B1", "row_type": "total", "value_chain_node": "total", "period": "FY2025",
         "geography": "global", "product_scope": "X", "currency": "USD", "revenue_pool": "100",
         "profit_measure": "EBIT", "profit_pool": "20", "source_ids": "S1", "driver_node_ids": "n1",
         "data_vintage_at": "2026-01-01", "status": "accepted", "notes": ""},
        {"boundary_id": "B1", "row_type": "component", "value_chain_node": "upstream", "period": "FY2025",
         "geography": "global", "product_scope": "X", "currency": "USD", "revenue_pool": "60",
         "profit_measure": "EBIT", "profit_pool": "15", "source_ids": "S1", "driver_node_ids": "n1",
         "data_vintage_at": "2026-01-01", "status": "accepted", "notes": ""},
        {"boundary_id": "B1", "row_type": "residual", "value_chain_node": "other", "period": "FY2025",
         "geography": "global", "product_scope": "X", "currency": "USD", "revenue_pool": "40",
         "profit_measure": "EBIT", "profit_pool": "5", "source_ids": "S2", "driver_node_ids": "n2",
         "data_vintage_at": "2026-01-02", "status": "accepted", "notes": ""},
    ]
    assert module.validate_industry_profit_pool_rows(rows) == []
    rows[-1]["profit_pool"] = "1"
    assert any(
        "reconcile" in problem.lower()
        for problem in module.validate_industry_profit_pool_rows(rows)
    )


def test_one_selected_state_and_one_selected_equation_are_sufficient():
    module = _load_delivery_module()
    problems = module.validate_operating_cycle_rows(
        [_selected_state(), _selected_revenue_equation()],
        **_cycle_context(),
    )
    assert problems == []


def test_selected_state_must_resolve_source_series_and_graph_references():
    module = _load_delivery_module()
    row = _selected_state(
        source_ids="UNKNOWN_SOURCE",
        data_series_ids="UNKNOWN_SERIES",
        driver_node_ids="UNKNOWN_NODE",
    )
    problems = " ".join(
        module.validate_operating_cycle_rows([row], **_cycle_context())
    )
    assert "unknown source_ids" in problems
    assert "unknown data_series_ids" in problems
    assert "unknown driver_node_ids" in problems


def test_selected_material_state_must_touch_the_profit_or_thesis_line():
    module = _load_delivery_module()
    problems = module.validate_operating_cycle_rows(
        [_selected_state(driver_node_ids="minor_driver")],
        **_cycle_context(),
    )
    assert any("main-line or profit-pool" in problem for problem in problems)


def test_selected_equation_recomputes_residual_instead_of_trusting_declared_check():
    module = _load_delivery_module()
    row = _selected_revenue_equation()
    row["lhs_value"] = "930"
    row["check_residual"] = "0"
    problems = module.validate_operating_cycle_rows([row], **_cycle_context())
    assert any("does not reconcile" in problem for problem in problems)
    assert any("check_residual" in problem for problem in problems)


def test_selected_equation_requires_dimensionally_consistent_units():
    module = _load_delivery_module()
    row = _selected_revenue_equation()
    row["rhs_2_unit"] = "USD/wafer"
    problems = module.validate_operating_cycle_rows([row], **_cycle_context())
    assert any("price denominator" in problem for problem in problems)


def test_selected_equation_must_resolve_source_series_and_graph_references():
    module = _load_delivery_module()
    row = _selected_revenue_equation(
        source_ids="UNKNOWN_SOURCE",
        data_series_ids="UNKNOWN_SERIES",
        driver_node_ids="UNKNOWN_NODE",
    )
    problems = " ".join(
        module.validate_operating_cycle_rows([row], **_cycle_context())
    )
    assert "unknown source_ids" in problems
    assert "unknown data_series_ids" in problems
    assert "unknown driver_node_ids" in problems


def test_selected_disclosure_limited_equation_caps_readiness():
    module = _load_delivery_module()
    row = _selected_revenue_equation()
    row.update({
        "equation_status": "disclosure_limited",
        "lhs_value": "",
        "rhs_1_value": "",
        "rhs_2_value": "",
        "check_residual": "",
        "data_series_ids": "",
        "unavailable_reason": (
            "Customer acceptance quantity is not disclosed and no independent "
            "measurement exists at the forecast cutoff."
        ),
    })
    screen_context = {**_cycle_context(), "readiness_target": "screen-grade"}
    assert module.validate_operating_cycle_rows([row], **screen_context) == []
    problems = module.validate_operating_cycle_rows([row], **_cycle_context())
    assert any("readiness_target" in problem for problem in problems)


def test_cycle_method_routes_selection_to_materiality_and_independent_review():
    text = (SKILL / "references/industry-economics-and-cycle.md").read_text(
        encoding="utf-8"
    ).lower()
    for concept in (
        "author only selected states",
        "do not pre-populate",
        "independent research reviewer",
        "recomputes the residual",
        "main-line",
    ):
        assert concept in text, concept
