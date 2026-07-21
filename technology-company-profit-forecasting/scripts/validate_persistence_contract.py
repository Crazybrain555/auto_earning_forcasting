#!/usr/bin/env python3
"""Executable persistence, mean-reversion, cost-behavior and moat contracts."""
from __future__ import annotations

import math
import re
from typing import Iterable


def _finite(value: object) -> bool:
    return (
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and math.isfinite(float(value))
    )


def _text(value: object, minimum: int = 1) -> bool:
    return isinstance(value, str) and len(value.strip()) >= minimum


def _ids(value: object) -> set[str]:
    if isinstance(value, list):
        return {str(item).strip() for item in value if str(item).strip()}
    return {
        item.strip()
        for item in re.split(r"[;,]", str(value or ""))
        if item.strip()
    }


def validate_persistence_analysis(
    payload: object,
    *,
    known_node_ids: set[str],
    main_line_relevant_node_ids: set[str],
    falsification_node_ids: set[str],
    known_source_ids: set[str],
    independent_source_ids: set[str],
    scenario_ids: set[str],
    strict: bool,
) -> list[str]:
    """Validate conditional persistence inputs without imposing a generic fade."""

    if not isinstance(payload, dict):
        return ["persistence_analysis must be an object"] if strict else []
    errors: list[str] = []

    mean = payload.get("mean_reversion")
    if not isinstance(mean, dict):
        errors.append("mean_reversion contract is required")
    else:
        status = str(mean.get("status") or "").strip().lower()
        allowed_statuses = {
            "accepted", "provisional", "human_required", "not_available_with_reason",
        }
        if status not in allowed_statuses:
            errors.append("mean_reversion.status must be typed")
        if status != "accepted":
            if not _text(mean.get("limitations")):
                errors.append("unresolved mean_reversion needs limitations for independent review")
            # Missing or disputed outside-view evidence is preserved rather
            # than converted into a fake numeric prior.  The frozen reviewer
            # decides the readiness consequence; deterministic code has no
            # authority to declare the reference class economically adequate.
            return errors + _validate_cost_behavior(
                payload.get("cost_behavior"),
                known_node_ids=known_node_ids,
                main_line_relevant_node_ids=main_line_relevant_node_ids,
                known_source_ids=known_source_ids,
                scenario_ids=scenario_ids,
            )
        for field in ("object", "unit"):
            if not _text(mean.get(field)):
                errors.append(f"mean_reversion.{field} is required")
        for field in ("reference_class", "sample_selection_limits", "company_departure"):
            if not _text(mean.get(field)):
                errors.append(f"mean_reversion.{field} is required")
        median = mean.get("target_median")
        low = mean.get("target_low")
        high = mean.get("target_high")
        if not all(_finite(item) for item in (low, median, high)):
            errors.append("mean_reversion target distribution needs finite low/median/high")
        elif not float(low) <= float(median) <= float(high):
            errors.append("mean_reversion target distribution must satisfy low <= median <= high")

        sources = _ids(mean.get("reference_class_source_ids"))
        unknown_sources = sorted(sources - known_source_ids)
        if not sources:
            errors.append("mean_reversion reference class needs named source lineage")
        if unknown_sources:
            errors.append("mean_reversion unknown source ids " + ",".join(unknown_sources))

        speed_nodes = _ids(mean.get("speed_driver_node_ids"))
        if not speed_nodes:
            errors.append("mean_reversion.speed_driver_node_ids is required")
        elif speed_nodes - known_node_ids:
            errors.append(
                "mean_reversion unknown speed_driver_node_ids "
                + ",".join(sorted(speed_nodes - known_node_ids))
            )
        elif not (speed_nodes & main_line_relevant_node_ids):
            errors.append("mean_reversion speed_driver_node_ids must connect to the thesis line")
        horizon = mean.get("fade_horizon_periods")
        if horizon is not None and (
            not isinstance(horizon, int) or isinstance(horizon, bool) or horizon <= 0
        ):
            errors.append("mean_reversion.fade_horizon_periods must be a positive integer")

        falsifiers = _ids(mean.get("falsification_node_ids"))
        if not falsifiers:
            errors.append("mean_reversion.falsification_node_ids is required")
        elif falsifiers - falsification_node_ids:
            errors.append(
                "mean_reversion undeclared falsification_node_ids "
                + ",".join(sorted(falsifiers - falsification_node_ids))
            )
        linked_scenarios = _ids(mean.get("scenario_ids"))
        if not linked_scenarios:
            errors.append("mean_reversion must bind a named scenario path")
        if linked_scenarios - scenario_ids:
            errors.append(
                "mean_reversion unknown scenario ids "
                + ",".join(sorted(linked_scenarios - scenario_ids))
            )

    errors.extend(_validate_cost_behavior(
        payload.get("cost_behavior"),
        known_node_ids=known_node_ids,
        main_line_relevant_node_ids=main_line_relevant_node_ids,
        known_source_ids=known_source_ids,
        scenario_ids=scenario_ids,
    ))
    return errors


