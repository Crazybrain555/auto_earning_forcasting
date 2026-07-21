#!/usr/bin/env python3
"""Validate analytical cohorts for material internally generated intangibles.

The schedule preserves issuer GAAP/IFRS/ASBE reporting and permits a shadow
capitalization view only as a sensitivity or comparability lens. It deliberately
does not decide that R&D, software, content or customer acquisition is an asset.
"""
from __future__ import annotations

import math


ALLOWED_ANALYTICAL_USES = {
    "analytical_sensitivity_only",
    "reference_class_comparability",
}
STATUSES = {"accepted", "not_material_with_reason", "human_required"}


def _finite(value: object) -> bool:
    return (
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and math.isfinite(float(value))
    )


def _text(value: object, minimum: int = 1) -> bool:
    return isinstance(value, str) and len(value.strip()) >= minimum


def _ids(value: object) -> set[str]:
    if not isinstance(value, list):
        return set()
    return {str(item).strip() for item in value if str(item).strip()}


def _close(left: object, right: object, scale: float = 1.0) -> bool:
    return _finite(left) and _finite(right) and math.isclose(
        float(left),
        float(right),
        rel_tol=1e-7,
        abs_tol=max(1e-8, abs(scale) * 1e-7),
    )


def validate_internal_intangible_schedule(
    payload: object,
    *,
    known_source_ids: set[str],
    known_node_ids: set[str],
    scenario_ids: set[str],
    accounting_basis_id: str,
    readiness: str,
    strict: bool,
) -> list[str]:
    """Return contract errors without manufacturing an economic life estimate."""

    if not isinstance(payload, dict):
        return ["internal intangible investment schedule must be an object"] if strict else []
    errors: list[str] = []
    if payload.get("schema_version") != "internal-intangible-investment/v1":
        errors.append("internal intangible investment schema_version is invalid")
    threshold = payload.get("materiality_threshold_pct_revenue")
    if not _finite(threshold) or float(threshold) <= 0:
        errors.append("materiality_threshold_pct_revenue must be finite and positive")
        threshold_value = 0.0
    else:
        threshold_value = float(threshold)
    categories = payload.get("categories")
    if not isinstance(categories, list) or not categories:
        return errors + ["internal intangible investment categories are required"]

    seen: set[str] = set()
    for index, category in enumerate(categories, 1):
        label = f"internal_intangibles.categories[{index}]"
        if not isinstance(category, dict):
            errors.append(f"{label} must be an object")
            continue
        category_id = str(category.get("category_id") or "").strip()
        if not category_id or category_id in seen:
            errors.append(f"{label}.category_id must be non-empty and unique")
        seen.add(category_id)
        status = str(category.get("status") or "").strip()
        if status not in STATUSES:
            errors.append(f"{label}.status is invalid")
            continue
        if status == "human_required":
            sources = _ids(category.get("source_ids"))
            if not _text(category.get("reason"), 30) or not sources:
                errors.append(f"{label} human_required needs a reason and source_ids")
            if sources - known_source_ids:
                errors.append(f"{label} has unknown source_ids")
            if str(readiness).lower() == "research-grade":
                errors.append(f"{label} unresolved material internal investment caps readiness")
            continue
        if status == "not_material_with_reason":
            sources = _ids(category.get("source_ids"))
            if not _text(category.get("reason"), 30) or not sources:
                errors.append(f"{label} not-material status needs a substantive reason and source_ids")
            if sources - known_source_ids:
                errors.append(f"{label} has unknown source_ids")
            test = category.get("materiality_test")
            if not isinstance(test, dict):
                errors.append(f"{label}.materiality_test is required")
                continue
            amount, revenue, pct = (
                test.get("amount"),
                test.get("revenue"),
                test.get("pct_revenue"),
            )
            if not all(_finite(item) for item in (amount, revenue, pct)) or float(revenue or 0) <= 0:
                errors.append(f"{label}.materiality_test needs finite amount/revenue/pct_revenue")
                continue
            expected_pct = abs(float(amount)) / abs(float(revenue)) * 100.0
            if not _close(pct, expected_pct, expected_pct):
                errors.append(f"{label}.materiality_test.pct_revenue is not recomputable")
            if expected_pct > threshold_value + 1e-9:
                errors.append(f"{label} not-material amount is not below the materiality threshold")
            continue

        if category.get("accounting_basis_id") != accounting_basis_id:
            errors.append(f"{label}.accounting_basis_id does not match the issuer reporting basis")
        if not _text(category.get("reported_policy"), 30):
            errors.append(f"{label}.reported_policy must preserve the issuer accounting treatment")
        policy_sources = _ids(category.get("policy_source_ids"))
        life_sources = _ids(category.get("economic_life_source_ids"))
        if not policy_sources or policy_sources - known_source_ids:
            errors.append(f"{label}.policy_source_ids must be known")
        if not life_sources or life_sources - known_source_ids:
            errors.append(f"{label}.economic_life_source_ids must be known and non-empty")
        if category.get("allowed_use") not in ALLOWED_ANALYTICAL_USES:
            errors.append(
                f"{label} shadow capitalization is analytical sensitivity only and cannot overwrite reported GAAP Base"
            )
        if not _text(category.get("product_or_program"), 3):
            errors.append(f"{label}.product_or_program is required")
        nodes = _ids(category.get("driver_node_ids"))
        if not nodes or nodes - known_node_ids:
            errors.append(f"{label}.driver_node_ids must be known")
        if not _ids(category.get("commercialization_gate_ids")):
            errors.append(f"{label}.commercialization_gate_ids is required")
        linked_scenarios = _ids(category.get("scenario_ids"))
        if not linked_scenarios or linked_scenarios - scenario_ids:
            errors.append(f"{label}.scenario_ids must bind the selected known model paths")
        if not _text(category.get("notes"), 30):
            errors.append(f"{label}.notes must state the analytical limitation")

        cohorts = category.get("cohorts")
        if not isinstance(cohorts, list) or not cohorts:
            errors.append(f"{label}.cohorts is required")
            continue
        cohort_ids: set[str] = set()
        for cohort_index, cohort in enumerate(cohorts, 1):
            row_label = f"{label}.cohorts[{cohort_index}]"
            if not isinstance(cohort, dict):
                errors.append(f"{row_label} must be an object")
                continue
            cohort_id = str(cohort.get("cohort_id") or "").strip()
            if not cohort_id or cohort_id in cohort_ids:
                errors.append(f"{row_label}.cohort_id must be non-empty and unique")
            cohort_ids.add(cohort_id)
            for field in ("vintage_period", "currency"):
                if not _text(cohort.get(field), 3):
                    errors.append(f"{row_label}.{field} is required")
            numeric_fields = (
                "revenue", "reported_expense", "reported_capitalized",
                "total_internal_investment", "materiality_pct_revenue",
                "economic_life_low", "economic_life_base", "economic_life_high",
                "attrition_or_obsolescence_rate", "maintenance_share", "growth_share",
                "opening_shadow_asset", "new_shadow_investment", "shadow_amortization",
                "shadow_writeoff", "closing_shadow_asset", "after_tax_expense_addback",
                "after_tax_shadow_amortization", "reported_nopat", "adjusted_nopat",
                "average_reported_invested_capital", "average_shadow_asset",
                "average_adjusted_invested_capital", "adjusted_roic",
            )
            missing = [field for field in numeric_fields if not _finite(cohort.get(field))]
            if missing:
                errors.append(f"{row_label} missing finite fields " + ",".join(missing))
                continue
            revenue = float(cohort["revenue"])
            total = float(cohort["total_internal_investment"])
            if revenue == 0:
                errors.append(f"{row_label}.revenue cannot be zero")
            if not _close(total, float(cohort["reported_expense"]) + float(cohort["reported_capitalized"]), total):
                errors.append(f"{row_label} total investment does not equal reported expense plus capitalized")
            expected_materiality = abs(total) / abs(revenue) * 100.0 if revenue else math.inf
            if not _close(cohort["materiality_pct_revenue"], expected_materiality, expected_materiality):
                errors.append(f"{row_label}.materiality_pct_revenue is not recomputable")
            low, base, high = (
                float(cohort["economic_life_low"]),
                float(cohort["economic_life_base"]),
                float(cohort["economic_life_high"]),
            )
            if low <= 0 or not low <= base <= high:
                errors.append(f"{row_label} economic life must satisfy 0 < low <= base <= high")
            attrition = float(cohort["attrition_or_obsolescence_rate"])
            if not 0 <= attrition <= 1:
                errors.append(f"{row_label}.attrition_or_obsolescence_rate must be between 0 and 1")
            if not _close(
                float(cohort["maintenance_share"]) + float(cohort["growth_share"]),
                1.0,
            ):
                errors.append(f"{row_label} maintenance_share + growth_share must equal 1")
            expected_close = (
                float(cohort["opening_shadow_asset"])
                + float(cohort["new_shadow_investment"])
                - float(cohort["shadow_amortization"])
                - float(cohort["shadow_writeoff"])
            )
            if not _close(cohort["closing_shadow_asset"], expected_close, expected_close):
                errors.append(f"{row_label} shadow asset roll does not close")
            expected_nopat = (
                float(cohort["reported_nopat"])
                + float(cohort["after_tax_expense_addback"])
                - float(cohort["after_tax_shadow_amortization"])
            )
            if not _close(cohort["adjusted_nopat"], expected_nopat, expected_nopat):
                errors.append(f"{row_label}.adjusted_nopat is not recomputable")
            expected_capital = (
                float(cohort["average_reported_invested_capital"])
                + float(cohort["average_shadow_asset"])
            )
            if not _close(cohort["average_adjusted_invested_capital"], expected_capital, expected_capital):
                errors.append(f"{row_label}.average_adjusted_invested_capital is not recomputable")
            expected_roic = expected_nopat / expected_capital if expected_capital else math.inf
            if not _close(cohort["adjusted_roic"], expected_roic, expected_roic):
                errors.append(f"{row_label}.adjusted_roic is not recomputable")
    return errors
