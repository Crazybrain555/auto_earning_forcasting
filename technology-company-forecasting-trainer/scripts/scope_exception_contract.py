#!/usr/bin/env python3
"""Typed contract for proportionate, genuinely narrow research exceptions.

This module does not decide whether a missing schedule is immaterial.  It only
prevents the several ``*_relaxed`` compatibility switches and lowered research
floors from silently waiving a full-company forecast.  A caller supplies the
specific exceptions it is trying to use; the same contract is shared by the
delivery and research-completeness validators.
"""
from __future__ import annotations

import sys
from pathlib import Path
from typing import Iterable

_SCRIPT_DIR = Path(__file__).resolve().parent
if str(_SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPT_DIR))

from equation_contract import finite_number, numbers_close


ALLOWED_SCOPE_TYPES = {
    "single_accounting_event",
    "single_segment",
    "single_patent_family",
    "single_driver_audit",
    "single_data_series_audit",
}
NON_DECISION_READY = {"screen-grade", "not-decision-ready"}
REQUIRED_BLOCKED_CONCLUSIONS = {
    "full_company_revenue",
    "full_company_operating_profit",
    "full_company_gaap_net_income",
    "full_company_intrinsic_value",
}
STATEMENT_PREFIXES = {
    "income_statement",
    "balance_sheet",
    "cash_flow_statement",
}


def _finite(value: object) -> bool:
    return finite_number(value) is not None


def _nonempty(value: object, minimum: int = 1) -> bool:
    return isinstance(value, str) and len(value.strip()) >= minimum


def _string_set(value: object) -> set[str]:
    if not isinstance(value, list):
        return set()
    return {item.strip() for item in value if isinstance(item, str) and item.strip()}


def validate_narrow_scope_exception(
    manifest: dict,
    *,
    requested_exceptions: Iterable[str],
) -> list[str]:
    """Return contract errors for any requested waiver-like behavior.

    An active scope declaration is always validated.  A caller that lowers a
    floor or uses a relaxed flag must also declare an active contract.  In both
    cases the decision contract itself must be narrow, cap readiness, quantify
    one perturbation and explicitly block all full-company earnings and value
    conclusions.  A second runtime mode is neither necessary nor sufficient.
    """

    requested = sorted({str(item).strip() for item in requested_exceptions if str(item).strip()})
    contract = manifest.get("narrow_scope_exception")
    contract_active = isinstance(contract, dict) and contract.get("status") == "active"
    if not requested and not contract_active:
        return []

    errors: list[str] = []
    purpose = str(manifest.get("purpose") or "").strip().lower()
    readiness = str(
        manifest.get("readiness_result") or manifest.get("readiness_target") or ""
    ).strip().lower()
    if any(token in purpose for token in ("full-company", "full company", "five-year", "whole company")):
        errors.append("full-company purpose cannot be renamed into a narrow exception")
    if readiness not in NON_DECISION_READY:
        errors.append(
            "narrow exception readiness must be capped at screen-grade or not-decision-ready"
        )

    if not isinstance(contract, dict) or contract.get("status") != "active":
        errors.append(
            "requested exceptions " + ",".join(requested)
            + " require narrow_scope_exception.status=active"
        )
        return errors

    if contract.get("scope_type") not in ALLOWED_SCOPE_TYPES:
        errors.append(
            "narrow_scope_exception.scope_type must be one of "
            + ",".join(sorted(ALLOWED_SCOPE_TYPES))
        )
    if not _nonempty(contract.get("scope_description"), 40):
        errors.append("narrow_scope_exception.scope_description must state a specific bounded scope")
    cap = str(contract.get("readiness_cap") or "").strip().lower()
    if cap not in NON_DECISION_READY or readiness not in NON_DECISION_READY:
        errors.append("narrow_scope_exception.readiness_cap cannot authorize research-grade")

    blocked = _string_set(contract.get("blocked_full_company_conclusions"))
    missing_blocked = sorted(REQUIRED_BLOCKED_CONCLUSIONS - blocked)
    if missing_blocked:
        errors.append(
            "narrow_scope_exception.blocked_full_company_conclusions missing "
            + ",".join(missing_blocked)
        )

    links = _string_set(contract.get("affected_statement_links"))
    invalid_links = {
        link for link in links
        if "." not in link
        or link.split(".", 1)[0] not in STATEMENT_PREFIXES
        or not link.split(".", 1)[1].strip()
    }
    if not links or invalid_links:
        errors.append(
            "narrow_scope_exception.affected_statement_links needs named statement.field links"
        )

    test = contract.get("materiality_test")
    if not isinstance(test, dict):
        errors.append("narrow_scope_exception.materiality_test is required")
        return errors
    for field in ("affected_metric", "unit", "perturbation_name"):
        if not _nonempty(test.get(field), 3):
            errors.append(f"narrow_scope_exception.materiality_test.{field} is required")
    for field in (
        "baseline_value",
        "perturbation_value",
        "perturbed_value",
        "impact_value",
        "decision_threshold",
    ):
        if not _finite(test.get(field)):
            errors.append(f"narrow_scope_exception.materiality_test.{field} must be finite numeric")
    numeric_fields = (
        test.get("baseline_value"),
        test.get("perturbed_value"),
        test.get("impact_value"),
        test.get("decision_threshold"),
    )
    if all(_finite(value) for value in numeric_fields):
        baseline, perturbed, impact, threshold = map(float, numeric_fields)
        if not numbers_close(perturbed - baseline, impact):
            errors.append(
                "narrow_scope_exception.materiality_test impact_value must equal perturbed_value - baseline_value"
            )
        if threshold <= 0:
            errors.append("narrow_scope_exception.materiality_test.decision_threshold must be > 0")
        expected = "above_threshold" if abs(impact) >= threshold else "below_threshold"
        if test.get("result") != expected:
            errors.append(
                "narrow_scope_exception.materiality_test.result does not match numeric threshold"
            )
    elif test.get("result") not in {"above_threshold", "below_threshold"}:
        errors.append(
            "narrow_scope_exception.materiality_test.result must be above_threshold or below_threshold"
        )
    return errors