def _validate_cost_behavior(
    costs: object,
    *,
    known_node_ids: set[str],
    main_line_relevant_node_ids: set[str],
    known_source_ids: set[str],
    scenario_ids: set[str],
) -> list[str]:
    """Keep the existing executable cost contract separate from outside-view status."""

    errors: list[str] = []
    if costs is None:
        costs = []
    if not isinstance(costs, list):
        errors.append("cost_behavior must be an array when supplied")
        return errors
    for index, row in enumerate(costs, 1):
        label = f"cost_behavior[{index}]"
        if not isinstance(row, dict):
            errors.append(f"{label} must be an object")
            continue
        materiality = str(row.get("materiality") or "").strip().lower()
        if materiality not in {"critical", "high", "medium", "low"}:
            errors.append(f"{label}.materiality is invalid")
        if materiality not in {"critical", "high"}:
            continue
        status = str(row.get("status") or "").strip().lower()
        if status not in {
            "accepted", "provisional", "human_required", "not_available_with_reason",
        }:
            errors.append(f"{label}.status must be typed")
            continue
        if status != "accepted":
            if not _text(row.get("limitations")):
                errors.append(f"{label} unresolved estimate needs limitations for independent review")
            continue
        for field in ("cost_line", "activity_unit", "floor_unit", "estimation_method", "notes"):
            if not _text(row.get(field)):
                errors.append(f"{label}.{field} is required")
        driver = str(row.get("activity_driver_node_id") or "").strip()
        if driver not in known_node_ids or driver not in main_line_relevant_node_ids:
            errors.append(f"{label}.activity_driver_node_id must be a known thesis-line node")
        for field in ("elasticity_up", "elasticity_down", "committed_resource_floor", "exit_or_adjustment_cost"):
            if not _finite(row.get(field)) or float(row.get(field) or 0) < 0:
                errors.append(f"{label}.{field} must be finite and non-negative")
        lag = row.get("adjustment_lag_periods")
        if not isinstance(lag, int) or isinstance(lag, bool) or lag < 0:
            errors.append(f"{label}.adjustment_lag_periods must be a non-negative integer")
        sources = _ids(row.get("source_ids"))
        if not sources:
            errors.append(f"{label}.source_ids is required")
        if sources - known_source_ids:
            errors.append(f"{label} unknown source ids " + ",".join(sorted(sources - known_source_ids)))
        linked_scenarios = _ids(row.get("scenario_ids"))
        if not linked_scenarios:
            errors.append(f"{label} must bind a named scenario path")
        if linked_scenarios - scenario_ids:
            errors.append(f"{label} unknown scenario ids " + ",".join(sorted(linked_scenarios - scenario_ids)))
    return errors


def validate_moat_rows(
    rows: Iterable[dict[str, object]],
    *,
    known_source_ids: set[str],
    independent_source_ids: set[str],
    known_node_ids: set[str],
    monitor_node_ids: set[str],
) -> list[str]:
    """Validate accepted moat permissions as evidenced persistence claims."""

    errors: list[str] = []
    for index, row in enumerate(rows, 1):
        if str(row.get("status") or "").strip().lower() != "accepted":
            continue
        label = str(row.get("dimension") or f"row {index}").strip()
        sources = _ids(row.get("evidence_source_ids"))
        if not sources:
            errors.append(f"{label}: evidence_source_ids is required")
        if sources - known_source_ids:
            errors.append(f"{label}: unknown source ids " + ",".join(sorted(sources - known_source_ids)))
        drivers = _ids(row.get("driver_node_ids"))
        if not drivers:
            errors.append(f"{label}: driver_node_ids is required")
        if drivers - known_node_ids:
            errors.append(f"{label}: unknown driver nodes " + ",".join(sorted(drivers - known_node_ids)))
        monitors = _ids(row.get("monitor_driver_node_ids"))
        if not monitors:
            errors.append(f"{label}: monitor_driver_node_ids is required")
        if monitors - monitor_node_ids:
            errors.append(f"{label}: unknown monitor nodes " + ",".join(sorted(monitors - monitor_node_ids)))

        for field in ("claim", "forecast_permission", "competitor_response"):
            if not _text(row.get(field)):
                errors.append(f"{label}: {field} is required")
        for field in (
            "roic_or_cash_effect",
            "reinvestment_runway",
            "downside_or_falsification",
            "valuation_sensitivity",
            "monitor_or_kill_trigger",
        ):
            if not _text(row.get(field)):
                errors.append(f"{label}: {field} is required")
        if not str(row.get("fade_schedule_link") or "").strip().startswith("value_creation.fade"):
            errors.append(f"{label}: fade_schedule_link must bind value_creation.fade")
    return errors
