"""Shared equation primitives keep every financial view on one arithmetic law."""
from __future__ import annotations

import importlib.util
from pathlib import Path


SKILL = Path(__file__).resolve().parents[1]
MODULE_PATH = SKILL / "scripts" / "equation_contract.py"
SPEC = importlib.util.spec_from_file_location("equation_contract", MODULE_PATH)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
SPEC.loader.exec_module(MODULE)


def valid_profit_chain() -> dict:
    return {
        "revenue": 100.0,
        "operating_costs_and_expenses": 80.0,
        "operating_profit": 20.0,
        "nonoperating_income_expense_net": -2.0,
        "pretax_profit": 18.0,
        "tax_expense": 4.0,
        "net_income": 14.0,
        "net_income_attributable_to_noncontrolling_interests": 1.0,
        "net_income_attributable": 13.0,
    }


def test_profit_chain_equations_are_shared_and_recomputed_as_one_chain():
    assert MODULE.validate_profit_chain_equations(valid_profit_chain(), label="base:FY2027") == []

    row = valid_profit_chain()
    row["pretax_profit"] = 999.0
    errors = MODULE.validate_profit_chain_equations(row, label="base:FY2027")
    assert any("pretax profit" in item for item in errors), errors


def test_profit_chain_rejects_numeric_strings_at_the_authored_json_boundary():
    row = valid_profit_chain()
    for field in MODULE.PROFIT_CHAIN_FIELDS:
        row[field] = str(row[field])
    errors = MODULE.validate_profit_chain_equations(row, label="reference:FY2027")
    assert errors
    for field in MODULE.PROFIT_CHAIN_FIELDS:
        assert any(field in item for item in errors), (field, errors)


def test_equation_numbers_reject_booleans_nan_and_infinity():
    for value in (True, False, float("nan"), float("inf"), ""):
        assert MODULE.finite_number(value) is None


def test_authored_json_numbers_are_finite_and_never_coerced():
    for value in (0, 1, 1.5, -2.0):
        assert MODULE.strict_finite_number(value) == float(value)
    for value in (
        True,
        False,
        "64",
        "NaN",
        "Infinity",
        float("nan"),
        float("inf"),
        float("-inf"),
        10**1000,
        None,
    ):
        assert MODULE.strict_finite_number(value) is None


def test_reconciliation_uses_scale_aware_tolerance_but_not_material_slack():
    assert MODULE.numbers_close(1_000_000_000.0, 1_000_000_000.01)
    assert not MODULE.numbers_close(100.0, 100.1)


def test_fact_period_uses_financial_ledger_vocabulary():
    assert MODULE.financial_fact_period({"fiscal_year": "2025", "fiscal_period": "FY"}) == "FY2025"
    assert MODULE.financial_fact_period({"fiscal_year": "2025", "fiscal_period": "Q2"}) == "2025Q2"
    assert MODULE.financial_fact_period({"period_end": "2025-06-30"}) == "2025-06-30"
