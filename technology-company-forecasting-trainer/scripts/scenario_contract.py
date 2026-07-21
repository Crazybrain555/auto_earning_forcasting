#!/usr/bin/env python3
"""Shared authored-scenario identity, role, probability, and value contracts."""
from __future__ import annotations

import math
import re
from collections.abc import Mapping
from types import MappingProxyType

from equation_contract import numbers_close, strict_finite_number


SCENARIO_ROLES = frozenset({"reference", "alternative"})


class ScenarioCatalog:
    """Immutable lookup surface derived only from ``scenario_set.json``."""

    __slots__ = ("ids", "reference_id", "probabilities", "roles")

    def __init__(
        self,
        *,
        ids: set[str],
        reference_id: str,
        probabilities: dict[str, float],
        roles: dict[str, str],
    ) -> None:
        self.ids = frozenset(ids)
        self.reference_id = reference_id
        self.probabilities = MappingProxyType(dict(probabilities))
        self.roles = MappingProxyType(dict(roles))


def validate_scenario_role_semantics(scenarios: object) -> list[str]:
    """Validate roles without imposing scenario names or a rival-count proxy."""

    if not isinstance(scenarios, list) or not scenarios:
        return ["scenario set must contain an authored reference path"]

    problems: list[str] = []
    reference_ids: list[str] = []
    for index, scenario in enumerate(scenarios, 1):
        if not isinstance(scenario, Mapping):
            problems.append(f"scenario-{index}: scenario must be an object")
            continue
        raw_id = scenario.get("id")
        scenario_id = raw_id.strip() if isinstance(raw_id, str) else ""
        label = scenario_id or f"scenario-{index}"
        raw_role = scenario.get("role")
        role = raw_role.strip().lower() if isinstance(raw_role, str) else ""
        if role not in SCENARIO_ROLES:
            problems.append(f"{label}: role must be reference or alternative")
            continue
        if role == "reference":
            reference_ids.append(scenario_id)
        else:
            shocks = scenario.get("shocks")
            if not isinstance(shocks, list) or not shocks:
                problems.append(
                    f"{label}: alternative scenario must name at least one causal shock "
                    "to an assumption/state node"
                )

    if len(reference_ids) != 1:
        problems.append(
            "scenario set must contain exactly one reference role; "
            f"found {len(reference_ids)}"
        )
    return problems


def parse_scenario_catalog(
    payload: object,
) -> tuple[ScenarioCatalog | None, list[str]]:
    """Parse the sole catalog for scenario IDs, roles, and probabilities."""

    if not isinstance(payload, Mapping):
        return None, ["scenario_set must be an object"]
    scenarios = payload.get("scenarios")
    if not isinstance(scenarios, list) or not scenarios:
        return None, ["scenario set must contain an authored reference path"]

    problems = validate_scenario_role_semantics(scenarios)
    ids: set[str] = set()
    roles: dict[str, str] = {}
    probabilities: dict[str, float] = {}
    reference_ids: list[str] = []

    for index, scenario in enumerate(scenarios, 1):
        if not isinstance(scenario, Mapping):
            continue
        raw_id = scenario.get("id")
        scenario_id = raw_id.strip() if isinstance(raw_id, str) else ""
        label = scenario_id or f"scenario-{index}"
        if not scenario_id:
            problems.append(f"{label}: scenario id must be a non-blank string")
        elif scenario_id in ids:
            problems.append(f"duplicate scenario id {scenario_id}")
        else:
            ids.add(scenario_id)

        raw_role = scenario.get("role")
        role = raw_role.strip().lower() if isinstance(raw_role, str) else ""
        if scenario_id and role in SCENARIO_ROLES and scenario_id not in roles:
            roles[scenario_id] = role
            if role == "reference":
                reference_ids.append(scenario_id)

        probability = strict_finite_number(scenario.get("probability"))
        if probability is None:
            problems.append(
                f"{label}: probability must be a finite authored JSON number between 0 and 1"
            )
        elif not 0.0 <= probability <= 1.0:
            problems.append(f"{label}: probability {probability} must be between 0 and 1")
        elif scenario_id and scenario_id not in probabilities:
            probabilities[scenario_id] = probability

    # validate_scenario_role_semantics owns the human-readable role error.  This
    # guard also prevents constructing a catalog from duplicate/blank IDs.
    if len(reference_ids) != 1 and not any(
        "exactly one reference" in problem for problem in problems
    ):
        problems.append(
            "scenario set must contain exactly one reference role; "
            f"found {len(reference_ids)}"
        )

    if len(probabilities) == len(scenarios):
        probability_sum = math.fsum(probabilities.values())
        if not math.isclose(probability_sum, 1.0, rel_tol=0.0, abs_tol=1e-6):
            problems.append(
                f"scenario probabilities sum to {probability_sum:.12g}, not 1"
            )

    if problems:
        return None, problems
    return (
        ScenarioCatalog(
            ids=ids,
            reference_id=reference_ids[0],
            probabilities=probabilities,
            roles=roles,
        ),
        [],
    )


