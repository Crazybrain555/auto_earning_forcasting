"""Narrow-scope exceptions must not become full-company strict-mode bypasses."""
from __future__ import annotations

import importlib.util
from pathlib import Path


SKILL = Path(__file__).resolve().parents[1]
MODULE_PATH = SKILL / "scripts" / "scope_exception_contract.py"
SPEC = importlib.util.spec_from_file_location("scope_exception_contract", MODULE_PATH)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
SPEC.loader.exec_module(MODULE)


def valid_narrow_manifest() -> dict:
    return {
        "run_mode": "audit_only",
        "purpose": "narrow audit of one inventory valuation and reversal event",
        "readiness_target": "screen-grade",
        "narrow_scope_exception": {
            "status": "active",
            "scope_type": "single_accounting_event",
            "scope_description": (
                "Only the named inventory write-down, reversal and related tax effects are in scope."
            ),
            "materiality_test": {
                "affected_metric": "gaap_net_income",
                "unit": "USDm",
                "baseline_value": 100.0,
                "perturbation_name": "inventory write-down increases by USD10m",
                "perturbation_value": 10.0,
                "perturbed_value": 92.0,
                "impact_value": -8.0,
                "decision_threshold": 5.0,
                "result": "above_threshold",
            },
            "affected_statement_links": [
                "balance_sheet.inventory",
                "income_statement.cogs",
                "income_statement.gaap_net_income",
                "cash_flow_statement.working_capital",
            ],
            "blocked_full_company_conclusions": [
                "full_company_revenue",
                "full_company_operating_profit",
                "full_company_gaap_net_income",
                "full_company_intrinsic_value",
            ],
            "readiness_cap": "screen-grade",
        },
    }


def test_full_company_strict_cannot_invoke_narrow_exception():
    manifest = valid_narrow_manifest()
    manifest.update(
        {
            "run_mode": "live_forecast",
            "purpose": "full-company five-year forecast and valuation",
            "readiness_target": "research-grade",
        }
    )
    errors = MODULE.validate_narrow_scope_exception(
        manifest,
        requested_exceptions=["driver_tree_relaxed", "workbook_formula_min_below_default"],
    )
    assert errors
    assert "full-company" in " ".join(errors).lower()


def test_reason_only_is_not_a_scope_contract():
    manifest = {
        "run_mode": "audit_only",
        "purpose": "narrow inventory audit",
        "readiness_target": "screen-grade",
        "research_depth_override_reason": "x" * 120,
    }
    errors = MODULE.validate_narrow_scope_exception(
        manifest,
        requested_exceptions=["research_depth_thresholds_below_default"],
    )
    assert errors
    assert "narrow_scope_exception" in " ".join(errors)


def test_typed_narrow_exception_can_limit_work_without_claiming_full_company():
    errors = MODULE.validate_narrow_scope_exception(
        valid_narrow_manifest(),
        requested_exceptions=[
            "research_depth_thresholds_below_default",
            "workbook_checks_relaxed",
            "driver_quantification_relaxed",
        ],
    )
    assert errors == []


def test_one_material_statement_link_is_not_rejected_by_a_link_count_proxy():
    manifest = valid_narrow_manifest()
    manifest["narrow_scope_exception"]["affected_statement_links"] = [
        "balance_sheet.inventory"
    ]
    errors = MODULE.validate_narrow_scope_exception(
        manifest,
        requested_exceptions=["single_driver_audit"],
    )
    assert errors == []


def test_materiality_bridge_and_blocked_conclusions_are_machine_checked():
    manifest = valid_narrow_manifest()
    contract = manifest["narrow_scope_exception"]
    contract["materiality_test"]["impact_value"] = 999.0
    contract["blocked_full_company_conclusions"] = ["full_company_revenue"]
    errors = MODULE.validate_narrow_scope_exception(
        manifest,
        requested_exceptions=["below_the_line_relaxed"],
    )
    joined = " ".join(errors).lower()
    assert "impact_value" in joined
    assert "blocked_full_company_conclusions" in joined


def test_exception_must_cap_readiness_below_research_grade():
    manifest = valid_narrow_manifest()
    manifest["readiness_target"] = "research-grade"
    errors = MODULE.validate_narrow_scope_exception(
        manifest,
        requested_exceptions=["driver_tree_relaxed"],
    )
    assert errors
    assert "readiness" in " ".join(errors).lower()


def test_active_scope_contract_is_validated_even_without_a_relaxed_switch():
    """The scope declaration is itself a contract, not only a waiver side effect."""

    manifest = valid_narrow_manifest()
    manifest["narrow_scope_exception"]["scope_description"] = "inventory"

    errors = MODULE.validate_narrow_scope_exception(
        manifest,
        requested_exceptions=[],
    )

    assert errors
    assert "scope_description" in " ".join(errors)


def test_inactive_scope_needs_no_contract_when_no_exception_is_requested():
    assert MODULE.validate_narrow_scope_exception(
        {"narrow_scope_exception": {"status": "not_applicable"}},
        requested_exceptions=[],
    ) == []
