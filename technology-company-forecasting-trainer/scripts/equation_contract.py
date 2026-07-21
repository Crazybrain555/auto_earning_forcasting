#!/usr/bin/env python3
"""Shared arithmetic and period primitives for the forecasting contracts.

These functions are intentionally small.  They define the numeric semantics
used by accounting bridges, named scenarios, integrated statements and narrow
scope materiality tests so those views cannot each invent their own tolerance,
period vocabulary or reported-profit identity.
"""
from __future__ import annotations

import math
import re
from collections.abc import Mapping


PROFIT_CHAIN_FIELDS = (
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


def finite_number(value: object) -> float | None:
    """Return a finite float while rejecting booleans and empty values."""

    if value is None or isinstance(value, bool):
        return None
    text = str(value).strip()
    if not text:
        return None
    try:
        number = float(text)
    except (TypeError, ValueError):
        return None
    return number if math.isfinite(number) else None


def strict_finite_number(value: object) -> float | None:
    """Return a finite authored JSON number without coercing another type.

    CSV-backed contracts intentionally use :func:`finite_number` because CSV
    cells arrive as strings.  Authored JSON contracts must preserve their type
    boundary: booleans and numeric-looking strings are not JSON numbers, and
    NaN/Infinity are not finite values even though Python's JSON parser accepts
    them by default.
    """

    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    try:
        number = float(value)
    except (OverflowError, TypeError, ValueError):
        return None
    return number if math.isfinite(number) else None


# Descriptive alias for callers that want to make the JSON/CSV distinction
# explicit.  Keep one implementation so all authored-number checks share the
# same semantics.
finite_json_number = strict_finite_number


def numbers_close(
    left: object,
    right: object,
    *,
    relative_tolerance: float = 1e-9,
    absolute_tolerance: float = 1e-6,
) -> bool:
    """Compare financial numbers with one scale-aware, non-material tolerance."""

    left_number = finite_number(left)
    right_number = finite_number(right)
    if left_number is None or right_number is None:
        return False
    return math.isclose(
        left_number,
        right_number,
        rel_tol=relative_tolerance,
        abs_tol=absolute_tolerance,
    )


def explicit_boolean(value: object) -> bool | None:
    """Parse an explicit boolean declaration without treating blanks as false."""

    if isinstance(value, bool):
        return value
    text = str(value or "").strip().lower()
    if text in {"true", "1", "yes"}:
        return True
    if text in {"false", "0", "no"}:
        return False
    return None


def validate_partition_reconciliation(
    *,
    label: str,
    parent_value: object,
    member_values: list[object],
    exhaustive: object,
    mutually_exclusive: object,
    declared_residual: object = None,
    require_parent_reconciliation: bool = False,
) -> list[str]:
    """Validate one declared partition and recompute its aggregation residual.

    A list of customers, products, regions or segments is not automatically a
    partition.  Only a scope explicitly declared both exhaustive and mutually
    exclusive may be reconciled to its parent.  Partial leader tables and
    overlapping analytical views remain valid evidence, but they cannot claim
    a 100% tie-out.  For a full partition, the residual is recomputed from the
    members rather than trusted from a green status cell.  Arithmetic closure
    uses :func:`numbers_close`; a percentage of the parent is not a precision
    contract.
    """

    problems: list[str] = []
    exhaustive_flag = explicit_boolean(exhaustive)
    exclusive_flag = explicit_boolean(mutually_exclusive)
    if exhaustive_flag is None:
        problems.append(f"{label}: partition_exhaustive must be explicitly true or false")
    if exclusive_flag is None:
        problems.append(
            f"{label}: partition_mutually_exclusive must be explicitly true or false"
        )
    if exhaustive_flag is None or exclusive_flag is None:
        return problems

    is_full_partition = exhaustive_flag and exclusive_flag
    if require_parent_reconciliation and not is_full_partition:
        problems.append(
            f"{label}: parent reconciliation requires a partition declared both "
            "exhaustive and mutually exclusive"
        )
        return problems
    if not is_full_partition:
        if finite_number(declared_residual) is not None:
            problems.append(
                f"{label}: a partial or overlapping view cannot declare a parent residual"
            )
        # A non-exhaustive but mutually exclusive leader table need not equal
        # its parent; it still cannot consume more than the parent.  An
        # explicitly overlapping view has no additive upper-bound semantics.
        if exclusive_flag:
            parent = finite_number(parent_value)
            members = [finite_number(value) for value in member_values]
            if parent is None:
                problems.append(
                    f"{label}: mutually exclusive partial partition parent_value must be numeric"
                )
            elif not members or any(value is None for value in members):
                problems.append(
                    f"{label}: mutually exclusive partial partition members must be non-empty and numeric"
                )
            else:
                member_sum = sum(value for value in members if value is not None)
                if member_sum > parent and not numbers_close(member_sum, parent):
                    problems.append(
                        f"{label}: mutually exclusive partial member sum {member_sum:g} "
                        f"exceeds parent {parent:g}"
                    )
        return problems

    parent = finite_number(parent_value)
    members = [finite_number(value) for value in member_values]
    if parent is None:
        problems.append(f"{label}: full partition parent_value must be numeric")
        return problems
    if not members or any(value is None for value in members):
        problems.append(f"{label}: full partition members must be non-empty and numeric")
        return problems

    recomputed = sum(value for value in members if value is not None) - parent
    member_sum = parent + recomputed
    if not numbers_close(member_sum, parent):
        problems.append(
            f"{label}: member sum {member_sum:g} does not reconcile to "
            f"parent {parent:g} under the shared numeric tolerance contract"
        )
    declared = finite_number(declared_residual)
    if declared is None:
        problems.append(f"{label}: full partition declared_residual must be numeric")
    elif not numbers_close(declared, recomputed):
        problems.append(
            f"{label}: declared residual {declared:g} does not equal "
            f"recomputed residual {recomputed:g}"
        )
    return problems


def validate_profit_chain_equations(
    row: Mapping[str, object],
    *,
    label: str,
) -> list[str]:
    """Recompute the complete reported-profit chain from one scenario row."""

    values = {
        field: strict_finite_number(row.get(field)) for field in PROFIT_CHAIN_FIELDS
    }
    missing = [field for field, value in values.items() if value is None]
    if missing:
        return [
            f"{label}: profit-chain fields must be finite authored JSON numbers: "
            + ",".join(missing)
        ]

    problems: list[str] = []
    if not numbers_close(
        values["operating_profit"],
        values["revenue"] - values["operating_costs_and_expenses"],
    ):
        problems.append(f"{label}: operating profit does not reconcile")
    if not numbers_close(
        values["pretax_profit"],
        values["operating_profit"] + values["nonoperating_income_expense_net"],
    ):
        problems.append(f"{label}: pretax profit does not reconcile")
    if not numbers_close(
        values["net_income"],
        values["pretax_profit"] - values["tax_expense"],
    ):
        problems.append(f"{label}: tax to consolidated net income does not reconcile")
    if not numbers_close(
        values["net_income_attributable"],
        values["net_income"]
        - values["net_income_attributable_to_noncontrolling_interests"],
    ):
        problems.append(f"{label}: NCI to attributable net income does not reconcile")
    return problems


def financial_fact_period(row: Mapping[str, object]) -> str | None:
    """Map the financial-fact ledger vocabulary to a bridge period key."""

    explicit = str(row.get("period") or "").strip()
    if explicit:
        return explicit
    fiscal_year = str(row.get("fiscal_year") or "").strip()
    fiscal_period = str(row.get("fiscal_period") or "").strip().upper()
    if fiscal_year and fiscal_period:
        normalized_year = fiscal_year.removeprefix("FY")
        if fiscal_period == "FY":
            return f"FY{normalized_year}"
        if re.fullmatch(r"(?:Q[1-4]|H[1-2]|M(?:0?[1-9]|1[0-2]))", fiscal_period):
            return f"{normalized_year}{fiscal_period}"
    period_end = str(row.get("period_end") or "").strip()
    return period_end or None


def period_sort_key(period: object) -> tuple[int, int, str]:
    """Order annual, half-year, quarter and month labels deterministically."""

    normalized = re.sub(r"[\s_-]+", "", str(period or "").upper())
    year_match = re.search(r"20\d{2}", normalized)
    year = int(year_match.group(0)) if year_match else 9999
    subperiod = 12
    quarter = re.search(r"Q([1-4])", normalized)
    half = re.search(r"H([1-2])", normalized)
    month = re.search(r"M(0?[1-9]|1[0-2])", normalized)
    if quarter:
        subperiod = int(quarter.group(1)) * 3
    elif half:
        subperiod = int(half.group(1)) * 6
    elif month:
        subperiod = int(month.group(1))
    return year, subperiod, normalized


def shock_activation_position(
    shock: Mapping[str, object],
    period_positions: Mapping[str, int],
) -> int | None:
    """Resolve the first modeled period affected by a dated, lagged shock."""

    effective_period = str(shock.get("effective_period") or "").strip()
    if effective_period in period_positions:
        base_position = period_positions[effective_period]
    else:
        effective_year = period_sort_key(effective_period)[0]
        candidates = [
            position
            for period, position in period_positions.items()
            if period_sort_key(period)[0] == effective_year
        ]
        if not candidates:
            return None
        base_position = min(candidates)
    lag = shock.get("lag_periods")
    if not isinstance(lag, int) or isinstance(lag, bool) or lag < 0:
        return None
    return base_position + lag