# Compatibility spelling for callers that describe this as a build operation.
build_scenario_catalog = parse_scenario_catalog


def validate_probability_view(
    view: object,
    catalog: ScenarioCatalog,
    *,
    label: str = "scenario probability view",
) -> list[str]:
    """Require a probability view to be a typed, exact catalog projection."""

    if not isinstance(view, Mapping):
        return [f"{label}: probabilities must be an object"]

    problems: list[str] = []
    raw_keys = set(view)
    non_string_keys = [key for key in raw_keys if not isinstance(key, str)]
    if non_string_keys:
        problems.append(f"{label}: probability keys must be scenario-id strings")
    keys = {key for key in raw_keys if isinstance(key, str)}
    missing = sorted(catalog.ids - keys)
    extra = sorted(keys - catalog.ids)
    if missing:
        problems.append(f"{label}: missing scenario probabilities: {', '.join(missing)}")
    if extra:
        problems.append(f"{label}: unknown scenario probabilities: {', '.join(extra)}")

    parsed: dict[str, float] = {}
    for scenario_id, raw_probability in view.items():
        if not isinstance(scenario_id, str):
            continue
        probability = strict_finite_number(raw_probability)
        if probability is None:
            problems.append(
                f"{label}: {scenario_id} probability must be a finite authored JSON number"
            )
        elif not 0.0 <= probability <= 1.0:
            problems.append(
                f"{label}: {scenario_id} probability {probability} must be between 0 and 1"
            )
        else:
            parsed[scenario_id] = probability

    if set(parsed) == catalog.ids:
        probability_sum = math.fsum(parsed.values())
        if not math.isclose(probability_sum, 1.0, rel_tol=0.0, abs_tol=1e-6):
            problems.append(f"{label}: probabilities sum to {probability_sum:.12g}, not 1")
        for scenario_id, probability in parsed.items():
            if not math.isclose(
                probability,
                catalog.probabilities[scenario_id],
                rel_tol=1e-12,
                abs_tol=1e-12,
            ):
                problems.append(
                    f"{label}: {scenario_id} probability does not match scenario_set"
                )
    return problems


def scenario_references(value: object) -> set[str]:
    """Parse a CSV scenario-reference cell without inventing aliases."""

    if isinstance(value, (list, tuple, set, frozenset)):
        return {str(item).strip() for item in value if str(item).strip()}
    return {
        item.strip()
        for item in re.split(r"[;,|]", str(value or ""))
        if item.strip()
    }


def validate_scenario_references(
    value: object,
    catalog: ScenarioCatalog,
    *,
    label: str,
    required: bool = True,
) -> list[str]:
    """Validate one authored field containing scenario IDs."""

    references = scenario_references(value)
    problems: list[str] = []
    if required and not references:
        problems.append(f"{label}: at least one declared scenario is required")
    unknown = sorted(references - catalog.ids)
    if unknown:
        problems.append(f"{label}: unknown scenario(s): {', '.join(unknown)}")
    return problems


def validate_assumption_scenario_bindings(
    rows: object,
    catalog: ScenarioCatalog,
) -> list[str]:
    """Bind every substantive assumption row to declared scenario identities."""

    if not isinstance(rows, list):
        return ["assumption_register rows must be an array"]
    problems: list[str] = []
    for index, row in enumerate(rows, 2):
        if not isinstance(row, Mapping):
            problems.append(f"assumption_register line {index}: row must be an object")
            continue
        assumption_id = str(row.get("assumption_id") or "").strip()
        label = f"assumption_register {assumption_id or f'line {index}'} scenario"
        problems.extend(
            validate_scenario_references(
                row.get("scenario"),
                catalog,
                label=label,
                required=True,
            )
        )
    return problems


def _executable_values_by_scenario(
    valuation: object,
    catalog: ScenarioCatalog,
) -> dict[str, float]:
    """Return valuation results whose arithmetic is validated today.

    The investment-case validator recomputes the reference
    ``valuation.per_share.value_per_share`` identity.  No per-scenario
    valuation identity exists yet, so a plausibly named free-form block must
    not be promoted to executable evidence.
    """

    if not isinstance(valuation, Mapping):
        return {}
    executable: dict[str, float] = {}
    per_share = valuation.get("per_share")
    if isinstance(per_share, Mapping):
        reference_value = strict_finite_number(per_share.get("value_per_share"))
        if reference_value is not None:
            executable[catalog.reference_id] = reference_value
    return executable


def validate_valuation_summary(
    summary: object,
    valuation: object,
    catalog: ScenarioCatalog,
) -> list[str]:
    """Publish only fair values backed by an executable valuation result."""

    label = "valuation_summary"
    if not isinstance(summary, Mapping):
        return [f"{label} must be an object"]
    fair_values = summary.get("fair_value_by_scenario_id")
    if not isinstance(fair_values, Mapping):
        return [f"{label}.fair_value_by_scenario_id must be an object"]

    problems: list[str] = []
    not_valued_raw = summary.get("not_valued_scenario_ids")
    if (
        not isinstance(not_valued_raw, list)
        or any(not isinstance(item, str) or not item.strip() for item in not_valued_raw)
        or len(set(not_valued_raw or [])) != len(not_valued_raw or [])
    ):
        problems.append(
            f"{label}.not_valued_scenario_ids must be a unique array of scenario IDs"
        )
        not_valued: set[str] = set()
    else:
        not_valued = {item.strip() for item in not_valued_raw}
    reference_raw = summary.get("reference_scenario_id")
    reference_id = reference_raw.strip() if isinstance(reference_raw, str) else ""
    executable = _executable_values_by_scenario(valuation, catalog)
    executable_ids = set(executable)
    fair_value_ids = {
        item for item in fair_values if isinstance(item, str)
    }
    expected_not_valued = set(catalog.ids) - executable_ids
    if fair_value_ids != executable_ids:
        problems.append(
            f"{label}.fair_value_by_scenario_id must exactly project executable valuation IDs"
        )
    if not_valued != expected_not_valued:
        problems.append(
            f"{label}.not_valued_scenario_ids must explicitly name every unexecuted scenario"
        )

    if executable_ids:
        if reference_id != catalog.reference_id:
            problems.append(
                f"{label}.reference_scenario_id must equal reference scenario "
                f"{catalog.reference_id}"
            )
    elif reference_raw is not None:
        problems.append(
            f"{label}.reference_scenario_id must be null when no fair value is executable"
        )

    expected_completeness = (
        "none_executable"
        if not executable_ids
        else "all_authored_scenarios_executable"
        if executable_ids == set(catalog.ids)
        else "reference_only_executable"
    )
    if summary.get("valuation_completeness") != expected_completeness:
        problems.append(
            f"{label}.valuation_completeness must be derived as {expected_completeness}"
        )
    if expected_completeness != "all_authored_scenarios_executable":
        action = str(summary.get("action") or "").strip().lower()
        if action not in {"watch", "human_required", "insufficient_evidence"}:
            problems.append(
                f"{label}.action cannot express an investment decision while authored scenarios are not valued"
            )
        if summary.get("recommended_buy_price") is not None:
            problems.append(
                f"{label}.recommended_buy_price must be null while authored scenarios are not valued"
            )

    for scenario_id, raw_value in fair_values.items():
        if not isinstance(scenario_id, str) or scenario_id not in catalog.ids:
            problems.append(f"{label}: unknown scenario fair value {scenario_id!r}")
            continue
        value = strict_finite_number(raw_value)
        if value is None:
            problems.append(
                f"{label}.{scenario_id} must be a finite authored JSON number"
            )
            continue
        executed_value = executable.get(scenario_id)
        if executed_value is None:
            problems.append(
                f"{label}.{scenario_id} has no executable valuation result"
            )
        elif not numbers_close(value, executed_value):
            problems.append(
                f"{label}.{scenario_id} does not match executable value_per_share"
            )
    return problems
