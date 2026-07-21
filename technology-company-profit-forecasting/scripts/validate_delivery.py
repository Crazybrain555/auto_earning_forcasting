#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import datetime as dt
import hashlib
import json
import math
import re
import sys
import subprocess
from pathlib import Path

_SCRIPT_DIR = Path(__file__).resolve().parent
if str(_SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPT_DIR))

from equation_contract import (
    PROFIT_CHAIN_FIELDS,
    explicit_boolean,
    financial_fact_period,
    finite_number as contract_finite_number,
    numbers_close,
    period_sort_key,
    shock_activation_position as resolve_shock_activation_position,
    strict_finite_number,
    validate_partition_reconciliation,
    validate_profit_chain_equations,
)
from artifact_registry import (
    load_registry,
    required_artifact_view_diagnostics,
    resolve_active_artifacts,
    validate_manifest_routes,
    validate_registry,
)
from provenance_contract import (
    canonical_observation_fingerprint,
    source_epistemic_class,
    source_epistemic_class_problems,
    source_origin_record_kind,
)
from publication_contract import PublicationContractError, validated_input_pack_hash
from scope_exception_contract import validate_narrow_scope_exception
from scenario_contract import (
    parse_scenario_catalog,
    validate_assumption_scenario_bindings,
    validate_probability_view,
    validate_scenario_role_semantics,
    validate_valuation_summary,
)
from runtime_context import load_profile, skill_root_from_script
from validate_internal_intangibles import validate_internal_intangible_schedule
from validate_persistence_contract import validate_persistence_analysis
from workbook_contract import (
    parse_workbook,
    validate_model_check_bindings,
    validate_scenario_workbook_bindings,
)


V2_FORBIDDEN_FIELDS = {
    "mechanism_weights",
    "archetype_weights",
    "materiality_weight",
    "company_lenses",
    "independence_weight",
}

ACCOUNTING_FRAMEWORKS = {"US_GAAP", "IFRS", "PRC_GAAP", "OTHER_LOCAL_GAAP"}
ACCOUNTING_POLICY_FORBIDDEN_KEYS = {
    "assumption_id",
    "driver_id",
    "driver_node_id",
    "driver_node_ids",
    "parameter",
    "parameter_value",
    "weight",
}

def parse_datetime(value: str) -> dt.datetime:
    value = value.strip()
    if value.endswith("Z"):
        value = value[:-1] + "+00:00"
    parsed = dt.datetime.fromisoformat(value)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=dt.timezone.utc)
    return parsed.astimezone(dt.timezone.utc)


CELL_REFERENCE_RE = re.compile(
    r"^(?:'[^']+'|[A-Za-z_][A-Za-z0-9_ ]*)!\$?[A-Z]{1,3}\$?[1-9][0-9]*$"
)
CELL_REFERENCE_SEARCH_RE = re.compile(
    r"(?:'[^']+'|[A-Za-z_][A-Za-z0-9_ ]*)!\$?[A-Z]{1,3}\$?[1-9][0-9]*"
)
MONITOR_OPERATORS = {
    "below", "above", "equal", "not_equal", "at_or_below", "at_or_above",
    "crosses_below", "crosses_above",
}
INDUSTRY_PROFIT_POOL_ROW_TYPES = {"total", "component", "residual"}
OPERATING_CYCLE_MATERIALITY_BASES = {
    "entity_boundary",
    "business_model_boundary",
    "contractual_boundary",
    "financial_statement_immateriality",
    "sensitivity_below_threshold",
}
OPERATING_CYCLE_EQUATION_TYPES = {
    "channel_inventory_roll",
    "company_inventory_roll",
    "revenue_recognition",
}
OPERATING_CYCLE_EQUATION_STATUSES = {
    "accepted",
    "disclosure_limited",
    "not_applicable",
}
EARNINGS_POWER_LAYER_ORDER = (
    "revenue",
    "core_operating_profit",
    "gaap_operating_profit",
    "pretax_profit",
    "gaap_net_income_attributable",
)
EARNINGS_POWER_LAYERS = set(EARNINGS_POWER_LAYER_ORDER)
HISTORICAL_KEY_FIELDS = (
    "revenue",
    "cost",
    "gross_profit",
    "operating_profit",
    "gaap_net_income_attributable",
)
HISTORICAL_PERIOD_TYPES = {"annual", "interim", "first_forecast"}
HISTORICAL_PERIOD_STATE = {
    "annual": "actual",
    "interim": "actual",
    "first_forecast": "forecast",
}
HISTORICAL_ROW_TYPES = {"consolidated", "segment", "elimination"}
HISTORICAL_DATA_STATUSES = {
    "reported", "derived", "bridged", "disclosure_limited", "not_applicable"
}
HISTORICAL_COMPARABILITY_STATUSES = {
    "comparable", "bridged", "disclosure_limited", "not_applicable"
}
HISTORICAL_SEGMENT_RECONCILIATION_STATUSES = {
    "reconciled", "single_segment", "disclosure_limited", "not_applicable"
}
HISTORICAL_LOW_READINESS = {"not-decision-ready", "screen-grade"}


def _valid_iso_date(value: object) -> bool:
    text = str(value or "").strip()
    if not text:
        return False
    try:
        if "T" in text or text.endswith("Z"):
            parse_datetime(text)
        else:
            dt.date.fromisoformat(text)
    except Exception:
        return False
    return True


def _numeric_text(value: object) -> bool:
    try:
        float(str(value).strip())
    except Exception:
        return False
    return str(value).strip() != ""


def _split_ids(value: object) -> set[str]:
    return {item.strip() for item in re.split(r"[;,]", str(value or "")) if item.strip()}


def _truthy(value: object) -> bool:
    return str(value or "").strip().lower() in {"true", "1", "yes", "y"}


def _independent_source(source: dict) -> bool:
    independence = str(source.get("independence") or "").strip().lower()
    if independence in {"independent", "third_party", "third-party", "cross_company"}:
        return True
    source_type = str(source.get("source_type") or "").strip().lower()
    return any(
        token in source_type
        for token in (
            "industry", "research", "paper", "standard", "patent", "expert",
            "customer", "supplier", "competitor", "measurement", "news",
        )
    )


def _causal_upstream_nodes(graph: dict, targets: set[str]) -> set[str]:
    """Expand thesis carriers to their declared causal upstream nodes."""

    reverse: dict[str, set[str]] = {}
    for equation in graph.get("equations", []):
        if not isinstance(equation, dict):
            continue
        output = str(equation.get("output") or "").strip()
        inputs = {
            str(item).strip()
            for item in (equation.get("inputs") or [])
            if str(item).strip()
        }
        if output:
            reverse.setdefault(output, set()).update(inputs)
    pending = list(targets)
    seen: set[str] = set()
    while pending:
        current = pending.pop()
        if current in seen:
            continue
        seen.add(current)
        pending.extend(reverse.get(current, set()) - seen)
    return seen


def _finite_number(value: object) -> float | None:
    return contract_finite_number(value)


def _json_number(value: object) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(float(value))


def _placeholder(value: object) -> bool:
    return str(value or "").strip().upper() in {"", "TBD", "REPLACE", "PENDING"}


CLAIM_TYPES = {
    "reported_fact",
    "derived_fact",
    "management_claim",
    "technical_boundary",
    "analyst_assumption",
    "scenario",
    "unknown",
}
CLAIM_PROPOSITION_SCOPES = {
    "reported_history",
    "current_observed_state",
    "management_view_or_plan",
    "future_execution",
    "external_state",
    "technical_boundary",
    "analyst_inference",
    "causal_interpretation",
    "scenario_only",
}
CLAIM_PREDICTIVE_PROPOSITION_SCOPES = frozenset({
    "future_execution",
    "external_state",
})
CLAIM_ALLOWED_USES = {
    "historical_anchor",
    "base_parameter",
    "technical_bound",
    "scenario_only",
    "monitoring_only",
    "discovery_only",
    "blocked",
}
CLAIM_STATUSES = {"accepted", "contested", "rejected", "human_required"}
CLAIM_LINK_RELATIONS = {"support", "contradict", "context"}
CLAIM_EVIDENCE_FUNCTIONS = {
    "direct_anchor",
    "historical_calibration",
    "causal_test",
    "external_test",
    "context_only",
}
CLAIM_RECONCILIATION_STATUSES = {"not_applicable", "reconciled", "unresolved"}
CLAIM_LINK_FIELDS = (
    "source_id",
    "relation",
    "evidence_function",
    "authority_scope",
    "measurement_or_construct_basis",
    "incentive_conflict",
    "reconciliation_status",
    "permission_rationale",
    "observation_ids",
)
CLAIM_NON_MODEL_USES = {"monitoring_only", "discovery_only", "blocked"}
CLAIM_MODEL_CHANGING_USES = CLAIM_ALLOWED_USES - CLAIM_NON_MODEL_USES
CLAIM_QUANTITATIVE_REFERENCE_USES = {"base_parameter"}
CLAIM_DECLARED_SUBJECTIVE_TYPES = {
    "management_claim",
    "analyst_assumption",
    "scenario",
}
def source_authority_semantics(source: dict) -> set[str]:
    """Map the controlled epistemic class to bounded claim semantics.

    ``source_type`` and ``role`` are retrieval/routing metadata and are
    deliberately excluded from authority decisions.
    """

    epistemic_class = source_epistemic_class(source)
    return {
        "official_reported_fact": {"factual_observation"},
        "independent_external_observation": {"factual_observation"},
        "management_statement_or_plan": {"management", "company_first_party"},
        "expert_or_analyst_opinion": {"expert_or_analyst"},
        "technical_evidence": {"technical"},
        "discovery_only": {"discovery_only"},
    }.get(epistemic_class, set())


def _supporting_source_records(
    claim: dict,
    source_records: dict[str, dict],
) -> list[tuple[dict, dict, set[str]]]:
    supporting: list[tuple[dict, dict, set[str]]] = []
    for link in claim.get("evidence_links") or []:
        if not isinstance(link, dict):
            continue
        if str(link.get("relation") or "").strip() != "support":
            continue
        source_id = str(link.get("source_id") or "").strip()
        source = source_records.get(source_id)
        if isinstance(source, dict):
            supporting.append((link, source, source_authority_semantics(source)))
    return supporting


def claim_requires_independent_authority(
    claim: dict,
    source_records: dict[str, dict] | None = None,
) -> bool:
    """Return whether a subjective proposition can alter an executed model state.

    The boundary is the use, not a preferred vocabulary for the source or the
    scenario.  Monitoring and discovery do not change an authored model state;
    historical anchors, technical bounds, reference parameters and authored
    alternatives do.  The latter therefore require a proposition-specific
    frozen judgment when their author is management or the analyst.
    """

    allowed_use = str(claim.get("allowed_use") or "").strip()
    if allowed_use not in CLAIM_MODEL_CHANGING_USES:
        return False
    proposition_scope = str(claim.get("proposition_scope") or "").strip()
    if proposition_scope in CLAIM_PREDICTIVE_PROPOSITION_SCOPES:
        return True
    if str(claim.get("claim_type") or "").strip() in CLAIM_DECLARED_SUBJECTIVE_TYPES:
        return True
    if not source_records:
        return False
    for _link, _source, semantics in _supporting_source_records(claim, source_records):
        if source_epistemic_class(_source) == "independent_external_observation":
            return True
        if semantics & {"management", "expert_or_analyst"}:
            return True
        if (
            "company_first_party" in semantics
            and proposition_scope in {"future_execution", "external_state"}
        ):
            return True
    return False


_OBSERVATION_EVIDENCE_FUNCTIONS = frozenset({
    "direct_anchor", "historical_calibration", "causal_test", "external_test",
})
_BOUND_SHA256_RE = re.compile(r"^sha256:[0-9a-f]{64}$")


def external_observation_review_binding(
    observation: dict,
    source: dict,
) -> dict[str, str]:
    """Return objective fields an independent review must repeat exactly."""

    return {
        "observation_id": str(observation.get("series_id") or "").strip(),
        "source_id": str(source.get("source_id") or "").strip(),
        "source_content_hash": str(source.get("content_hash") or "").strip(),
        "origin_record_kind": source_origin_record_kind(source),
        "epistemic_class": source_epistemic_class(source),
        "measurement_method_id": str(
            observation.get("measurement_method_id") or ""
        ).strip(),
        "source_locator": str(source.get("location") or "").strip(),
        "fingerprint": canonical_observation_fingerprint(observation),
    }


def external_observation_binding_problems(
    observation: dict,
    source: dict,
    *,
    claim_driver_node_ids: set[str],
    label: str,
) -> list[str]:
    """Validate a separate original observation, not a relabelled document."""

    problems = source_epistemic_class_problems(source, label=f"{label}: source")
    if source_origin_record_kind(source) != "original_measurement_observation":
        problems.append(
            f"{label}: source origin_record_kind must be "
            "original_measurement_observation"
        )
    if source_epistemic_class(source) != "independent_external_observation":
        problems.append(
            f"{label}: source epistemic_class must be independent_external_observation"
        )
    source_id = str(source.get("source_id") or "").strip()
    observation_id = str(observation.get("series_id") or "").strip()
    if _placeholder(observation_id):
        problems.append(f"{label}: observation requires a substantive series_id")
    if str(observation.get("source_id") or "").strip() != source_id:
        problems.append(f"{label}: observation source_id must match its evidence link")
    if str(observation.get("original_source_id") or "").strip() != source_id:
        problems.append(
            f"{label}: observation original_source_id must be the bound original source"
        )
    if str(source.get("root_original_source_id") or "").strip() != source_id:
        problems.append(f"{label}: observation source must be its own original root")
    if source.get("derived_from_source_id") not in {None, ""}:
        problems.append(f"{label}: observation source cannot be a derived commentary record")
    if source.get("common_origin") is not False:
        problems.append(f"{label}: observation source common_origin must be false")
    source_method = str(source.get("measurement_method_id") or "").strip()
    observation_method = str(observation.get("measurement_method_id") or "").strip()
    if _placeholder(observation_method) or observation_method != source_method:
        problems.append(
            f"{label}: observation measurement_method_id must match source provenance"
        )
    source_hash = str(source.get("content_hash") or "").strip()
    if not _BOUND_SHA256_RE.fullmatch(source_hash):
        problems.append(
            f"{label}: original observation source requires a bound sha256 content_hash"
        )
    if _placeholder(source.get("location")):
        problems.append(f"{label}: original observation source requires a durable locator")
    for field in (
        "metric_construct_id", "observation_type", "available_at", "vintage_id",
        "period_start", "period_end", "unit", "entity_scope", "population_coverage",
    ):
        if _placeholder(observation.get(field)):
            problems.append(f"{label}: observation requires substantive {field}")
    if contract_finite_number(observation.get("observation_value")) is None:
        problems.append(f"{label}: observation_value must be finite")
    if str(observation.get("status") or "").strip().casefold() != "accepted":
        problems.append(f"{label}: observation must be accepted")
    observation_nodes = _split_ids(observation.get("driver_node_ids"))
    if not observation_nodes & claim_driver_node_ids:
        problems.append(
            f"{label}: observation driver_node_ids must intersect the claim driver nodes"
        )
    return problems


def _source_can_test_external_execution(
    source: dict,
    link: dict,
    observation_records: dict[str, dict],
    claim_driver_node_ids: set[str],
) -> bool:
    """Return whether a source has a bound original external observation.

    Management is authoritative about its own statements and intent, but it
    cannot independently test its future execution or an external state.  This
    is a proposition boundary, not a document count or source-family list.
    """

    if (
        source_epistemic_class(source) != "independent_external_observation"
        or source_origin_record_kind(source) != "original_measurement_observation"
        or source_epistemic_class_problems(source)
    ):
        return False
    observation_ids = link.get("observation_ids")
    if not isinstance(observation_ids, list) or not observation_ids:
        return False
    source_id = str(source.get("source_id") or "").strip()
    for observation_id in observation_ids:
        observation = observation_records.get(str(observation_id).strip())
        if not isinstance(observation, dict):
            return False
        if external_observation_binding_problems(
            observation,
            source,
            claim_driver_node_ids=claim_driver_node_ids,
            label=f"source {source_id} observation {observation_id}",
        ):
            return False
    return True


def validate_claim_source_authority(
    claim: dict,
    *,
    source_records: dict[str, dict],
    authority_judgments: dict[str, dict],
    observation_records: dict[str, dict] | None = None,
) -> list[str]:
    """Validate semantic claim/source compatibility and model permission.

    The actual support-linked SourceRecords participate in the decision, so a
    subjective source cannot gain a factual permission by changing
    ``claim_type``.  Qualitative sufficiency remains with the frozen reviewer;
    this function enforces only types, boundaries, and faithful bindings.
    """

    claim_id = str(claim.get("claim_id") or "UNKNOWN").strip()
    claim_type = str(claim.get("claim_type") or "").strip()
    proposition_scope = str(claim.get("proposition_scope") or "").strip()
    allowed_use = str(claim.get("allowed_use") or "").strip()
    supporting = _supporting_source_records(claim, source_records)
    observation_records = observation_records or {}
    claim_driver_node_ids = {
        str(item).strip()
        for item in (claim.get("driver_node_ids") or [])
        if str(item).strip()
    }
    problems: list[str] = []
    expected_observation_bindings: dict[str, dict[str, str]] = {}

    has_management_support = False
    has_technical_support = False
    has_factual_support = False
    for link, source, semantics in supporting:
        source_id = str(link.get("source_id") or "UNKNOWN").strip()
        problems.extend(
            source_epistemic_class_problems(
                source,
                label=f"{claim_id}: source {source_id}",
            )
        )
        has_management_support = has_management_support or "management" in semantics
        has_technical_support = has_technical_support or "technical" in semantics
        has_factual_support = has_factual_support or "factual_observation" in semantics
        evidence_function = str(link.get("evidence_function") or "").strip()
        raw_observation_ids = link.get("observation_ids")
        if not isinstance(raw_observation_ids, list):
            problems.append(
                f"{claim_id}: source {source_id} observation_ids must be an array"
            )
            raw_observation_ids = []
        observation_items = [str(item).strip() for item in raw_observation_ids]
        observation_ids = {item for item in observation_items if item}
        if len(observation_items) != len(observation_ids):
            problems.append(
                f"{claim_id}: source {source_id} observation_ids must be unique non-empty ids"
            )
        needs_original_observation = (
            allowed_use in CLAIM_MODEL_CHANGING_USES
            and evidence_function in _OBSERVATION_EVIDENCE_FUNCTIONS
            and source_epistemic_class(source) == "independent_external_observation"
        )
        if needs_original_observation and not observation_ids:
            problems.append(
                f"{claim_id}: source {source_id} {evidence_function} requires observation_ids "
                "bound to a separate original measurement record"
            )
        for observation_id in sorted(observation_ids):
            observation = observation_records.get(observation_id)
            if not isinstance(observation, dict):
                problems.append(
                    f"{claim_id}: source {source_id} has unknown observation_id {observation_id}"
                )
                continue
            observation_problems = external_observation_binding_problems(
                observation,
                source,
                claim_driver_node_ids=claim_driver_node_ids,
                label=f"{claim_id}: observation {observation_id}",
            )
            problems.extend(observation_problems)
            if not observation_problems:
                expected_observation_bindings[observation_id] = (
                    external_observation_review_binding(observation, source)
                )
        if "management" in semantics and claim_type not in {
            "management_claim",
            "analyst_assumption",
            "scenario",
        }:
            problems.append(
                f"{claim_id}: incompatible management support source {source_id} "
                f"for claim_type {claim_type or '<blank>'}"
            )
        if "expert_or_analyst" in semantics and claim_type not in {
            "analyst_assumption",
            "scenario",
        }:
            problems.append(
                f"{claim_id}: incompatible expert/analyst support source {source_id} "
                f"for claim_type {claim_type or '<blank>'}"
            )
        if "technical" in semantics and claim_type not in {
            "technical_boundary",
            "derived_fact",
            "analyst_assumption",
            "scenario",
        }:
            problems.append(
                f"{claim_id}: incompatible technical support source {source_id} "
                f"for claim_type {claim_type or '<blank>'}"
            )
        if "discovery_only" in semantics and allowed_use in CLAIM_MODEL_CHANGING_USES:
            problems.append(
                f"{claim_id}: discovery-only source {source_id} cannot support "
                f"model-changing use {allowed_use}"
            )

    if claim_type == "management_claim" and supporting and not has_management_support:
        problems.append(
            f"{claim_id}: incompatible management_claim has no management support source"
        )
    if claim_type == "technical_boundary" and supporting and not has_technical_support:
        problems.append(
            f"{claim_id}: incompatible technical_boundary has no technical support source"
        )
    if claim_type == "reported_fact" and supporting and not has_factual_support:
        problems.append(
            f"{claim_id}: incompatible reported_fact has no factual-observation authority"
        )
    if (
        claim_type == "reported_fact"
        and proposition_scope in CLAIM_PREDICTIVE_PROPOSITION_SCOPES
    ):
        problems.append(
            f"{claim_id}: reported_fact is incompatible with proposition_scope "
            f"{proposition_scope}; a future execution or external-state proposition is "
            "an estimate or inference, not a reported fact"
        )

    if has_management_support and allowed_use in CLAIM_QUANTITATIVE_REFERENCE_USES:
        calibration = claim.get("forecast_calibration")
        calibration_fields = (
            "historical_bias_or_range",
            "calibration_basis",
            "application_boundary",
        )
        if not isinstance(calibration, dict):
            problems.append(
                f"{claim_id}: management forecast calibration is required for base_parameter"
            )
        else:
            missing_calibration = [
                field for field in calibration_fields
                if _placeholder(calibration.get(field))
            ]
            if missing_calibration:
                problems.append(
                    f"{claim_id}: management forecast calibration missing "
                    + ",".join(missing_calibration)
                )

    if (
        proposition_scope in CLAIM_PREDICTIVE_PROPOSITION_SCOPES
        and allowed_use in CLAIM_MODEL_CHANGING_USES
        and not any(
            str(link.get("evidence_function") or "").strip()
            in {"causal_test", "external_test"}
            and _source_can_test_external_execution(
                source,
                link,
                observation_records,
                claim_driver_node_ids,
            )
            for link, source, _semantics in supporting
        )
    ):
        problems.append(
            f"{claim_id}: future execution or external state in a "
            "model-changing use requires a named causal_test or external_test from an "
            "independent external factual source with "
            "epistemic_class=independent_external_observation; management cannot test "
            "its own execution, "
            "and a reported label, issuer, expert, or analyst opinion cannot replace the "
            "external observation that tests the predicted state"
        )

    if claim_requires_independent_authority(claim, source_records):
        linked_source_ids = {
            str(item).strip()
            for item in (claim.get("source_ids") or [])
            if str(item).strip()
        }
        linked_source_epistemic_classes = {
            source_id: source_epistemic_class(source_records[source_id])
            for source_id in linked_source_ids
            if source_id in source_records
        }
        linked_source_origin_record_kinds = {
            source_id: source_origin_record_kind(source_records[source_id])
            for source_id in linked_source_ids
            if source_id in source_records
        }
        problems.extend(
            validate_claim_authority_permission(
                claim,
                linked_source_ids=linked_source_ids,
                linked_source_epistemic_classes=linked_source_epistemic_classes,
                linked_source_origin_record_kinds=linked_source_origin_record_kinds,
                expected_observation_bindings=expected_observation_bindings,
                authority_judgments=authority_judgments,
            )
        )
    return problems


def validate_claim_authority_permission(
    claim: dict,
    *,
    linked_source_ids: set[str],
    linked_source_epistemic_classes: dict[str, str],
    linked_source_origin_record_kinds: dict[str, str],
    expected_observation_bindings: dict[str, dict[str, str]],
    authority_judgments: dict[str, dict],
) -> list[str]:
    """Enforce a frozen reviewer's declared permission without scoring authority."""

    claim_id = str(claim.get("claim_id") or "UNKNOWN").strip()
    allowed_use = str(claim.get("allowed_use") or "").strip()
    judgment = authority_judgments.get(claim_id)
    if not isinstance(judgment, dict):
        return [
            f"{claim_id}: {claim.get('claim_type')} requires a frozen independent "
            f"authority judgment before {allowed_use} use"
        ]

    problems: list[str] = []
    if str(judgment.get("claim_id") or "").strip() != claim_id:
        problems.append(f"{claim_id}: frozen authority judgment names a different claim_id")
    reviewed_source_ids = {
        str(item).strip()
        for item in (judgment.get("reviewed_source_ids") or [])
        if str(item).strip()
    }
    if reviewed_source_ids != linked_source_ids:
        problems.append(
            f"{claim_id}: frozen authority judgment reviewed_source_ids must match "
            "the claim evidence links exactly"
        )
    reviewed_classes_raw = judgment.get("reviewed_source_epistemic_classes")
    if not isinstance(reviewed_classes_raw, dict):
        problems.append(
            f"{claim_id}: frozen authority judgment "
            "reviewed_source_epistemic_classes must be an object bound to the reviewed sources"
        )
    else:
        reviewed_source_epistemic_classes = {
            str(source_id).strip(): str(epistemic_class or "").strip()
            for source_id, epistemic_class in reviewed_classes_raw.items()
            if str(source_id).strip()
        }
        if reviewed_source_epistemic_classes != linked_source_epistemic_classes:
            problems.append(
                f"{claim_id}: frozen authority judgment "
                "reviewed_source_epistemic_classes must match the linked SourceRecords exactly"
            )
    reviewed_origins_raw = judgment.get("reviewed_source_origin_record_kinds")
    if not isinstance(reviewed_origins_raw, dict):
        problems.append(
            f"{claim_id}: frozen authority judgment "
            "reviewed_source_origin_record_kinds must be an object bound to the reviewed sources"
        )
    else:
        reviewed_source_origin_record_kinds = {
            str(source_id).strip(): str(origin_kind or "").strip()
            for source_id, origin_kind in reviewed_origins_raw.items()
            if str(source_id).strip()
        }
        if reviewed_source_origin_record_kinds != linked_source_origin_record_kinds:
            problems.append(
                f"{claim_id}: frozen authority judgment "
                "reviewed_source_origin_record_kinds must match the linked SourceRecords exactly"
            )
    reviewed_observations_raw = judgment.get("reviewed_observation_bindings")
    if not isinstance(reviewed_observations_raw, dict):
        problems.append(
            f"{claim_id}: frozen authority judgment reviewed_observation_bindings "
            "must be an object"
        )
    else:
        if set(reviewed_observations_raw) != set(expected_observation_bindings):
            problems.append(
                f"{claim_id}: frozen authority judgment reviewed_observation_bindings "
                "keys must match the claim's observation_ids exactly"
            )
        for observation_id, expected in expected_observation_bindings.items():
            reviewed = reviewed_observations_raw.get(observation_id)
            if not isinstance(reviewed, dict):
                continue
            objective = {
                key: reviewed.get(key) for key in expected
            }
            if objective != expected:
                problems.append(
                    f"{claim_id}: frozen authority judgment reviewed_observation_bindings "
                    f"does not match observation {observation_id} fingerprint and provenance"
                )
            if _placeholder(reviewed.get("classification_rationale")):
                problems.append(
                    f"{claim_id}: observation {observation_id} requires an independent "
                    "classification_rationale tied to the inspected source content"
                )
    if str(judgment.get("authority_sufficiency") or "").strip().casefold() != "adequate":
        problems.append(f"{claim_id}: frozen authority judgment does not permit {allowed_use}")
    if str(judgment.get("permitted_use") or "").strip() != allowed_use:
        problems.append(f"{claim_id}: frozen authority judgment does not permit {allowed_use}")
    if _placeholder(judgment.get("rationale")):
        problems.append(f"{claim_id}: frozen authority judgment requires a substantive rationale")
    return problems


def validate_claim_records(
    claims: list[dict],
    *,
    source_records: dict[str, dict],
    graph_node_ids: set[str],
    main_line_carriers: set[str],
    authority_judgments: dict[str, dict] | None = None,
    observation_records: dict[str, dict] | None = None,
) -> list[str]:
    """Validate proposition-scoped evidence permissions.

    Code checks identity, completeness, linkage, contradiction state and the
    faithful application of a frozen review.  It never converts source counts,
    publisher labels or a numeric score into authority.
    """

    problems: list[str] = []
    authority_judgments = authority_judgments or {}
    observation_records = observation_records or {}
    seen_claim_ids: set[str] = set()
    substantive_claims: list[dict] = []

    for index, claim in enumerate(claims, 1):
        label = f"claim[{index}]"
        if not isinstance(claim, dict):
            problems.append(f"{label}: claim must be an object")
            continue
        claim_id = str(claim.get("claim_id") or "").strip()
        if _placeholder(claim_id):
            problems.append(f"{label}: placeholder claim_id")
            continue
        label = claim_id
        if claim_id in seen_claim_ids:
            problems.append(f"{label}: duplicate claim_id")
        seen_claim_ids.add(claim_id)
        substantive_claims.append(claim)

        required = {
            "text",
            "claim_type",
            "proposition_scope",
            "source_ids",
            "evidence_links",
            "allowed_use",
            "driver_node_ids",
            "as_of",
            "status",
        }
        missing = sorted(
            field for field in required
            if field not in claim or claim.get(field) in (None, "")
        )
        if missing:
            problems.append(f"{label}: missing {','.join(missing)}")

        claim_type = str(claim.get("claim_type") or "").strip()
        proposition_scope = str(claim.get("proposition_scope") or "").strip()
        allowed_use = str(claim.get("allowed_use") or "").strip()
        status = str(claim.get("status") or "").strip()
        if claim_type not in CLAIM_TYPES:
            problems.append(f"{label}: unknown claim_type {claim_type or '<blank>'}")
        if proposition_scope not in CLAIM_PROPOSITION_SCOPES:
            problems.append(
                f"{label}: unknown proposition_scope {proposition_scope or '<blank>'}"
            )
        if allowed_use not in CLAIM_ALLOWED_USES:
            problems.append(f"{label}: unknown allowed_use {allowed_use or '<blank>'}")
        if status not in CLAIM_STATUSES:
            problems.append(f"{label}: unknown status {status or '<blank>'}")
        if _placeholder(claim.get("text")):
            problems.append(f"{label}: text must be substantive")
        if not _valid_iso_date(claim.get("as_of")):
            problems.append(f"{label}: as_of must be an ISO date or datetime")

        raw_source_ids = claim.get("source_ids")
        if not isinstance(raw_source_ids, list):
            problems.append(f"{label}: source_ids must be an array")
            raw_source_ids = []
        source_id_items = [str(item).strip() for item in raw_source_ids]
        linked_source_ids = {item for item in source_id_items if item}
        if len(linked_source_ids) != len(source_id_items):
            problems.append(f"{label}: source_ids must be unique non-empty ids")

        links = claim.get("evidence_links")
        if not isinstance(links, list):
            problems.append(f"{label}: evidence_links must be an array")
            links = []
        link_source_ids: set[str] = set()
        unresolved_contradiction = False
        for link_index, link in enumerate(links, 1):
            link_label = f"{label}:evidence_links[{link_index}]"
            if not isinstance(link, dict):
                problems.append(f"{link_label} must be an object")
                continue
            missing_link = [
                field for field in CLAIM_LINK_FIELDS
                if field not in link
                or (field != "observation_ids" and _placeholder(link.get(field)))
            ]
            if missing_link:
                problems.append(f"{link_label}: missing {','.join(missing_link)}")
            link_source_id = str(link.get("source_id") or "").strip()
            if link_source_id in link_source_ids:
                problems.append(f"{link_label}: duplicate source_id {link_source_id}")
            if link_source_id:
                link_source_ids.add(link_source_id)
            relation = str(link.get("relation") or "").strip()
            evidence_function = str(link.get("evidence_function") or "").strip()
            reconciliation = str(link.get("reconciliation_status") or "").strip()
            if relation not in CLAIM_LINK_RELATIONS:
                problems.append(f"{link_label}: invalid relation {relation or '<blank>'}")
            if evidence_function not in CLAIM_EVIDENCE_FUNCTIONS:
                problems.append(
                    f"{link_label}: invalid evidence_function "
                    f"{evidence_function or '<blank>'}"
                )
            if reconciliation not in CLAIM_RECONCILIATION_STATUSES:
                problems.append(
                    f"{link_label}: invalid reconciliation_status {reconciliation or '<blank>'}"
                )
            raw_observation_ids = link.get("observation_ids")
            if not isinstance(raw_observation_ids, list):
                problems.append(f"{link_label}: observation_ids must be an array")
            else:
                observation_id_items = [
                    str(item).strip() for item in raw_observation_ids
                ]
                observation_ids = {item for item in observation_id_items if item}
                if len(observation_id_items) != len(observation_ids):
                    problems.append(
                        f"{link_label}: observation_ids must be unique non-empty ids"
                    )
            if relation == "contradict" and reconciliation == "not_applicable":
                problems.append(
                    f"{link_label}: contradictory evidence must be reconciled or unresolved"
                )
            if relation == "contradict" and reconciliation != "reconciled":
                unresolved_contradiction = True

        if linked_source_ids != link_source_ids:
            problems.append(f"{label}: source_ids and evidence_links must match exactly")
        unknown_link_sources = sorted(link_source_ids - set(source_records))
        if unknown_link_sources:
            problems.append(
                f"{label}: unknown evidence-link source ids "
                + ",".join(unknown_link_sources)
            )

        raw_nodes = claim.get("driver_node_ids")
        if not isinstance(raw_nodes, list):
            problems.append(f"{label}: driver_node_ids must be an array")
            raw_nodes = []
        node_items = [str(item).strip() for item in raw_nodes]
        linked_nodes = {item for item in node_items if item}
        if len(linked_nodes) != len(node_items):
            problems.append(f"{label}: driver_node_ids must be unique non-empty ids")
        unknown_nodes = sorted(linked_nodes - graph_node_ids)
        if unknown_nodes:
            problems.append(f"{label}: unknown driver nodes {','.join(unknown_nodes)}")
        if allowed_use in CLAIM_MODEL_CHANGING_USES and not linked_source_ids:
            problems.append(f"{label}: {allowed_use} requires source lineage")
        if status == "accepted" and unresolved_contradiction:
            problems.append(f"{label}: unresolved contradiction cannot be accepted")
        problems.extend(
            validate_claim_source_authority(
                claim,
                source_records=source_records,
                authority_judgments=authority_judgments,
                observation_records=observation_records,
            )
        )

    if not substantive_claims:
        problems.append("no substantive claim records")
    if substantive_claims and main_line_carriers and not any(
        main_line_carriers
        & {
            str(item).strip()
            for item in (claim.get("driver_node_ids") or [])
            if str(item).strip()
        }
        for claim in substantive_claims
    ):
        problems.append("no claim links evidence to a main-line carrier node")
    return problems


def frozen_artifact_hash_problems(
    workspace: Path,
    frozen_artifacts: object,
    artifact_names: tuple[str, ...],
    *,
    label: str,
) -> list[str]:
    """Verify one canonical set of frozen-file bindings."""

    if not isinstance(frozen_artifacts, dict):
        return [f"{label}: frozen_artifacts must be an object"]
    problems: list[str] = []
    for name in artifact_names:
        path = workspace / name
        if not path.exists():
            problems.append(f"{label}: {name} is missing")
            continue
        declared_hash = str(frozen_artifacts.get(name) or "").strip()
        actual_hash = "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()
        if declared_hash != actual_hash:
            problems.append(f"{label}: {name} hash mismatch")
    return problems


def load_frozen_claim_authority_judgments(
    workspace: Path,
    claim_path: Path,
) -> tuple[dict[str, dict], list[str]]:
    """Load claim permissions only when the review is independent and current."""

    review_path = workspace / "research_quality_review.json"
    if not review_path.exists():
        return {}, []
    problems: list[str] = []
    try:
        review = json.loads(review_path.read_text(encoding="utf-8"))
    except Exception as exc:
        return {}, [f"cannot read frozen independent authority judgment: {exc}"]
    if not isinstance(review, dict):
        return {}, ["frozen independent authority judgment must be an object"]
    builder_id = str(review.get("builder_id") or "").strip()
    reviewer_id = str(review.get("reviewer_id") or "").strip()
    if review.get("independent_of_builder") is not True or not reviewer_id or reviewer_id == builder_id:
        problems.append("claim authority judgment is not independently reviewed")
    problems.extend(
        frozen_artifact_hash_problems(
            workspace,
            review.get("frozen_artifacts"),
            (
                "claim_ledger.jsonl",
                "source_manifest.json",
                "data_series_register.csv",
            ),
            label="claim authority judgment is stale",
        )
    )
    raw_judgments = review.get("claim_authority_judgments")
    if not isinstance(raw_judgments, list):
        problems.append("research quality review claim_authority_judgments must be an array")
        raw_judgments = []
    judgments: dict[str, dict] = {}
    for item in raw_judgments:
        if not isinstance(item, dict):
            continue
        claim_id = str(item.get("claim_id") or "").strip()
        if claim_id and claim_id not in judgments:
            judgments[claim_id] = item
    return ({} if problems else judgments), problems


def validate_accounting_basis_contract(
    manifest: dict,
    *,
    snapshot: dict | None = None,
    financial_fact_rows: list[dict[str, str]] | None = None,
    source_ids: set[str] | None = None,
) -> list[str]:
    """Validate accounting framework lineage without encoding GAAP differences as drivers.

    Each framework/version is a dated reporting contract. Historical facts and
    forecast outputs name one of those contracts. A change of contract is
    reconciled by sourced monetary adjustments, never by a company-growth
    parameter or an unexplained normalized margin.
    """

    problems: list[str] = []
    accounting = manifest.get("accounting_basis")
    if not isinstance(accounting, dict):
        return ["accounting_basis must be a typed object; bare GAAP/IFRS labels are forbidden"]

    forecast_basis_id = str(accounting.get("forecast_basis_id") or "").strip()
    historical_basis_ids = {
        str(item).strip()
        for item in (accounting.get("historical_basis_ids") or [])
        if str(item).strip()
    }
    bases = accounting.get("bases")
    bridges = accounting.get("comparability_bridges")
    if _placeholder(forecast_basis_id):
        problems.append("accounting_basis.forecast_basis_id is required")
    if not historical_basis_ids:
        problems.append("accounting_basis.historical_basis_ids must be non-empty")
    if not isinstance(bases, list) or not bases:
        problems.append("accounting_basis.bases must contain at least one typed basis")
        bases = []
    if not isinstance(bridges, list):
        problems.append("accounting_basis.comparability_bridges must be an array")
        bridges = []

    manifest_currency = str(manifest.get("currency") or "").strip()

    basis_by_id: dict[str, dict] = {}
    for index, basis in enumerate(bases):
        label = f"accounting_basis.bases[{index}]"
        if not isinstance(basis, dict):
            problems.append(f"{label} must be an object")
            continue
        basis_id = str(basis.get("basis_id") or "").strip()
        if _placeholder(basis_id):
            problems.append(f"{label}.basis_id is required")
        elif basis_id in basis_by_id:
            problems.append(f"duplicate accounting basis_id {basis_id}")
        else:
            basis_by_id[basis_id] = basis

        framework = str(basis.get("framework") or "").strip()
        if framework not in ACCOUNTING_FRAMEWORKS:
            problems.append(
                f"{basis_id or label}: framework must be one of "
                + ",".join(sorted(ACCOUNTING_FRAMEWORKS))
            )
        for field in ("jurisdiction", "version"):
            if _placeholder(basis.get(field)):
                problems.append(f"{basis_id or label}: {field} is required")
        try:
            effective_at = parse_datetime(str(basis.get("effective_at") or ""))
        except Exception:
            effective_at = None
            problems.append(f"{basis_id or label}: effective_at must be an ISO date-time")
        presentation_currency = str(basis.get("presentation_currency") or "").strip()
        if _placeholder(presentation_currency):
            problems.append(f"{basis_id or label}: presentation_currency is required")
        elif manifest_currency and presentation_currency != manifest_currency:
            problems.append(
                f"{basis_id or label}: presentation_currency {presentation_currency} "
                f"does not match manifest currency {manifest_currency}"
            )

        policy_choices = basis.get("major_policy_choices")
        if not isinstance(policy_choices, list) or not policy_choices:
            problems.append(f"{basis_id or label}: major_policy_choices must be non-empty")
            policy_choices = []
        for policy_index, policy in enumerate(policy_choices):
            policy_label = f"{basis_id or label}:major_policy_choices[{policy_index}]"
            if not isinstance(policy, dict):
                problems.append(f"{policy_label} must be an object")
                continue
            for field in ("policy_id", "policy_area", "choice"):
                if _placeholder(policy.get(field)):
                    problems.append(f"{policy_label}: {field} is required")
            forbidden = sorted(ACCOUNTING_POLICY_FORBIDDEN_KEYS & set(policy))
            if forbidden:
                problems.append(
                    f"{policy_label}: accounting policy cannot be a company driver parameter "
                    f"({','.join(forbidden)})"
                )
            policy_sources = {
                str(item).strip()
                for item in (policy.get("source_ids") or [])
                if str(item).strip()
            }
            if not policy_sources:
                problems.append(f"{policy_label}: source_ids must be non-empty")
            elif source_ids is not None and policy_sources - source_ids:
                problems.append(
                    f"{policy_label}: unknown source_ids "
                    + ",".join(sorted(policy_sources - source_ids))
                )

    declared_ids = set(basis_by_id)
    if forecast_basis_id and forecast_basis_id not in declared_ids:
        problems.append("accounting_basis.forecast_basis_id is not declared in bases")
    unknown_historical = sorted(historical_basis_ids - declared_ids)
    if unknown_historical:
        problems.append(
            "accounting_basis.historical_basis_ids are not declared: "
            + ",".join(unknown_historical)
        )

    if snapshot is not None:
        snapshot_basis = str(snapshot.get("accounting_basis_id") or "").strip()
        if snapshot_basis != forecast_basis_id:
            problems.append(
                "snapshot.accounting_basis_id must equal accounting_basis.forecast_basis_id"
            )

    for row in financial_fact_rows or []:
        fact_id = str(row.get("fact_id") or "UNKNOWN").strip()
        if _placeholder(fact_id):
            continue
        fact_basis = str(row.get("accounting_basis_id") or "").strip()
        if fact_basis not in historical_basis_ids:
            problems.append(
                f"financial fact {fact_id}: accounting_basis_id must be one of historical_basis_ids"
            )

    covered_from_ids: set[str] = set()
    covered_fact_periods: set[tuple[str, str]] = set()
    for index, bridge in enumerate(bridges):
        label = f"accounting_basis.comparability_bridges[{index}]"
        if not isinstance(bridge, dict):
            problems.append(f"{label} must be an object")
            continue
        bridge_id = str(bridge.get("bridge_id") or "").strip()
        from_id = str(bridge.get("from_basis_id") or "").strip()
        to_id = str(bridge.get("to_basis_id") or "").strip()
        if _placeholder(bridge_id):
            problems.append(f"{label}.bridge_id is required")
        if from_id not in historical_basis_ids:
            problems.append(f"{bridge_id or label}: from_basis_id is not a historical basis")
        if to_id != forecast_basis_id:
            problems.append(f"{bridge_id or label}: to_basis_id must be the forecast basis")
        if from_id in historical_basis_ids and to_id == forecast_basis_id:
            covered_from_ids.add(from_id)
        bridge_period = str(bridge.get("period") or "").strip()
        if _placeholder(bridge_period):
            problems.append(f"{bridge_id or label}: period is required")
        elif from_id in historical_basis_ids and to_id == forecast_basis_id:
            covered_fact_periods.add((from_id, bridge_period))
        bridge_sources = {
            str(item).strip()
            for item in (bridge.get("source_ids") or [])
            if str(item).strip()
        }
        if not bridge_sources:
            problems.append(f"{bridge_id or label}: source_ids must be non-empty")
        elif source_ids is not None and bridge_sources - source_ids:
            problems.append(
                f"{bridge_id or label}: unknown source_ids "
                + ",".join(sorted(bridge_sources - source_ids))
            )
        adjustments = bridge.get("adjustments")
        if not isinstance(adjustments, list) or not adjustments:
            problems.append(f"{bridge_id or label}: quantified adjustments must be non-empty")
            adjustments = []
        for adjustment_index, adjustment in enumerate(adjustments):
            adj_label = f"{bridge_id or label}:adjustments[{adjustment_index}]"
            if not isinstance(adjustment, dict):
                problems.append(f"{adj_label} must be an object")
                continue
            for field in ("adjustment_id", "line_item", "explanation"):
                if _placeholder(adjustment.get(field)):
                    problems.append(f"{adj_label}: {field} is required")
            if _finite_number(adjustment.get("amount")) is None:
                problems.append(f"{adj_label}: adjustment needs a finite amount")
            adjustment_currency = str(adjustment.get("currency") or "").strip()
            if adjustment_currency != manifest_currency:
                problems.append(
                    f"{adj_label}: currency must equal manifest presentation currency {manifest_currency}"
                )

    missing_bridges = sorted(
        basis_id
        for basis_id in historical_basis_ids
        if basis_id != forecast_basis_id and basis_id not in covered_from_ids
    )
    if missing_bridges:
        problems.append(
            "each historical basis differing from forecast needs a quantified comparability bridge: "
            + ",".join(missing_bridges)
        )
    required_fact_periods = {
        (fact_basis_id, period)
        for row in (financial_fact_rows or [])
        if (
            (fact_basis_id := str(row.get("accounting_basis_id") or "").strip())
            in historical_basis_ids
            and fact_basis_id != forecast_basis_id
            and (period := financial_fact_period(row)) is not None
        )
    }
    missing_fact_periods = sorted(required_fact_periods - covered_fact_periods)
    if missing_fact_periods:
        problems.append(
            "financial fact periods need a matching comparability bridge: "
            + ",".join(f"{basis_id}@{period}" for basis_id, period in missing_fact_periods)
        )
    return problems


def _valid_model_cell_or_formula(value: object) -> bool:
    text = str(value or "").strip()
    return bool(
        CELL_REFERENCE_RE.fullmatch(text)
        or (text.startswith("=") and CELL_REFERENCE_SEARCH_RE.search(text[1:]))
    )


def _unit_dimension(value: object) -> str:
    """Normalize common scale/plural notation while preserving dimension."""

    text = str(value or "").strip().lower()
    for token in ("millions", "million", "mn", "thousands", "thousand"):
        text = re.sub(rf"\b{token}\b", "", text)
    text = re.sub(r"\s+", "", text).replace("units", "unit")
    return text


def _named_list(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    return [item.strip() for item in value if isinstance(item, str) and not _placeholder(item)]


def validate_growth_challenger_review(review: object) -> list[str]:
    """Validate analyst-selected outside views without prescribing their taxonomy.

    The company and decision determine which outside view is relevant.  The
    validator checks the selected bridge's direction and arithmetic; frozen
    independent review judges whether a material challenger was omitted.
    """

    if not isinstance(review, list) or not review:
        return ["growth_challenger_review missing or empty"]

    problems: list[str] = []
    seen: set[str] = set()
    for index, row in enumerate(review, 1):
        if not isinstance(row, dict):
            problems.append(f"row {index}: must be an object")
            continue
        challenger = str(row.get("challenger") or "").strip().lower()
        label = challenger or f"row {index}"
        if _placeholder(challenger):
            problems.append(f"{label}: challenger must name the selected outside view")
            continue
        if challenger in seen:
            problems.append(f"{label}: duplicate challenger")
        seen.add(challenger)

        if _placeholder(row.get("horizon")):
            problems.append(f"{label}: horizon missing")
        status = str(row.get("status") or "").strip().lower()
        if status not in {"accepted", "not_available_with_reason", "human_required"}:
            problems.append(
                f"{label}: status must be accepted, not_available_with_reason, or human_required"
            )
            continue
        if status != "accepted":
            if _placeholder(row.get("notes")):
                problems.append(f"{label}: {status} requires notes")
            continue

        challenger_growth = _finite_number(row.get("challenger_growth_pct"))
        model_growth = _finite_number(row.get("driver_tree_growth_pct"))
        if challenger_growth is None or model_growth is None:
            problems.append(f"{label}: accepted row needs numeric challenger_growth_pct and driver_tree_growth_pct")
            continue
        direction = str(row.get("difference_direction") or "").strip().lower()
        gap = model_growth - challenger_growth
        expected_direction = "acceleration" if gap > 1e-9 else ("deceleration" if gap < -1e-9 else "no_difference")
        if direction != expected_direction:
            problems.append(
                f"{label}: difference_direction {direction or '<blank>'} does not match {expected_direction}"
            )
        if not isinstance(row.get("material_difference"), bool):
            problems.append(f"{label}: material_difference must be an explicit boolean")
            continue
        if _placeholder(row.get("materiality_basis")):
            problems.append(f"{label}: materiality_basis missing")

        if row["material_difference"]:
            driver_ids = _named_list(row.get("transition_driver_node_ids"))
            state_ids = _named_list(row.get("named_state_ids"))
            if not driver_ids:
                problems.append(f"{label}: material difference needs named transition_driver_node_ids")
            if not state_ids:
                problems.append(f"{label}: material difference needs named_state_ids")
            bridge = row.get("bridge")
            if not isinstance(bridge, list) or not bridge:
                problems.append(f"{label}: material difference needs a quantified bridge")
            else:
                bridge_total = 0.0
                bridge_valid = True
                for bridge_index, item in enumerate(bridge, 1):
                    bridge_driver = item.get("driver_node_id") if isinstance(item, dict) else None
                    if not isinstance(bridge_driver, str) or _placeholder(bridge_driver):
                        problems.append(f"{label}: bridge row {bridge_index} needs driver_node_id")
                        bridge_valid = False
                        continue
                    if bridge_driver.strip() not in driver_ids:
                        problems.append(
                            f"{label}: bridge driver {bridge_driver.strip()} is not named in transition_driver_node_ids"
                        )
                        bridge_valid = False
                    delta = _finite_number(item.get("delta_growth_pct"))
                    if delta is None:
                        problems.append(f"{label}: bridge row {bridge_index} needs numeric delta_growth_pct")
                        bridge_valid = False
                    else:
                        bridge_total += delta
                tolerance = max(1e-6, abs(gap) * 0.001)
                if bridge_valid and abs(bridge_total - gap) > tolerance:
                    problems.append(
                        f"{label}: quantified bridge {bridge_total:g} does not reconcile to growth gap {gap:g}"
                    )
        elif _placeholder(row.get("notes")):
            problems.append(f"{label}: non-material difference requires notes explaining the case-specific basis")

    return problems


def validate_canonical_output_period(
    output: object,
    *,
    needs_range: bool,
    strict_full_company: bool,
) -> list[str]:
    if not isinstance(output, dict):
        return ["period missing from outputs"]

    problems: list[str] = []
    if strict_full_company:
        if _placeholder(output.get("period")):
            problems.append("period missing")
        required_points = (
            "revenue_point",
            "operating_profit_point",
            "pretax_profit_point",
            "tax_expense_point",
            "noncontrolling_interest_net_income_point",
            "net_income_point",
            "profit_point",
        )
        missing_points = [field for field in required_points if not _json_number(output.get(field))]
        if missing_points:
            problems.append("missing/non-numeric " + ",".join(missing_points))
    else:
        if not _json_number(output.get("revenue_point")):
            problems.append("missing/non-numeric revenue_point")
        if not (_json_number(output.get("profit_point")) or _json_number(output.get("eps_point"))):
            problems.append("missing/non-numeric profit_point or eps_point")

    if needs_range:
        if not all(_json_number(output.get(field)) for field in ("revenue_low", "revenue_high")):
            problems.append("missing/non-numeric revenue_low,revenue_high")
        if strict_full_company:
            if not all(
                _json_number(output.get(field))
                for field in ("operating_profit_low", "operating_profit_high")
            ):
                problems.append(
                    "missing/non-numeric operating_profit_low,operating_profit_high"
                )
            if not all(_json_number(output.get(field)) for field in ("profit_low", "profit_high")):
                problems.append("missing/non-numeric profit_low,profit_high")
        elif not (
            all(_json_number(output.get(field)) for field in ("profit_low", "profit_high"))
            or all(_json_number(output.get(field)) for field in ("eps_low", "eps_high"))
        ):
            problems.append("missing/non-numeric profit_low/high or eps_low/high")

    profit = output.get("profit_point")
    net_income = output.get("net_income_point")
    if _json_number(profit) and _json_number(net_income):
        tolerance = max(1e-6, abs(float(profit)) * 0.001)
        if abs(float(profit) - float(net_income)) > tolerance:
            problems.append("profit_point and net_income_point disagree")
    return problems


def validate_driver_tree_partitions(
    tree: object,
    *,
    consolidated_revenue: object,
) -> list[str]:
    """Reconcile the primary revenue partition and type analytical cross-cuts.

    The primary driver-tree leaves are a full-company arithmetic partition.
    Customer, product or geography leader tables may instead be partial or
    overlapping cross-checks.  Those views must state that boundary and are
    deliberately not forced to 100%.
    """

    if not isinstance(tree, dict):
        return ["driver_tree must be an object"]
    problems: list[str] = []
    segments = tree.get("segments")
    if not isinstance(segments, list) or not segments:
        return problems

    partition = tree.get("partition")
    if not isinstance(partition, dict):
        problems.append(
            "driver_tree.partition must declare id, dimension, exhaustiveness and mutual exclusivity"
        )
    else:
        if _placeholder(partition.get("partition_id")):
            problems.append("driver_tree.partition.partition_id missing")
        if _placeholder(partition.get("dimension")):
            problems.append("driver_tree.partition.dimension missing")
        problems.extend(
            validate_partition_reconciliation(
                label="driver_tree.partition",
                parent_value=consolidated_revenue,
                member_values=[
                    segment.get("revenue_point") if isinstance(segment, dict) else None
                    for segment in segments
                ],
                exhaustive=partition.get("exhaustive"),
                mutually_exclusive=partition.get("mutually_exclusive"),
                declared_residual=partition.get("declared_residual"),
                require_parent_reconciliation=True,
            )
        )

    for index, view in enumerate(tree.get("cross_check_views") or [], 1):
        if not isinstance(view, dict):
            problems.append(f"driver_tree.cross_check_views[{index}] must be an object")
            continue
        members = view.get("members")
        if not isinstance(members, list) or not members:
            # Narrative or equation-only cross-checks are not share tables.
            continue
        label = f"driver_tree.cross_check_views[{index}]"
        cross_partition = view.get("partition")
        if not isinstance(cross_partition, dict):
            problems.append(
                f"{label}.partition must declare whether the member list is exhaustive "
                "and mutually exclusive"
            )
            continue
        if _placeholder(cross_partition.get("partition_id")):
            problems.append(f"{label}.partition.partition_id missing")
        if _placeholder(cross_partition.get("dimension")):
            problems.append(f"{label}.partition.dimension missing")
        member_values = [
            member.get("share") if isinstance(member, dict) else None
            for member in members
        ]
        problems.extend(
            validate_partition_reconciliation(
                label=f"{label}.partition",
                parent_value=cross_partition.get("parent_value"),
                member_values=member_values,
                exhaustive=cross_partition.get("exhaustive"),
                mutually_exclusive=cross_partition.get("mutually_exclusive"),
                declared_residual=cross_partition.get("declared_residual"),
                require_parent_reconciliation=False,
            )
        )
    return problems


def validate_product_customer_driver_rows(rows: list[dict[str, str]]) -> list[str]:
    """Type the aggregation scope before a driver row reaches the model.

    This schedule is the construction input; the snapshot is the numeric
    execution view. Requiring the partition declaration here prevents a
    partial customer list or an overlapping product/geography cut from being
    routed into the primary revenue sum in the first place.
    """

    problems: list[str] = []
    substantive = [
        row for row in rows
        if str(row.get("segment_or_product") or "").strip().upper()
        not in {"", "TBD", "PENDING"}
    ]
    if not substantive:
        return ["product/customer driver schedule has no substantive rows"]
    for index, row in enumerate(substantive, 1):
        identity = str(row.get("segment_or_product") or f"row-{index}").strip()
        role = str(row.get("primary_tree_or_cross_check") or "").strip().lower()
        if role not in {"primary", "cross_check"}:
            problems.append(
                f"{identity}: primary_tree_or_cross_check must be primary or cross_check"
            )
        if _placeholder(row.get("partition_id")):
            problems.append(f"{identity}: partition_id missing")
        if _placeholder(row.get("partition_dimension")):
            problems.append(f"{identity}: partition_dimension missing")
        exhaustive = explicit_boolean(row.get("partition_exhaustive"))
        mutually_exclusive = explicit_boolean(row.get("partition_mutually_exclusive"))
        if exhaustive is None:
            problems.append(f"{identity}: partition_exhaustive must be explicitly true or false")
        if mutually_exclusive is None:
            problems.append(
                f"{identity}: partition_mutually_exclusive must be explicitly true or false"
            )
        if role == "primary" and not (exhaustive and mutually_exclusive):
            problems.append(
                f"{identity}: a primary revenue partition must be exhaustive and mutually exclusive; "
                "route partial or overlapping rows to cross_check"
            )
        if _placeholder(row.get("driver_node_ids")):
            problems.append(f"{identity}: driver_node_ids missing")
        if _placeholder(row.get("evidence_source_ids")):
            problems.append(f"{identity}: evidence_source_ids missing")
        if _placeholder(row.get("consolidation_link")):
            problems.append(f"{identity}: consolidation_link missing")
        if str(row.get("schedule_status") or "").strip().lower() != "accepted":
            problems.append(f"{identity}: schedule_status must be accepted")
    return problems


def validate_historical_segment_bridge_rows(
    rows: list[dict[str, str]],
    *,
    strict: bool = False,
    readiness_target: str = "",
    graph_node_ids: set[str] | None = None,
) -> list[str]:
    """Validate a usable historical base rather than a three-row placeholder.

    The strict contract requires three explicitly comparable annual slots, the
    latest interim status, consolidated earnings layers, segment-to-group
    reconciliation, and a numeric first-forecast bridge.  Disclosure gaps are
    allowed only as typed limitations with a readiness cap; missing numbers
    must never be replaced with zero merely to satisfy the gate.
    """

    problems: list[str] = []
    graph_node_ids = set(graph_node_ids or set())
    readiness = str(readiness_target or "").strip().lower()

    def _low_readiness_required(label: str) -> None:
        if readiness not in HISTORICAL_LOW_READINESS:
            problems.append(
                f"{label}: disclosure limitation requires readiness_target capped at "
                f"screen-grade (current: {readiness or 'unset'})"
            )

    def _row_label(row: dict[str, str]) -> str:
        return f"{str(row.get('period') or 'UNKNOWN')}:{str(row.get('row_type') or 'UNKNOWN')}"

    def _meaningful_member_identity(value: object) -> bool:
        """Distinguish an explicit disclosed/modelled member from an unknown token."""

        text = str(value or "").strip()
        return (
            not _placeholder(text)
            and text.casefold()
            not in {"unknown", "none", "n/a", "na", "null", "placeholder"}
        )

    def _partition_member_field(partition_dimension: object) -> str:
        """Map a partition dimension to its one authoritative member-ID field."""

        dimension = str(partition_dimension or "").strip().casefold()
        if dimension == "reported_operating_segment":
            return "reported_segment"
        if dimension == "normalized_economic_branch":
            return "normalized_segment"
        return "partition_member_id"

    def _partition_member_identity(
        row: dict[str, str], partition_dimension: object
    ) -> tuple[str, str]:
        field = _partition_member_field(partition_dimension)
        return field, str(row.get(field) or "").strip()

    def _period_identity(row: dict[str, str]) -> tuple[str, str, str, str]:
        """Return the stable fields that make a partition row belong to one parent."""

        return (
            str(row.get("period") or "").strip(),
            str(row.get("period_type") or "").strip().lower(),
            str(row.get("actual_or_forecast") or "").strip().lower(),
            str(row.get("currency") or "").strip().upper(),
        )

    def _period_identity_label(identity: tuple[str, str, str, str]) -> str:
        period, period_type, actual_or_forecast, currency = identity
        return (
            f"period={period or '<blank>'},period_type={period_type or '<blank>'},"
            f"actual_or_forecast={actual_or_forecast or '<blank>'},"
            f"currency={currency or '<blank>'}"
        )

    def _nontrivial_bridge(value: object) -> bool:
        return str(value or "").strip().lower() not in {
            "", "none", "none_no_change", "not_applicable", "n/a", "na", "tbd", "pending"
        }

    input_rows = list(rows)
    if not input_rows:
        return ["historical bridge has no substantive rows"]

    for row in input_rows:
        label = _row_label(row)
        period = str(row.get("period") or "").strip()
        period_type = str(row.get("period_type") or "").strip().lower()
        actual_or_forecast = str(row.get("actual_or_forecast") or "").strip().lower()
        row_type = str(row.get("row_type") or "").strip().lower()
        data_status = str(row.get("data_status") or "").strip().lower()
        comparability_status = str(row.get("comparability_status") or "").strip().lower()
        if _placeholder(period):
            problems.append(
                f"{label}: period must be explicit; blank/TBD/PENDING is invalid"
            )
        if period_type not in HISTORICAL_PERIOD_TYPES:
            problems.append(f"{label}: period_type must be annual, interim or first_forecast")
        elif actual_or_forecast != HISTORICAL_PERIOD_STATE[period_type]:
            problems.append(
                f"{label}: period_type/actual_or_forecast combination is invalid; "
                f"{period_type} rows require actual_or_forecast="
                f"{HISTORICAL_PERIOD_STATE[period_type]}"
            )
        if row_type not in HISTORICAL_ROW_TYPES:
            problems.append(f"{label}: row_type must be consolidated, segment or elimination")
        if row_type in {"segment", "elimination"}:
            partition_dimension = str(row.get("partition_dimension") or "").strip()
            if _placeholder(partition_dimension):
                problems.append(
                    f"{label}: segment/elimination row requires partition_dimension"
                )
            else:
                member_field, member_id = _partition_member_identity(
                    row, partition_dimension
                )
                if not _meaningful_member_identity(member_id):
                    problems.append(
                        f"{label}: partition_dimension {partition_dimension} requires "
                        f"non-placeholder {member_field} as its explicit member identity"
                    )
        if data_status not in HISTORICAL_DATA_STATUSES:
            problems.append(f"{label}: data_status must be typed")
        if comparability_status not in HISTORICAL_COMPARABILITY_STATUSES:
            problems.append(f"{label}: comparability_status must be typed")
        if not str(row.get("scope_basis") or "").strip():
            problems.append(f"{label}: scope_basis missing")
        if not str(row.get("currency") or "").strip():
            problems.append(f"{label}: currency missing")
        if not str(row.get("source_ids") or "").strip():
            problems.append(f"{label}: source_ids missing")

        typed_absence = data_status in {"disclosure_limited", "not_applicable"} or comparability_status in {
            "disclosure_limited", "not_applicable"
        }
        if typed_absence:
            if not str(row.get("missing_disclosure_reason") or "").strip():
                problems.append(f"{label}: typed limitation requires missing_disclosure_reason")
        disclosure_limited = data_status == "disclosure_limited" or comparability_status == "disclosure_limited"
        not_applicable_outside_interim = (
            (data_status == "not_applicable" or comparability_status == "not_applicable")
            and period_type != "interim"
        )
        if disclosure_limited or not_applicable_outside_interim:
            _low_readiness_required(label)

        if comparability_status == "bridged" and not (
            _nontrivial_bridge(row.get("perimeter_bridge"))
            or _nontrivial_bridge(row.get("accounting_bridge"))
        ):
            problems.append(
                f"{label}: bridged comparability requires a real perimeter or accounting bridge"
            )
        if comparability_status == "bridged" and row_type == "consolidated":
            for field in HISTORICAL_KEY_FIELDS:
                normalized_value = _finite_number(row.get(field))
                reported_value = _finite_number(row.get(f"reported_{field}"))
                delta_field = f"{field}_comparability_delta"
                delta = _finite_number(row.get(delta_field))
                if normalized_value is None:
                    # The typed disclosure-limited route below owns a genuinely
                    # unavailable line; a bridged row cannot hide it.
                    problems.append(f"{label}: bridged comparable value {field} must be numeric")
                elif reported_value is None or delta is None:
                    problems.append(
                        f"{label}: bridged comparability requires numeric reported_{field} "
                        f"and {delta_field}"
                    )
                elif not numbers_close(reported_value + delta, normalized_value):
                    problems.append(
                        f"{label}: {delta_field} does not reconcile reported_{field} "
                        f"to comparable {field}"
                    )
        elif comparability_status == "comparable":
            if not str(row.get("perimeter_bridge") or "").strip():
                problems.append(f"{label}: perimeter_bridge must state the change or none_no_change")
            if not str(row.get("accounting_bridge") or "").strip():
                problems.append(f"{label}: accounting_bridge must state the change or none_no_change")

    # Invalid input rows are reported above rather than silently disappearing.
    # Only rows with an explicit period can participate in period identities and
    # accounting reconciliation below.
    substantive = [
        row for row in input_rows
        if not _placeholder(row.get("period"))
    ]
    if not substantive:
        problems.append("historical bridge has no substantive rows")
        return problems

    annual_consolidated = [
        row for row in substantive
        if str(row.get("period_type") or "").strip().lower() == "annual"
        and str(row.get("row_type") or "").strip().lower() == "consolidated"
        and str(row.get("actual_or_forecast") or "").strip().lower() == "actual"
    ]
    if len({str(row.get("period") or "").strip() for row in annual_consolidated}) < 3:
        problems.append(
            "historical bridge must carry at least three distinct annual consolidated period slots; "
            "use a typed not_applicable/disclosure_limited row rather than omitting a period"
        )

    interim_consolidated = [
        row for row in substantive
        if str(row.get("period_type") or "").strip().lower() == "interim"
        and str(row.get("row_type") or "").strip().lower() == "consolidated"
        and str(row.get("actual_or_forecast") or "").strip().lower() == "actual"
    ]
    if not interim_consolidated:
        problems.append(
            "latest interim status missing; add the disclosed interim or a typed "
            "disclosure_limited/not_applicable row with reason"
        )

    actual_consolidated = annual_consolidated + interim_consolidated

    # Parentage is a relationship, not a period-label heuristic.  Bind every
    # disclosed segment or elimination -- including first-forecast rows -- to
    # exactly one consolidated row with the same stable period identity.  This
    # prevents a relabelled or forecast component from becoming an unvalidated
    # orphan, while allowing a consolidated-only first forecast.
    consolidated_by_identity: dict[
        tuple[str, str, str, str], list[dict[str, str]]
    ] = {}
    consolidated_by_period: dict[str, list[dict[str, str]]] = {}
    for row in substantive:
        if str(row.get("row_type") or "").strip().lower() != "consolidated":
            continue
        identity = _period_identity(row)
        consolidated_by_identity.setdefault(identity, []).append(row)
        consolidated_by_period.setdefault(identity[0], []).append(row)

    for identity, parents in consolidated_by_identity.items():
        if len(parents) != 1:
            problems.append(
                "historical partition requires exactly one consolidated parent for stable "
                f"period identity ({_period_identity_label(identity)}); found {len(parents)}"
            )

    for row in substantive:
        if str(row.get("row_type") or "").strip().lower() not in {"segment", "elimination"}:
            continue
        identity = _period_identity(row)
        parents = consolidated_by_identity.get(identity, [])
        if len(parents) == 1:
            continue
        label = _row_label(row)
        if not parents:
            # Preserve field-specific diagnostics when a row retained the
            # parent's period label but drifted on type/state/currency.
            same_period_parents = consolidated_by_period.get(identity[0], [])
            if len(same_period_parents) == 1:
                parent = same_period_parents[0]
                for field in ("period_type", "actual_or_forecast", "currency"):
                    parent_value = str(parent.get(field) or "").strip()
                    member_value = str(row.get(field) or "").strip()
                    if field == "currency":
                        matches_parent = member_value.upper() == parent_value.upper()
                    else:
                        matches_parent = member_value.lower() == parent_value.lower()
                    if not matches_parent:
                        problems.append(
                            f"{label}: member {field} {member_value or '<blank>'} "
                            f"must match parent {parent_value or '<blank>'}"
                        )
            problems.append(
                f"{label}: segment/elimination row has no consolidated actual parent or "
                "first-forecast parent for stable period identity "
                f"({_period_identity_label(identity)})"
            )
        else:
            problems.append(
                f"{label}: segment/elimination row has {len(parents)} consolidated parents "
                "for stable period identity; exactly one is required"
            )
    numeric_history: list[dict[str, str]] = []
    for row in actual_consolidated:
        label = _row_label(row)
        data_status = str(row.get("data_status") or "").strip().lower()
        reconciliation_status = str(row.get("segment_reconciliation_status") or "").strip().lower()
        if reconciliation_status not in HISTORICAL_SEGMENT_RECONCILIATION_STATUSES:
            problems.append(f"{label}: segment_reconciliation_status must be typed")
        if reconciliation_status == "disclosure_limited":
            if not str(row.get("missing_disclosure_reason") or "").strip():
                problems.append(f"{label}: segment disclosure limitation requires a reason")
            _low_readiness_required(label)
        elif reconciliation_status == "not_applicable":
            if not str(row.get("missing_disclosure_reason") or "").strip():
                problems.append(
                    f"{label}: not_applicable segment reconciliation requires a reason"
                )

        if data_status in {"reported", "derived", "bridged"}:
            missing_numeric = [field for field in HISTORICAL_KEY_FIELDS if _finite_number(row.get(field)) is None]
            if missing_numeric:
                problems.append(
                    f"{label}: numeric consolidated history missing {','.join(missing_numeric)}; "
                    "use disclosure_limited instead of a blank or fabricated value"
                )
                continue
            numeric_history.append(row)
            revenue = _finite_number(row.get("revenue"))
            cost = _finite_number(row.get("cost"))
            gross_profit = _finite_number(row.get("gross_profit"))
            assert revenue is not None and cost is not None and gross_profit is not None
            if not numbers_close(revenue - cost, gross_profit):
                problems.append(f"{label}: revenue - cost does not reconcile to gross_profit")

    complete_comparable_annuals = {
        str(row.get("period") or "").strip()
        for row in numeric_history
        if str(row.get("period_type") or "").strip().lower() == "annual"
        and str(row.get("comparability_status") or "").strip().lower() in {"comparable", "bridged"}
    }
    if len(complete_comparable_annuals) < 3:
        _low_readiness_required(
            f"only {len(complete_comparable_annuals)} complete comparable annual periods"
        )

    partition_consolidated = [
        row for row in substantive
        if str(row.get("row_type") or "").strip().lower() == "consolidated"
        and (
            (
                str(row.get("period_type") or "").strip().lower() in {"annual", "interim"}
                and str(row.get("actual_or_forecast") or "").strip().lower() == "actual"
            )
            or (
                str(row.get("period_type") or "").strip().lower() == "first_forecast"
                and str(row.get("actual_or_forecast") or "").strip().lower() == "forecast"
            )
        )
    ]

    # Each material period declares which reported rows form the primary
    # partition.  This prevents a customer, product or geography cross-cut
    # from being added to reported segments and double counted.  A status is
    # never a substitute for inspecting the rows: every disclosed full
    # partition is recomputed, while partial/overlapping views are validated
    # only as bounded cross-checks.
    for consolidated in partition_consolidated:
        label = _row_label(consolidated)
        reconciliation_status = str(
            consolidated.get("segment_reconciliation_status") or ""
        ).strip().lower()
        period = str(consolidated.get("period") or "").strip()
        parent_identity = _period_identity(consolidated)
        partition_id = str(consolidated.get("partition_id") or "").strip()
        partition_dimension = str(consolidated.get("partition_dimension") or "").strip()
        same_label_component_rows = [
            row for row in substantive
            if str(row.get("period") or "").strip() == period
            and str(row.get("row_type") or "").strip().lower() in {"segment", "elimination"}
        ]
        period_component_rows = [
            row for row in substantive
            if _period_identity(row) == parent_identity
            and str(row.get("row_type") or "").strip().lower() in {"segment", "elimination"}
        ]
        if reconciliation_status == "not_applicable":
            if same_label_component_rows:
                problems.append(
                    f"{label}: not_applicable is allowed only when no segment/elimination "
                    "partition rows exist; numeric segment/elimination rows require "
                    "reconciled, single_segment, or disclosure_limited"
                )
            continue

        component_groups: dict[str, list[dict[str, str]]] = {}
        for component in period_component_rows:
            component_label = _row_label(component)
            for field in ("period", "period_type", "actual_or_forecast", "currency"):
                parent_value = str(consolidated.get(field) or "").strip()
                member_value = str(component.get(field) or "").strip()
                if field == "currency":
                    matches_parent = member_value.upper() == parent_value.upper()
                elif field in {"period_type", "actual_or_forecast"}:
                    matches_parent = member_value.lower() == parent_value.lower()
                else:
                    matches_parent = member_value == parent_value
                if not matches_parent:
                    problems.append(
                        f"{component_label}: member {field} {member_value or '<blank>'} "
                        f"must match parent {parent_value or '<blank>'}"
                    )
            component_partition_id = str(component.get("partition_id") or "").strip()
            if not component_partition_id:
                problems.append(
                    f"{component_label}: segment/elimination row requires partition_id"
                )
                continue
            if not str(component.get("partition_dimension") or "").strip():
                problems.append(
                    f"{component_label}: segment/elimination row requires partition_dimension"
                )
            component_groups.setdefault(component_partition_id, []).append(component)

        for group_id, group_rows in component_groups.items():
            declared_dimension = (
                partition_dimension
                if group_id == partition_id
                else str(group_rows[0].get("partition_dimension") or "").strip()
            )
            seen_member_identities: set[str] = set()
            for component in group_rows:
                member_field, member_id = _partition_member_identity(
                    component, declared_dimension
                )
                if not _meaningful_member_identity(member_id):
                    problems.append(
                        f"{label}:segment revenue partition {group_id}: "
                        f"partition_dimension {declared_dimension or '<blank>'} requires "
                        f"non-placeholder {member_field} as its explicit member identity"
                    )
                    continue
                member_identity = member_id.casefold()
                if member_identity in seen_member_identities:
                    problems.append(
                        f"{label}:segment revenue partition {group_id}: "
                        "duplicate member identity "
                        f"{member_id} for partition_dimension "
                        f"{declared_dimension or '<blank>'}"
                    )
                seen_member_identities.add(member_identity)

        consolidated_revenue = _finite_number(consolidated.get("revenue"))
        if consolidated_revenue is None:
            # The typed disclosure/data limitation and readiness gate above own
            # an unavailable parent.  There is no numeric parent to reconcile.
            continue

        def _validate_component_group(
            group_id: str,
            group_rows: list[dict[str, str]],
            *,
            require_parent_reconciliation: bool,
            partition_label: str = "segment revenue partition",
        ) -> None:
            is_declared_primary = group_id == partition_id
            declaration = consolidated if is_declared_primary else group_rows[0]
            group_label = f"{label}:{partition_label} {group_id}"
            dimensions = {
                str(row.get("partition_dimension") or "").strip()
                for row in group_rows
                if str(row.get("partition_dimension") or "").strip()
            }
            declared_dimension = str(declaration.get("partition_dimension") or "").strip()
            if len(dimensions) > 1 or (
                declared_dimension and dimensions and dimensions != {declared_dimension}
            ):
                problems.append(
                    f"{group_label}: partition members disagree on partition_dimension"
                )

            if not is_declared_primary:
                exhaustive_values = {
                    explicit_boolean(row.get("partition_exhaustive"))
                    for row in group_rows
                    if explicit_boolean(row.get("partition_exhaustive")) is not None
                }
                exclusive_values = {
                    explicit_boolean(row.get("partition_mutually_exclusive"))
                    for row in group_rows
                    if explicit_boolean(row.get("partition_mutually_exclusive")) is not None
                }
                if len(exhaustive_values) > 1:
                    problems.append(
                        f"{group_label}: partition members disagree on partition_exhaustive"
                    )
                if len(exclusive_values) > 1:
                    problems.append(
                        f"{group_label}: partition members disagree on partition_mutually_exclusive"
                    )

            full_partition = (
                explicit_boolean(declaration.get("partition_exhaustive")) is True
                and explicit_boolean(declaration.get("partition_mutually_exclusive")) is True
            )
            rows_to_reconcile = group_rows
            if not require_parent_reconciliation and not full_partition:
                rows_to_reconcile = [
                    row for row in group_rows
                    if _finite_number(row.get("revenue")) is not None
                ]

            problems.extend(
                validate_partition_reconciliation(
                    label=group_label,
                    parent_value=consolidated_revenue,
                    member_values=[row.get("revenue") for row in rows_to_reconcile],
                    exhaustive=declaration.get("partition_exhaustive"),
                    mutually_exclusive=declaration.get("partition_mutually_exclusive"),
                    declared_residual=declaration.get("check_to_consolidated"),
                    require_parent_reconciliation=require_parent_reconciliation,
                )
            )

        if reconciliation_status == "reconciled":
            if not partition_id:
                problems.append(f"{label}: reconciled status requires partition_id")
            if not partition_dimension:
                problems.append(f"{label}: reconciled status requires partition_dimension")
            primary_rows = component_groups.get(partition_id, [])
            _validate_component_group(
                partition_id,
                primary_rows,
                require_parent_reconciliation=True,
            )
            for group_id, group_rows in component_groups.items():
                if group_id != partition_id:
                    _validate_component_group(
                        group_id,
                        group_rows,
                        require_parent_reconciliation=False,
                    )
        elif reconciliation_status == "single_segment":
            if not partition_id or not partition_dimension:
                problems.append(
                    f"{label}: single_segment requires partition_id and partition_dimension"
                )
            primary_rows = component_groups.get(partition_id, [])
            disclosed_segments = [
                row for row in period_component_rows
                if str(row.get("row_type") or "").strip().lower() == "segment"
            ]
            if len(disclosed_segments) != 1:
                problems.append(
                    f"{label}: single_segment requires exactly one disclosed segment member; "
                    f"found {len(disclosed_segments)}"
                )
            _validate_component_group(
                partition_id,
                primary_rows,
                require_parent_reconciliation=True,
                partition_label="single-segment partition",
            )
            for group_id, group_rows in component_groups.items():
                if group_id != partition_id:
                    _validate_component_group(
                        group_id,
                        group_rows,
                        require_parent_reconciliation=False,
                    )
        elif reconciliation_status == "disclosure_limited":
            for group_id, group_rows in component_groups.items():
                _validate_component_group(
                    group_id,
                    group_rows,
                    require_parent_reconciliation=False,
                )

    marked_latest = [
        row for row in numeric_history
        if str(row.get("latest_actual") or "").strip().lower() in {"true", "1", "yes"}
    ]
    if len(marked_latest) != 1:
        problems.append(f"historical bridge requires exactly one numeric latest_actual row; found {len(marked_latest)}")
    numeric_interims = [
        row for row in numeric_history
        if str(row.get("period_type") or "").strip().lower() == "interim"
    ]
    if numeric_interims and marked_latest and marked_latest[0] not in numeric_interims:
        problems.append("a disclosed numeric interim must be the marked latest_actual")

    first_forecasts = [
        row for row in substantive
        if str(row.get("period_type") or "").strip().lower() == "first_forecast"
        and str(row.get("row_type") or "").strip().lower() == "consolidated"
        and str(row.get("actual_or_forecast") or "").strip().lower() == "forecast"
    ]
    if len(first_forecasts) != 1:
        problems.append(f"historical bridge requires exactly one consolidated first_forecast row; found {len(first_forecasts)}")
    elif marked_latest:
        forecast = first_forecasts[0]
        label = _row_label(forecast)
        latest = marked_latest[0]
        latest_period = str(latest.get("period") or "").strip()
        if str(forecast.get("bridge_from_period") or "").strip() != latest_period:
            problems.append(f"{label}: bridge_from_period must equal marked latest actual {latest_period}")
        if not str(forecast.get("forecast_bridge") or "").strip():
            problems.append(f"{label}: forecast_bridge narrative missing")
        driver_ids = _split_ids(forecast.get("driver_node_ids"))
        if not driver_ids:
            problems.append(f"{label}: forecast bridge driver_node_ids missing")
        elif graph_node_ids and not driver_ids <= graph_node_ids:
            problems.append(
                f"{label}: forecast bridge references unknown driver_node_ids "
                f"{sorted(driver_ids - graph_node_ids)}"
            )
        for field in HISTORICAL_KEY_FIELDS:
            actual_value = _finite_number(latest.get(field))
            forecast_value = _finite_number(forecast.get(field))
            delta_field = f"{field}_bridge_delta"
            delta = _finite_number(forecast.get(delta_field))
            if actual_value is None or forecast_value is None:
                problems.append(f"{label}: numeric first forecast missing {field}")
            elif delta is None:
                problems.append(f"{label}: {delta_field} must be numeric")
            elif not numbers_close(actual_value + delta, forecast_value):
                problems.append(
                    f"{label}: {delta_field} does not bridge {field} from {latest_period}"
                )

    if not strict:
        # Non-strict mode reports the same diagnostic contract; strictness is
        # retained in the signature for parity with sibling validators.
        return problems
    return problems


def validate_industry_profit_pool_rows(rows: list[dict[str, str]]) -> list[str]:
    """Validate an economic boundary and its component-to-total reconciliation.

    A profit-pool table is not substantive merely because it names one value-chain
    node. Every boundary/period must carry one total plus component and/or residual
    rows whose revenue and chosen profit measure reconcile to that total.
    """

    problems: list[str] = []
    substantive = [
        row for row in rows
        if not _placeholder(row.get("boundary_id"))
        and not _placeholder(row.get("value_chain_node"))
    ]
    if not substantive:
        return ["no substantive industry profit-pool rows"]

    grouping_fields = (
        "boundary_id", "period", "geography", "product_scope", "currency", "profit_measure"
    )
    groups: dict[tuple[str, ...], list[dict[str, str]]] = {}
    for index, row in enumerate(substantive, 1):
        label = str(row.get("value_chain_node") or f"row {index}").strip()
        for field in (*grouping_fields, "row_type"):
            if _placeholder(row.get(field)):
                problems.append(f"{label}: missing {field}")

        row_type = str(row.get("row_type") or "").strip().lower()
        if row_type not in INDUSTRY_PROFIT_POOL_ROW_TYPES:
            problems.append(
                f"{label}: row_type must be total, component, or residual"
            )
        for field in ("revenue_pool", "profit_pool"):
            if _finite_number(row.get(field)) is None:
                problems.append(f"{label}: {field} must be numeric")
        if not _split_ids(row.get("source_ids")):
            problems.append(f"{label}: source_ids missing")
        if not _split_ids(row.get("driver_node_ids")):
            problems.append(f"{label}: driver_node_ids missing")
        if not _valid_iso_date(row.get("data_vintage_at")):
            problems.append(f"{label}: data_vintage_at must be an ISO date")
        if str(row.get("status") or "").strip().lower() in {"", "pending", "tbd"}:
            problems.append(f"{label}: status is pending")

        key = tuple(str(row.get(field) or "").strip() for field in grouping_fields)
        groups.setdefault(key, []).append(row)

    for key, group_rows in groups.items():
        boundary_label = "/".join(item or "<blank>" for item in key)
        totals = [
            row for row in group_rows
            if str(row.get("row_type") or "").strip().lower() == "total"
        ]
        components = [
            row for row in group_rows
            if str(row.get("row_type") or "").strip().lower() in {"component", "residual"}
        ]
        if len(totals) != 1:
            problems.append(
                f"{boundary_label}: expected exactly one total row, found {len(totals)}"
            )
            continue
        if not components:
            problems.append(
                f"{boundary_label}: total has no component or residual rows to reconcile"
            )
            continue

        for field in ("revenue_pool", "profit_pool", "invested_capital"):
            total_value = _finite_number(totals[0].get(field))
            component_values = [_finite_number(row.get(field)) for row in components]
            # Invested capital is optional at row level. Reconcile it only when the
            # total and every child provide the measure; revenue and profit are
            # already required above.
            if total_value is None or any(value is None for value in component_values):
                continue
            component_sum = sum(value for value in component_values if value is not None)
            tolerance = max(1e-6, abs(total_value) * 0.001)
            if abs(component_sum - total_value) > tolerance:
                problems.append(
                    f"{boundary_label}: {field} components do not reconcile to total "
                    f"({component_sum:g} vs {total_value:g})"
                )
    return problems


def validate_operating_cycle_rows(
    rows: list[dict[str, str]],
    *,
    strict: bool = False,
    readiness_target: str = "",
    manifest_entity: str = "",
    source_ids: set[str] | None = None,
    data_series_ids: set[str] | None = None,
    graph_node_ids: set[str] | None = None,
    main_line_carriers: set[str] | None = None,
    main_line_relevant_nodes: set[str] | None = None,
    profit_pool_rows: list[dict[str, str]] | None = None,
) -> list[str]:
    """Validate the material cycle states and stock-flow equations selected.

    State families are business-model specific.  Omitted manufacturing or
    inventory states are not replaced by boilerplate not-material rows; an
    independent research review judges whether the selected states span the
    principal cycle risk.  Deterministic code validates the rows and equations
    that actually carry the forecast.
    """

    problems: list[str] = []
    known_boundaries = {
        str(row.get("boundary_id") or "").strip()
        for row in (profit_pool_rows or [])
        if not _placeholder(row.get("boundary_id"))
    }
    profit_pool_nodes = {
        node_id
        for row in (profit_pool_rows or [])
        if str(row.get("status") or "").strip().lower() not in {"", "pending", "tbd", "rejected"}
        for node_id in _split_ids(row.get("driver_node_ids"))
    }
    main_line_carriers = main_line_carriers or set()
    main_line_relevant_nodes = main_line_relevant_nodes or set(main_line_carriers)
    readiness = str(readiness_target or "").strip().lower()
    substantive = [
        row for row in rows
        if not _placeholder(row.get("branch_id"))
        and (
            not _placeholder(row.get("state_family"))
            or str(row.get("record_type") or "").strip().lower() == "equation_check"
        )
    ]
    if not substantive:
        return ["no substantive operating-cycle rows"]

    state_rows = [
        row for row in substantive
        if str(row.get("record_type") or "state").strip().lower() != "equation_check"
    ]
    equation_rows = [
        row for row in substantive
        if str(row.get("record_type") or "").strip().lower() == "equation_check"
    ]

    rows_by_branch: dict[str, list[dict[str, str]]] = {}
    for index, row in enumerate(state_rows, 1):
        branch_id = str(row.get("branch_id") or "").strip()
        family = str(row.get("state_family") or "").strip().lower()
        label = f"{branch_id or '<blank>'}:{family or f'row-{index}'}"
        rows_by_branch.setdefault(branch_id, []).append(row)

        if _placeholder(family):
            problems.append(f"{label}: state_family is required")
        for field in ("metric_name", "period", "frequency", "value", "unit", "applicability"):
            if _placeholder(row.get(field)):
                problems.append(f"{label}: missing {field}")
        if not _valid_iso_date(row.get("as_of")):
            problems.append(f"{label}: as_of must be an ISO date")
        if not _valid_iso_date(row.get("data_vintage_at")):
            problems.append(f"{label}: data_vintage_at must be an ISO date")

        applicability = str(row.get("applicability") or "").strip().lower()
        status = str(row.get("status") or "").strip().lower()
        linked_sources = _split_ids(row.get("source_ids"))
        linked_series = _split_ids(row.get("data_series_ids"))
        linked_nodes = _split_ids(row.get("driver_node_ids"))
        if source_ids is not None:
            unknown_sources = sorted(linked_sources - source_ids)
            if unknown_sources:
                problems.append(f"{label}: unknown source_ids {','.join(unknown_sources)}")
        if graph_node_ids is not None:
            unknown_nodes = sorted(linked_nodes - graph_node_ids)
            if unknown_nodes:
                problems.append(f"{label}: unknown driver_node_ids {','.join(unknown_nodes)}")
        if data_series_ids is not None:
            unknown_series = sorted(linked_series - data_series_ids)
            if unknown_series:
                problems.append(f"{label}: unknown data_series_ids {','.join(unknown_series)}")
        if applicability in {"not_material", "not_applicable"}:
            if status != "not_material_with_reason":
                problems.append(f"{label}: not-material row requires status not_material_with_reason")
            if str(row.get("value") or "").strip().lower() not in {"not_applicable", "n/a"}:
                problems.append(f"{label}: not-material row value must be not_applicable")
            if _placeholder(row.get("notes")):
                problems.append(f"{label}: not-material row requires a reason in notes")
            if not linked_sources:
                problems.append(f"{label}: not-material reason requires source_ids")
            if not linked_nodes:
                problems.append(f"{label}: not-material reason requires driver_node_ids")

            entity_id = str(row.get("entity_id") or "").strip()
            if _placeholder(entity_id):
                problems.append(f"{label}: not-material reason requires entity_id")
            elif manifest_entity and entity_id.casefold() != manifest_entity.strip().casefold():
                problems.append(f"{label}: entity_id does not match manifest entity {manifest_entity}")

            materiality_basis = str(row.get("materiality_basis") or "").strip().lower()
            if materiality_basis not in OPERATING_CYCLE_MATERIALITY_BASES:
                problems.append(
                    f"{label}: materiality_basis must be one of "
                    + ",".join(sorted(OPERATING_CYCLE_MATERIALITY_BASES))
                )

            boundary_id = str(row.get("profit_pool_boundary_id") or "").strip()
            if _placeholder(boundary_id):
                problems.append(f"{label}: not-material reason requires profit_pool_boundary_id")
            elif profit_pool_rows is not None and boundary_id not in known_boundaries:
                problems.append(f"{label}: unknown profit-pool boundary {boundary_id}")

            if linked_nodes & main_line_carriers:
                problems.append(f"{label}: main-line carrier cannot be marked not-material")
            if linked_nodes & profit_pool_nodes:
                problems.append(f"{label}: profit-pool material node cannot be marked not-material")
            continue

        if applicability not in {"material", "applicable"}:
            problems.append(f"{label}: applicability must be material, applicable, or not_material")
        if _finite_number(row.get("value")) is None:
            problems.append(f"{label}: applicable value must be numeric")
        if not _split_ids(row.get("source_ids")):
            problems.append(f"{label}: source_ids missing")
        if not _split_ids(row.get("data_series_ids")):
            problems.append(f"{label}: data_series_ids missing")
        if not _split_ids(row.get("driver_node_ids")):
            problems.append(f"{label}: driver_node_ids missing")
        if status in {"", "pending", "tbd", "not_material_with_reason"}:
            problems.append(f"{label}: status is not an accepted applicable state")
        if (
            strict
            and readiness not in {"screen-grade", "not-decision-ready"}
            and linked_nodes
            and not (linked_nodes & (main_line_relevant_nodes | profit_pool_nodes))
        ):
            problems.append(
                f"{label}: material operating-cycle row does not link to a "
                "main-line or profit-pool causal node"
            )
        lead_lag = str(row.get("lead_lag_days") or "").strip()
        if lead_lag and _finite_number(lead_lag) is None:
            problems.append(f"{label}: lead_lag_days must be numeric when supplied")

    for branch_id, branch_rows in rows_by_branch.items():
        if strict and readiness not in {"screen-grade", "not-decision-ready"}:
            material_nodes = {
                node_id
                for row in branch_rows
                if str(row.get("applicability") or "").strip().lower() in {"material", "applicable"}
                for node_id in _split_ids(row.get("driver_node_ids"))
            }
            economically_linked = main_line_relevant_nodes | profit_pool_nodes
            if material_nodes and not (material_nodes & economically_linked):
                problems.append(
                    f"{branch_id or '<blank>'}: material operating-cycle rows do not link "
                    "to a main-line or profit-pool causal node"
                )

    equations_by_branch: dict[str, dict[str, list[dict[str, str]]]] = {}
    seen_equation_ids: set[str] = set()
    for index, row in enumerate(equation_rows, 1):
        branch_id = str(row.get("branch_id") or "").strip()
        equation_id = str(row.get("equation_id") or "").strip()
        equation_type = str(row.get("equation_type") or "").strip().lower()
        label = f"{branch_id or '<blank>'}:{equation_type or f'equation-{index}'}"
        equations_by_branch.setdefault(branch_id, {}).setdefault(equation_type, []).append(row)

        if _placeholder(equation_id):
            problems.append(f"{label}: equation_id missing")
        elif equation_id in seen_equation_ids:
            problems.append(f"{label}: duplicate equation_id {equation_id}")
        seen_equation_ids.add(equation_id)
        if equation_type not in OPERATING_CYCLE_EQUATION_TYPES:
            problems.append(f"{label}: unsupported equation_type")
            continue
        for field in ("period", "frequency"):
            if _placeholder(row.get(field)):
                problems.append(f"{label}: missing {field}")
        if not _valid_iso_date(row.get("as_of")):
            problems.append(f"{label}: as_of must be an ISO date")
        if not _valid_iso_date(row.get("data_vintage_at")):
            problems.append(f"{label}: data_vintage_at must be an ISO date")
        if not _valid_model_cell_or_formula(row.get("model_cell_or_formula")):
            problems.append(f"{label}: model_cell_or_formula must be an exact workbook cell or executable formula")

        status = str(row.get("equation_status") or "").strip().lower()
        linked_sources = _split_ids(row.get("source_ids"))
        linked_series = _split_ids(row.get("data_series_ids"))
        linked_nodes = _split_ids(row.get("driver_node_ids"))
        if not linked_sources:
            problems.append(f"{label}: source_ids missing")
        elif source_ids is not None and linked_sources - source_ids:
            problems.append(f"{label}: unknown source_ids {','.join(sorted(linked_sources - source_ids))}")
        if not linked_series and status == "accepted":
            problems.append(f"{label}: data_series_ids missing")
        elif linked_series and data_series_ids is not None and linked_series - data_series_ids:
            problems.append(f"{label}: unknown data_series_ids {','.join(sorted(linked_series - data_series_ids))}")
        if not linked_nodes:
            problems.append(f"{label}: driver_node_ids missing")
        elif graph_node_ids is not None and linked_nodes - graph_node_ids:
            problems.append(f"{label}: unknown driver_node_ids {','.join(sorted(linked_nodes - graph_node_ids))}")

        if status not in OPERATING_CYCLE_EQUATION_STATUSES:
            problems.append(f"{label}: equation_status must be accepted, disclosure_limited or not_applicable")
            continue
        if status in {"disclosure_limited", "not_applicable"}:
            if _placeholder(row.get("unavailable_reason")):
                problems.append(f"{label}: {status} requires unavailable_reason")
            if status == "disclosure_limited" and readiness not in {"screen-grade", "not-decision-ready"}:
                problems.append(
                    f"{label}: disclosure_limited stock-flow equation requires readiness_target "
                    f"capped at screen-grade (current: {readiness or 'unset'})"
                )
            if status == "not_applicable":
                basis = str(row.get("materiality_basis") or "").strip().lower()
                if basis not in OPERATING_CYCLE_MATERIALITY_BASES:
                    problems.append(
                        f"{label}: not_applicable equation requires a controlled materiality_basis"
                    )
            continue

        required_operands = {
            "channel_inventory_roll": ("lhs_value", "rhs_1_value", "rhs_2_value"),
            "company_inventory_roll": ("lhs_value", "rhs_1_value", "rhs_2_value", "rhs_3_value"),
            "revenue_recognition": ("lhs_value", "rhs_1_value", "rhs_2_value"),
        }[equation_type]
        values = {field: _finite_number(row.get(field)) for field in required_operands}
        missing_values = [field for field, value in values.items() if value is None]
        tolerance = _finite_number(row.get("check_tolerance"))
        declared_residual = _finite_number(row.get("check_residual"))
        factor = _finite_number(row.get("unit_conversion_factor"))
        if missing_values:
            problems.append(f"{label}: non-numeric " + ",".join(missing_values))
        if tolerance is None or tolerance < 0:
            problems.append(f"{label}: check_tolerance must be a non-negative number")
        if declared_residual is None:
            problems.append(f"{label}: check_residual must be numeric")
        if factor is None or factor <= 0:
            problems.append(f"{label}: unit_conversion_factor must be positive")

        required_units = {
            "channel_inventory_roll": ("lhs_unit", "rhs_1_unit", "rhs_2_unit"),
            "company_inventory_roll": ("lhs_unit", "rhs_1_unit", "rhs_2_unit", "rhs_3_unit"),
            "revenue_recognition": ("lhs_unit", "rhs_1_unit", "rhs_2_unit"),
        }[equation_type]
        if any(_placeholder(row.get(field)) for field in required_units):
            problems.append(f"{label}: equation units are incomplete")
        elif equation_type in {"channel_inventory_roll", "company_inventory_roll"}:
            dimensions = {_unit_dimension(row.get(field)) for field in required_units}
            if len(dimensions) != 1:
                problems.append(f"{label}: additive stock-flow units do not match")
            if factor is not None and abs(factor - 1.0) > 1e-12:
                problems.append(f"{label}: additive stock-flow unit_conversion_factor must equal 1")
        else:
            price_unit = str(row.get("rhs_2_unit") or "").strip()
            if "/" not in price_unit:
                problems.append(f"{label}: realized-price unit must be output_unit/quantity_unit")
            else:
                price_numerator, price_denominator = price_unit.split("/", 1)
                if _unit_dimension(row.get("lhs_unit")) != _unit_dimension(price_numerator):
                    problems.append(f"{label}: recognized-revenue unit does not match price numerator")
                if _unit_dimension(row.get("rhs_1_unit")) != _unit_dimension(price_denominator):
                    problems.append(f"{label}: accepted-quantity unit does not match price denominator")

        if not missing_values and tolerance is not None and declared_residual is not None and factor is not None:
            lhs = float(values["lhs_value"])
            rhs_1 = float(values["rhs_1_value"])
            rhs_2 = float(values["rhs_2_value"])
            if equation_type == "channel_inventory_roll":
                computed_residual = lhs - (rhs_1 + rhs_2)
            elif equation_type == "company_inventory_roll":
                rhs_3 = float(values["rhs_3_value"])
                computed_residual = lhs - (rhs_1 + rhs_2 - rhs_3)
            else:
                computed_residual = lhs - (rhs_1 * rhs_2 * factor)
            if abs(computed_residual) > tolerance:
                problems.append(
                    f"{label}: {equation_type} does not reconcile; computed residual {computed_residual:g}"
                )
            if abs(declared_residual - computed_residual) > max(tolerance, 1e-6):
                problems.append(
                    f"{label}: check_residual does not equal recomputed residual {computed_residual:g}"
                )

    return problems


def validate_earnings_power_rows(
    rows: list[dict[str, str]],
    *,
    source_ids: set[str],
    graph_node_ids: set[str],
    snapshot: dict | None = None,
    readiness_target: str = "",
    material_profit_impact_pct: object = None,
) -> list[str]:
    """Validate the reported-to-normalized profit bridge without scoring it.

    The gate is deliberately structural: an analyst may conclude that a line is
    human-required, but may not replace the profit layers with one consolidated
    margin or silently omit cash/accrual, investment, cycle and fade reasoning.
    """

    problems: list[str] = []
    active = [
        row for row in rows
        if not _placeholder(row.get("period")) and not _placeholder(row.get("profit_layer"))
    ]
    if not active:
        return ["no substantive earnings-power rows"]

    by_period: dict[str, list[dict[str, str]]] = {}
    human_required_rows: list[dict[str, str]] = []
    for row in active:
        period = str(row.get("period") or "").strip()
        layer = str(row.get("profit_layer") or "").strip().lower()
        label = f"{period or '<blank>'}:{layer or '<blank>'}"
        by_period.setdefault(period, []).append(row)
        if layer not in EARNINGS_POWER_LAYERS:
            problems.append(f"{label}: unknown profit_layer")
        status = str(row.get("status") or "").strip().lower()
        if status not in {"accepted", "human_required", "not_material_with_reason"}:
            problems.append(f"{label}: status must be accepted, human_required, or not_material_with_reason")
            continue
        if status == "human_required":
            if _placeholder(row.get("notes")):
                problems.append(f"{label}: unresolved or not-material row needs a reason in notes")
            human_required_rows.append(row)
            continue
        if status == "not_material_with_reason" and _placeholder(row.get("notes")):
            problems.append(f"{label}: unresolved or not-material row needs a reason in notes")

        # Accepted rows and conditional not-material rows share the same
        # numeric, evidence and graph contract.  Immateriality may waive a
        # materiality conclusion; it may never waive the measured bridge.
        numeric_fields = (
            "reported_amount", "bridge_from_prior_layer", "normalization_adjustment", "normalized_amount",
            "cash_support", "accrual_component", "investment_adjustment", "cycle_adjustment",
            "fade_target", "fade_horizon",
        )
        values = {field: _finite_number(row.get(field)) for field in numeric_fields}
        missing_numeric = [field for field, value in values.items() if value is None]
        if missing_numeric:
            problems.append(f"{label}: non-numeric " + ",".join(missing_numeric))
        elif abs(
            float(values["reported_amount"])
            + float(values["normalization_adjustment"])
            - float(values["normalized_amount"])
        ) > max(1e-6, abs(float(values["normalized_amount"])) * 0.001):
            problems.append(f"{label}: reported + normalization does not equal normalized_amount")

        if layer == "gaap_operating_profit" and status in {
            "accepted", "not_material_with_reason",
        }:
            quality_fields = ("operating_tax_expense", "nopat", "noa_bridge_residual")
            quality_values = {field: _finite_number(row.get(field)) for field in quality_fields}
            missing_quality = [field for field, value in quality_values.items() if value is None]
            if missing_quality:
                problems.append(f"{label}: non-numeric " + ",".join(missing_quality))
            elif values["reported_amount"] is not None:
                nopat = float(quality_values["nopat"])
                operating_tax = float(quality_values["operating_tax_expense"])
                reported_operating_profit = float(values["reported_amount"])
                identity_tolerance = max(1e-6, abs(nopat) * 0.001)
                if abs(reported_operating_profit - operating_tax - nopat) > identity_tolerance:
                    problems.append(
                        f"{label}: reported operating profit less operating_tax_expense must equal nopat"
                    )
                cash_support = values["cash_support"]
                accrual_component = values["accrual_component"]
                if cash_support is not None and accrual_component is not None:
                    recomputed_residual = nopat - float(cash_support) - float(accrual_component)
                    if abs(recomputed_residual) > identity_tolerance:
                        problems.append(
                            f"{label}: nopat must equal cash_support plus accrual_component (change in net operating assets)"
                        )
                    if abs(float(quality_values["noa_bridge_residual"]) - recomputed_residual) > identity_tolerance:
                        problems.append(
                            f"{label}: noa_bridge_residual does not equal the recomputed residual"
                        )

        for field in ("persistence_driver", "competitive_response"):
            if _placeholder(row.get(field)):
                problems.append(f"{label}: missing {field}")
        linked_sources = _split_ids(row.get("source_ids"))
        linked_nodes = _split_ids(row.get("driver_node_ids"))
        if not linked_sources:
            problems.append(f"{label}: source_ids missing")
        elif linked_sources - source_ids:
            problems.append(f"{label}: unknown source ids " + ",".join(sorted(linked_sources - source_ids)))
        if not linked_nodes:
            problems.append(f"{label}: driver_node_ids missing")
        elif linked_nodes - graph_node_ids:
            problems.append(f"{label}: unknown driver nodes " + ",".join(sorted(linked_nodes - graph_node_ids)))

    for period, period_rows in by_period.items():
        rows_by_layer: dict[str, list[dict[str, str]]] = {}
        for row in period_rows:
            layer = str(row.get("profit_layer") or "").strip().lower()
            rows_by_layer.setdefault(layer, []).append(row)
        layers = set(rows_by_layer)
        missing = EARNINGS_POWER_LAYERS - layers
        if missing:
            problems.append(f"{period}: missing profit layer " + ",".join(sorted(missing)))
        duplicates = sorted(layer for layer, layer_rows in rows_by_layer.items() if len(layer_rows) > 1)
        if duplicates:
            problems.append(f"{period}: duplicate profit layer " + ",".join(duplicates))

        not_material_layers = [
            layer
            for layer, layer_rows in rows_by_layer.items()
            if len(layer_rows) == 1
            and str(layer_rows[0].get("status") or "").strip().lower()
            == "not_material_with_reason"
        ]
        readiness = str(readiness_target or "").strip().lower()
        if len(not_material_layers) == len(period_rows) and readiness == "research-grade":
            problems.append(
                f"{period}: all earnings-power layers are not_material_with_reason; "
                "research-grade requires a measured profit chain"
            )
        if not_material_layers:
            threshold = _finite_number(material_profit_impact_pct)
            revenue_rows = rows_by_layer.get("revenue") or []
            revenue_amount = (
                _finite_number(revenue_rows[0].get("reported_amount"))
                if len(revenue_rows) == 1 else None
            )
            if threshold is None or threshold < 0:
                problems.append(
                    f"{period}: not-material layer requires non-negative manifest material_profit_impact_pct"
                )
            for layer in not_material_layers:
                row = rows_by_layer[layer][0]
                bridge = _finite_number(row.get("bridge_from_prior_layer"))
                if layer == "revenue":
                    problems.append(f"{period}:revenue: revenue anchor cannot be not-material")
                    continue
                if bridge is None or revenue_amount is None:
                    problems.append(
                        f"{period}:{layer}: not-material test needs numeric bridge and revenue anchor"
                    )
                    continue
                if revenue_amount == 0:
                    if bridge != 0:
                        problems.append(
                            f"{period}:{layer}: non-zero bridge cannot be immaterial against zero revenue"
                        )
                    impact_pct = 0.0
                else:
                    impact_pct = abs(bridge) / abs(revenue_amount) * 100
                if threshold is not None and threshold >= 0 and impact_pct > threshold:
                    problems.append(
                        f"{period}:{layer}: bridge impact {impact_pct:.6g}% exceeds materiality threshold "
                        f"{threshold:.6g}%"
                    )

        if not missing and not duplicates and all(
            str(rows_by_layer[layer][0].get("status") or "").strip().lower()
            in {"accepted", "not_material_with_reason"}
            for layer in EARNINGS_POWER_LAYER_ORDER
        ):
            previous_reported: float | None = None
            for layer in EARNINGS_POWER_LAYER_ORDER:
                row = rows_by_layer[layer][0]
                reported = _finite_number(row.get("reported_amount"))
                bridge = _finite_number(row.get("bridge_from_prior_layer"))
                if reported is None or bridge is None:
                    continue
                tolerance = max(1e-6, abs(reported) * 0.001)
                if previous_reported is None:
                    if abs(bridge) > tolerance:
                        problems.append(f"{period}:{layer}: first layer bridge_from_prior_layer must be zero")
                elif abs(previous_reported + bridge - reported) > tolerance:
                    problems.append(
                        f"{period}:{layer}: prior reported + bridge does not equal reported_amount"
                    )
                previous_reported = reported

            nia_row = rows_by_layer["gaap_net_income_attributable"][0]
            tax_expense = _finite_number(nia_row.get("tax_expense"))
            nci_net_income = _finite_number(
                nia_row.get("net_income_attributable_to_noncontrolling_interests")
            )
            pretax_reported = _finite_number(
                rows_by_layer["pretax_profit"][0].get("reported_amount")
            )
            attributable_reported = _finite_number(nia_row.get("reported_amount"))
            if tax_expense is None or nci_net_income is None:
                problems.append(
                    f"{period}:gaap_net_income_attributable: tax_expense and "
                    "net_income_attributable_to_noncontrolling_interests must be numeric; "
                    "use explicit zero when no minority claim exists"
                )
            elif (
                pretax_reported is None
                or attributable_reported is None
                or abs(pretax_reported - tax_expense - nci_net_income - attributable_reported)
                > max(1e-6, abs(attributable_reported) * 0.001)
            ):
                problems.append(
                    f"{period}:gaap_net_income_attributable: reported amount must equal pretax less "
                    "tax and non-controlling interest"
                )

    readiness = str(readiness_target or "").strip().lower()
    if human_required_rows:
        fully_unresolved_periods = [
            period
            for period, period_rows in by_period.items()
            if period_rows and all(
                str(row.get("status") or "").strip().lower() == "human_required"
                for row in period_rows
            )
        ]
        if fully_unresolved_periods:
            if readiness != "not-decision-ready":
                problems.append(
                    f"{','.join(sorted(fully_unresolved_periods))}: all earnings-power layers are "
                    "human_required; readiness_target must be not-decision-ready"
                )
        elif readiness not in {"screen-grade", "not-decision-ready"}:
            problems.append(
                "human_required earnings-power layers require readiness_target capped at screen-grade"
            )
        if snapshot is not None:
            disclosures = snapshot.get("human_required")
            if not isinstance(disclosures, list) or not any(
                not _placeholder(item) for item in disclosures
            ):
                problems.append("snapshot.human_required must disclose unresolved earnings-power layers")

    if snapshot is not None:
        snapshot_metrics = {
            "revenue": "revenue_point",
            "gaap_operating_profit": "operating_profit_point",
            "pretax_profit": "pretax_profit_point",
            "gaap_net_income_attributable": "profit_point",
        }
        outputs = snapshot.get("outputs") or {}
        integrated_rows = ((snapshot.get("integrated_model") or {}).get("periods") or [])
        integrated_by_period: dict[str, dict] = {}
        for index, integrated_row in enumerate(integrated_rows):
            if not isinstance(integrated_row, dict):
                problems.append(f"integrated statement row {index + 1} must be an object")
                continue
            integrated_period = str(integrated_row.get("period") or "").strip()
            if _placeholder(integrated_period):
                continue
            if integrated_period in integrated_by_period:
                problems.append(f"{integrated_period}: duplicate integrated statement period")
            else:
                integrated_by_period[integrated_period] = integrated_row
        for horizon, output in outputs.items():
            if not isinstance(output, dict) or _placeholder(output.get("period")):
                continue
            period = str(output["period"]).strip()
            integrated_row = integrated_by_period.get(period)
            if not integrated_row:
                problems.append(f"{period}: snapshot {horizon} has no integrated statement period")
            period_rows = by_period.get(period)
            if not period_rows:
                problems.append(f"{period}: snapshot {horizon} has no earnings-power rows")
                continue
            rows_by_layer = {
                str(row.get("profit_layer") or "").strip().lower(): row
                for row in period_rows
            }
            for layer, metric in snapshot_metrics.items():
                row = rows_by_layer.get(layer)
                if not row or str(row.get("status") or "").strip().lower() not in {
                    "accepted", "not_material_with_reason"
                }:
                    continue
                reported = _finite_number(row.get("reported_amount"))
                snapshot_value = _finite_number(output.get(metric))
                if metric == "profit_point" and snapshot_value is None:
                    snapshot_value = _finite_number(output.get("net_income_point"))
                if reported is None or snapshot_value is None:
                    problems.append(f"{period}:{layer}: snapshot {metric} missing or non-numeric")
                    continue
                tolerance = max(1e-6, abs(snapshot_value) * 0.001)
                if abs(reported - snapshot_value) > tolerance:
                    problems.append(
                        f"{period}:{layer}: reported_amount does not reconcile to snapshot {metric}"
                    )
            if integrated_row:
                income = integrated_row.get("income_statement") or {}
                integrated_metrics = {
                    "revenue": "revenue",
                    "gaap_operating_profit": "operating_profit",
                    "pretax_profit": "pretax_profit",
                    "gaap_net_income_attributable": "net_income_attributable",
                }
                for layer, statement_metric in integrated_metrics.items():
                    row = rows_by_layer.get(layer)
                    if not row or str(row.get("status") or "").strip().lower() not in {
                        "accepted", "not_material_with_reason"
                    }:
                        continue
                    reported = _finite_number(row.get("reported_amount"))
                    statement_value = _finite_number(income.get(statement_metric))
                    if reported is None or statement_value is None:
                        problems.append(
                            f"{period}:{layer}: integrated statement {statement_metric} missing or non-numeric"
                        )
                    elif abs(reported - statement_value) > max(
                        1e-6, abs(statement_value) * 0.001
                    ):
                        problems.append(
                            f"{period}:{layer}: reported_amount does not reconcile to integrated "
                            f"statement {statement_metric}"
                        )
                nia_row = rows_by_layer.get("gaap_net_income_attributable")
                if nia_row:
                    bridge_pairs = (
                        ("tax_expense", "tax_expense"),
                        (
                            "net_income_attributable_to_noncontrolling_interests",
                            "net_income_attributable_to_noncontrolling_interests",
                        ),
                    )
                    for row_field, statement_field in bridge_pairs:
                        row_value = _finite_number(nia_row.get(row_field))
                        statement_value = _finite_number(income.get(statement_field))
                        if row_value is None or statement_value is None or abs(
                            row_value - statement_value
                        ) > max(1e-6, abs(statement_value or 0.0) * 0.001):
                            problems.append(
                                f"{period}:gaap_net_income_attributable: {row_field} does not reconcile "
                                f"to integrated statement {statement_field}"
                            )
    return problems


def validate_monitor_rows(
    rows: list[dict[str, str]],
    *,
    graph_nodes: dict[str, dict],
    main_line_carriers: set[str],
    main_line_falsifications: set[str],
    source_ids: set[str],
    material_technology_node_ids: set[str] | None = None,
) -> tuple[list[str], list[dict[str, str]]]:
    """Validate that monitoring rows are executable cells, not prose reminders."""

    problems: list[str] = []
    active_rows: list[dict[str, str]] = []
    material_technology_node_ids = material_technology_node_ids or set()
    for row in rows:
        driver_id = str(row.get("driver_id") or "").strip()
        if driver_id.upper() in {"", "TBD", "REPLACE"}:
            continue
        status = str(row.get("status") or "").strip().lower()
        if status not in {"active", "retired"}:
            problems.append(f"{driver_id}: status must be active or retired")
            continue
        if status == "retired":
            continue
        active_rows.append(row)
        if driver_id not in graph_nodes:
            problems.append(f"unknown driver_id {driver_id}")

        cell = str(row.get("model_cell_or_formula") or "").strip()
        if not cell:
            problems.append(f"{driver_id}: missing model_cell_or_formula")
        elif not CELL_REFERENCE_RE.fullmatch(cell):
            problems.append(f"{driver_id}: model_cell_or_formula must be an exact workbook cell reference")

        monitor_type = str(row.get("monitor_type") or "").strip().lower()
        if monitor_type not in {"continuous", "milestone"}:
            problems.append(f"{driver_id}: monitor_type must be continuous or milestone")
        for field in ("thesis_link", "series", "frequency", "unit", "action_if_breached", "owner"):
            if not str(row.get(field) or "").strip():
                problems.append(f"{driver_id}: missing {field}")

        linked_sources = _split_ids(row.get("source_id"))
        if not linked_sources:
            problems.append(f"{driver_id}: missing source_id")
        elif linked_sources - source_ids:
            problems.append(f"{driver_id}: unknown source_id(s) {','.join(sorted(linked_sources - source_ids))}")

        for field in ("last_observed_at", "next_expected_at"):
            if not _valid_iso_date(row.get(field)):
                problems.append(f"{driver_id}: {field} must be an ISO date")
        if monitor_type == "milestone" and not _valid_iso_date(row.get("milestone_date")):
            problems.append(f"{driver_id}: milestone monitor requires an ISO milestone_date")

        for field in ("current_value", "model_value", "trigger_value"):
            if not _numeric_text(row.get(field)):
                problems.append(f"{driver_id}: {field} must be numeric")
        operator = str(row.get("trigger_operator") or "").strip().lower()
        if operator not in MONITOR_OPERATORS:
            problems.append(f"{driver_id}: invalid trigger_operator {operator or 'blank'}")

    if not active_rows:
        problems.append("no substantive active monitoring rows")
    monitored_ids = {str(row.get("driver_id") or "").strip() for row in active_rows}
    if main_line_carriers and not (monitored_ids & main_line_carriers):
        problems.append("no main-line carrier has an executable frequency/threshold monitor")
    if main_line_falsifications and not (monitored_ids & main_line_falsifications):
        problems.append("no main-line falsification node has an executable monitor")
    milestone_ids = {
        str(row.get("driver_id") or "").strip()
        for row in active_rows
        if str(row.get("monitor_type") or "").strip().lower() == "milestone"
    }
    unmonitored_tech = material_technology_node_ids - milestone_ids
    if unmonitored_tech:
        problems.append(
            "material technology gate lacks milestone monitor: " + ",".join(sorted(unmonitored_tech))
        )
    return problems, active_rows


def validate_scenario_collection_presence(scenarios: object) -> list[str]:
    """Require one authored reference path without imposing a rival-count proxy.

    Material rival adequacy is a frozen independent-review judgment.  Every
    path that is actually authored remains subject to probability, shock,
    profit-chain and workbook-binding contracts below.
    """

    if not isinstance(scenarios, list) or not scenarios:
        return ["scenario set must contain an authored reference path"]
    return []


def validate_scenario_shocks(
    scenarios: list[dict],
    *,
    graph_nodes: dict[str, dict],
    forecast_periods: set[str] | None = None,
) -> list[str]:
    """Require every ordinary scenario shock to be executable in the model.

    A named node and value are not sufficient: unit, workbook destination,
    effective period and lag determine what the shock actually changes and
    when it reaches the statements.
    """

    problems: list[str] = []
    forecast_periods = {
        str(period).strip() for period in (forecast_periods or set()) if str(period).strip()
    }

    def _declared_period(value: str) -> bool:
        if not forecast_periods:
            return True
        if value in forecast_periods:
            return True
        normalized_value = re.sub(r"[\s_-]+", "", value.upper())
        normalized_declared = {
            re.sub(r"[\s_-]+", "", period.upper()) for period in forecast_periods
        }
        if normalized_value in normalized_declared:
            return True
        for declared in normalized_declared:
            annual = re.fullmatch(r"(?:FY)?(20\d{2})", declared)
            if not annual:
                continue
            year = annual.group(1)
            subperiod = r"(?:Q[1-4]|H[12]|M(?:0?[1-9]|1[0-2]))"
            if re.fullmatch(rf"(?:FY)?{year}{subperiod}", normalized_value):
                return True
            if re.fullmatch(rf"{subperiod}(?:FY)?{year}", normalized_value):
                return True
        return False

    for scenario_index, scenario in enumerate(scenarios, 1):
        if not isinstance(scenario, dict):
            problems.append(f"scenario-{scenario_index}: scenario must be an object")
            continue
        scenario_id = str(scenario.get("id") or "").strip() or f"scenario-{scenario_index}"
        shocks = scenario.get("shocks")
        if not isinstance(shocks, list):
            problems.append(f"{scenario_id}: shocks must be an array")
            continue
        seen_nodes: set[str] = set()
        for shock_index, shock in enumerate(shocks, 1):
            if not isinstance(shock, dict):
                problems.append(f"{scenario_id}:shock-{shock_index}: shock must be an object")
                continue
            node_id = str(shock.get("node_id") or "").strip()
            label = f"{scenario_id}:{node_id or f'shock-{shock_index}'}"
            node = graph_nodes.get(node_id)
            if not node:
                problems.append(f"{label}: shock references unknown node {node_id or '<blank>'}")
            elif str(node.get("kind") or "").strip().lower() not in {
                "input", "assumption", "state", "observable", "competitor_response"
            }:
                problems.append(f"{label}: cannot shock derived/output node {node_id}")
            if node_id in seen_nodes:
                problems.append(f"{label}: duplicate shock to the same node within one scenario")
            seen_nodes.add(node_id)

            if _placeholder(shock.get("operation")):
                problems.append(f"{label}: operation is required")
            if strict_finite_number(shock.get("value")) is None:
                problems.append(
                    f"{label}: value must be a finite authored JSON number"
                )
            unit = str(shock.get("unit") or "").strip()
            if not unit:
                problems.append(f"{label}: unit is required")
            elif node:
                node_unit = str(node.get("unit") or "").strip()
                if not node_unit:
                    problems.append(f"{label}: graph node has no unit to validate the shock")
                elif _unit_dimension(unit) != _unit_dimension(node_unit):
                    problems.append(
                        f"{label}: shock unit {unit} does not match node unit {node_unit}"
                    )

            if not _valid_model_cell_or_formula(shock.get("model_cell_or_formula")):
                problems.append(
                    f"{label}: model_cell_or_formula must be an exact workbook cell or executable formula"
                )
            effective_period = str(shock.get("effective_period") or "").strip()
            if not effective_period:
                problems.append(f"{label}: effective_period is required")
            elif not _declared_period(effective_period):
                problems.append(
                    f"{label}: effective_period {effective_period} is outside declared forecast periods "
                    f"{sorted(forecast_periods)}"
                )
            lag = shock.get("lag_periods")
            if not isinstance(lag, int) or isinstance(lag, bool) or lag < 0:
                problems.append(f"{label}: lag_periods must be a non-negative integer")
    return problems


def validate_scenario_roles(scenarios: list[dict]) -> list[str]:
    """Separate canonical-path semantics from analyst-chosen scenario names.

    The role is machine-readable; the id is a free, human-readable description.
    Exactly one reference path reconciles to the integrated statements and point
    outputs. Alternatives exist only when a named causal shock distinguishes
    their state, without imposing a fixed number of rival paths.
    """

    return validate_scenario_role_semantics(scenarios)


def validate_scenario_profit_chains(
    scenarios: list[dict],
    *,
    forecast_periods: set[str],
    snapshot_outputs: dict,
    integrated_periods: list[dict],
) -> list[str]:
    """Recompute every named scenario as one joint reported-profit path.

    Scenario ranges are not independent marginal intervals.  The low and high
    snapshot tuples each name one scenario, and every published layer must
    equal the same scenario-period row.  This prevents revenue from one joint
    state being silently combined with profit or tax from another state.
    """

    chain_fields = PROFIT_CHAIN_FIELDS
    point_fields = {
        "revenue": "revenue_point",
        "operating_profit": "operating_profit_point",
        "pretax_profit": "pretax_profit_point",
        "tax_expense": "tax_expense_point",
        "net_income_attributable_to_noncontrolling_interests":
            "noncontrolling_interest_net_income_point",
        "net_income_attributable": "net_income_point",
    }
    range_fields = {
        "revenue": "revenue",
        "operating_profit": "operating_profit",
        "pretax_profit": "pretax_profit",
        "tax_expense": "tax_expense",
        "net_income_attributable_to_noncontrolling_interests":
            "noncontrolling_interest_net_income",
        "net_income_attributable": "net_income",
    }

    def close(left: object, right: object) -> bool:
        left_number = strict_finite_number(left)
        right_number = strict_finite_number(right)
        return (
            left_number is not None
            and right_number is not None
            and numbers_close(left_number, right_number)
        )

    problems: list[str] = validate_scenario_roles(scenarios)
    declared_periods = {
        str(period).strip() for period in forecast_periods if str(period).strip()
    }

    ordered_periods = sorted(declared_periods, key=period_sort_key)
    period_positions = {period: index for index, period in enumerate(ordered_periods)}

    scenario_rows: dict[str, dict[str, dict]] = {}
    scenario_ids: set[str] = set()
    joint_state_owner: dict[str, str] = {}

    for scenario_index, scenario in enumerate(scenarios, 1):
        if not isinstance(scenario, dict):
            continue
        scenario_id = str(scenario.get("id") or "").strip() or f"scenario-{scenario_index}"
        scenario_ids.add(scenario_id)
        raw_rows = scenario.get("profit_chain_periods")
        if not isinstance(raw_rows, list) or not raw_rows:
            problems.append(f"{scenario_id}: profit_chain_periods missing or empty")
            raw_rows = []
        by_period: dict[str, dict] = {}
        shocks = scenario.get("shocks") if isinstance(scenario.get("shocks"), list) else []
        shock_node_ids = {
            str(shock.get("node_id") or "").strip()
            for shock in shocks if isinstance(shock, dict) and str(shock.get("node_id") or "").strip()
        }
        shock_by_node_id = {
            str(shock.get("node_id") or "").strip(): shock
            for shock in shocks
            if isinstance(shock, dict) and str(shock.get("node_id") or "").strip()
        }
        linked_shock_ids: set[str] = set()
        scenario_joint_state_ids: set[str] = set()

        for row_index, row in enumerate(raw_rows, 1):
            if not isinstance(row, dict):
                problems.append(f"{scenario_id}:profit-chain-{row_index}: must be an object")
                continue
            period = str(row.get("period") or "").strip()
            label = f"{scenario_id}:{period or f'profit-chain-{row_index}'}"
            if not period:
                problems.append(f"{label}: period is required")
                continue
            if period in by_period:
                problems.append(f"{label}: duplicate profit-chain period")
                continue
            by_period[period] = row

            problems.extend(validate_profit_chain_equations(row, label=label))

            model_cells = row.get("model_cells")
            if not isinstance(model_cells, dict):
                problems.append(f"{label}: model_cells must bind every profit-chain layer")
                model_cells = {}
            for field in chain_fields:
                if not _valid_model_cell_or_formula(model_cells.get(field)):
                    problems.append(
                        f"{label}: model_cells.{field} must be an exact workbook cell or executable formula"
                    )

            applied = row.get("applied_shock_node_ids")
            if not isinstance(applied, list) or any(
                not isinstance(item, str) or _placeholder(item) for item in (applied or [])
            ):
                problems.append(f"{label}: applied_shock_node_ids must be an array of named node ids")
                applied_ids: set[str] = set()
            else:
                applied_ids = {str(item).strip() for item in applied}
            unknown_applied = applied_ids - shock_node_ids
            if unknown_applied:
                problems.append(
                    f"{label}: applied shock node is not declared in scenario shocks: "
                    + ",".join(sorted(unknown_applied))
                )
            chain_period_position = period_positions.get(period)
            required_shock_ids = {
                node_id
                for node_id, shock in shock_by_node_id.items()
                if chain_period_position is not None
                    and (activation := resolve_shock_activation_position(shock, period_positions)) is not None
                    and activation <= chain_period_position
            }
            for missing_shock_id in sorted(required_shock_ids - applied_ids):
                problems.append(
                    f"{label}: shock {missing_shock_id} is not linked to this profit-chain period"
                )
            for premature_shock_id in sorted((applied_ids & shock_node_ids) - required_shock_ids):
                activation = resolve_shock_activation_position(
                    shock_by_node_id[premature_shock_id], period_positions
                )
                if chain_period_position is not None and activation is not None and activation > chain_period_position:
                    problems.append(
                        f"{label}: shock {premature_shock_id} is applied before its effective period and lag"
                    )
            linked_shock_ids |= applied_ids & shock_node_ids

            joint_state_id = str(row.get("joint_state_id") or "").strip()
            if _placeholder(joint_state_id):
                problems.append(f"{label}: joint_state_id is required")
            else:
                scenario_joint_state_ids.add(joint_state_id)

        scenario_rows[scenario_id] = by_period
        row_periods = set(by_period)
        if row_periods != declared_periods:
            missing = sorted(declared_periods - row_periods)
            extra = sorted(row_periods - declared_periods)
            problems.append(
                f"{scenario_id}: period coverage must equal forecast periods; "
                f"missing={missing or []}; extra={extra or []}"
            )
        for shock_node_id in sorted(shock_node_ids - linked_shock_ids):
            problems.append(
                f"{scenario_id}: shock {shock_node_id} is not linked to any profit-chain period"
            )
        if len(scenario_joint_state_ids) > 1:
            problems.append(
                f"{scenario_id}: joint_state_id must remain stable across the scenario profit path"
            )
        for joint_state_id in sorted(scenario_joint_state_ids):
            prior_owner = joint_state_owner.setdefault(joint_state_id, scenario_id)
            if prior_owner != scenario_id:
                problems.append(
                    f"joint_state_id {joint_state_id} is assigned to more than one scenario: "
                    f"{prior_owner},{scenario_id}"
                )

    reference_ids = [
        str(scenario.get("id") or "").strip()
        for scenario in scenarios
        if isinstance(scenario, dict)
        and str(scenario.get("role") or "").strip().lower() == "reference"
        and str(scenario.get("id") or "").strip()
    ]
    reference_id = reference_ids[0] if len(reference_ids) == 1 else ""

    integrated_by_period: dict[str, dict] = {}
    for row in integrated_periods:
        if not isinstance(row, dict):
            continue
        period = str(row.get("period") or "").strip()
        if period and period not in integrated_by_period:
            integrated_by_period[period] = row.get("income_statement") or {}

    output_by_period: dict[str, dict] = {}
    for output in snapshot_outputs.values() if isinstance(snapshot_outputs, dict) else []:
        if not isinstance(output, dict):
            continue
        period = str(output.get("period") or "").strip()
        if period and period not in output_by_period:
            output_by_period[period] = output

    if reference_id:
        for period in sorted(declared_periods):
            reference_row = scenario_rows.get(reference_id, {}).get(period)
            if not reference_row:
                continue
            integrated_income = integrated_by_period.get(period)
            if not isinstance(integrated_income, dict):
                problems.append(
                    f"{reference_id}:{period}: integrated statement period is missing"
                )
            else:
                for field in chain_fields:
                    if not close(reference_row.get(field), integrated_income.get(field)):
                        problems.append(
                            f"{reference_id}:{period}: integrated {field} does not reconcile "
                            "to the reference scenario"
                        )
            output = output_by_period.get(period)
            if not isinstance(output, dict):
                problems.append(
                    f"{reference_id}:{period}: canonical snapshot output period is missing"
                )
                continue
            for chain_field, point_field in point_fields.items():
                if not close(reference_row.get(chain_field), output.get(point_field)):
                    problems.append(
                        f"{reference_id}:{period}: snapshot {point_field} does not reconcile "
                        "to the reference scenario"
                    )
            if not close(
                reference_row.get("net_income_attributable"), output.get("profit_point")
            ):
                problems.append(
                    f"{reference_id}:{period}: snapshot profit_point does not reconcile "
                    "to the reference scenario"
                )

    # Each side of the published interval must be one declared scenario tuple.
    # Matching each field to that same row prevents marginal-interval splicing.
    for period in sorted(declared_periods):
        output = output_by_period.get(period)
        if not isinstance(output, dict):
            continue
        for side in ("low", "high"):
            scenario_field = f"{side}_scenario_id"
            selected_id = str(output.get(scenario_field) or "").strip()
            if not selected_id or selected_id not in scenario_rows:
                problems.append(
                    f"{period}: {scenario_field} must name a declared joint scenario"
                )
                continue
            selected_row = scenario_rows[selected_id].get(period)
            if not selected_row:
                problems.append(
                    f"{period}: joint {side} scenario {selected_id} has no profit-chain row"
                )
                continue
            for chain_field, output_stem in range_fields.items():
                output_field = f"{output_stem}_{side}"
                if not close(selected_row.get(chain_field), output.get(output_field)):
                    problems.append(
                        f"{period}: {output_field} does not reconcile to joint {side} "
                        f"scenario {selected_id}"
                    )
            profit_field = f"profit_{side}"
            if not close(selected_row.get("net_income_attributable"), output.get(profit_field)):
                problems.append(
                    f"{period}: {profit_field} does not reconcile to joint {side} "
                    f"scenario {selected_id}"
                )

        for stem, point_field in (
            ("revenue", "revenue_point"),
            ("operating_profit", "operating_profit_point"),
            ("pretax_profit", "pretax_profit_point"),
            ("net_income", "net_income_point"),
        ):
            low = strict_finite_number(output.get(f"{stem}_low"))
            point = strict_finite_number(output.get(point_field))
            high = strict_finite_number(output.get(f"{stem}_high"))
            if None in (low, point, high) or not (low <= point <= high):
                problems.append(
                    f"{period}: {stem} hierarchy must satisfy low <= point <= high"
                )

    return problems


def validate_recurring_scenario_dimensions(scenarios: list[dict]) -> list[str]:
    """Validate the recurring mechanisms selected for each alternative path.

    Retention, price, usage cost and sales efficiency are useful candidates,
    not a universal four-factor shape.  The analyst selects material shock
    dimensions; this check only makes those selections explicit and unique.
    """

    problems: list[str] = []
    for scenario in scenarios:
        if not isinstance(scenario, dict):
            continue
        scenario_id = str(scenario.get("id") or "").strip()
        if str(scenario.get("role") or "").strip().lower() == "reference":
            continue
        shocks = scenario.get("shocks")
        if not isinstance(shocks, list):
            problems.append(f"{scenario_id or '<blank>'}: shocks must be an array")
            continue
        seen_dimensions: set[str] = set()
        for shock_index, shock in enumerate(shocks, 1):
            if not isinstance(shock, dict):
                continue
            dimension = str(shock.get("dimension") or "").strip().lower()
            if _placeholder(dimension):
                problems.append(
                    f"{scenario_id}:shock-{shock_index}: name the selected recurring economic dimension"
                )
            elif dimension in seen_dimensions:
                problems.append(f"{scenario_id}: duplicate recurring dimension {dimension}")
            seen_dimensions.add(dimension)
    return problems


def fail_record(checks: list[dict], name: str, detail: str, severity: str = "error") -> None:
    checks.append({"check": name, "passed": False, "severity": severity, "detail": detail})


def pass_record(checks: list[dict], name: str, detail: str = "") -> None:
    checks.append({"check": name, "passed": True, "severity": "info", "detail": detail})


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate a full-company forecast delivery workspace.")
    parser.add_argument("--workspace", required=True)
    parser.add_argument("--strict", action="store_true")
    args = parser.parse_args()

    workspace = Path(args.workspace).resolve()
    checks: list[dict] = []
    skill_root = skill_root_from_script(__file__)
    profile = load_profile(skill_root)
    package_registry_profile = str(profile.get("profile") or "").strip() or None
    method_system = json.loads(
        (skill_root / "assets" / "method_system.json").read_text(encoding="utf-8")
    )
    canonical_stage_ids = [
        str(stage.get("id") or "").strip()
        for stage in (method_system.get("stages") or [])
        if isinstance(stage, dict) and str(stage.get("id") or "").strip()
    ]
    if not workspace.exists():
        print(json.dumps({"passed": False, "error": f"workspace missing: {workspace}"}, indent=2))
        return 2

    manifest_path = workspace / "run_manifest.json"
    manifest_preview: dict = {}
    if manifest_path.exists():
        try:
            candidate = json.loads(manifest_path.read_text(encoding="utf-8"))
            if isinstance(candidate, dict):
                manifest_preview = candidate
        except Exception:
            # The canonical manifest parse below reports the detailed error.
            pass
    registry_profile = (
        str(manifest_preview.get("artifact_profile") or "").strip()
        or package_registry_profile
    )
    active_artifact_paths: set[str] = set()
    try:
        artifact_registry = load_registry(skill_root / "assets" / "artifact_registry.json")
        registry_problems = validate_registry(artifact_registry, skill_root=skill_root)
        if registry_problems:
            fail_record(checks, "artifact-registry:valid", "; ".join(registry_problems[:12]))
            active_artifacts: list[dict] = []
        else:
            pass_record(checks, "artifact-registry:valid")
            route_problems = validate_manifest_routes(artifact_registry, manifest_preview)
            if route_problems:
                fail_record(
                    checks,
                    "manifest:artifact-registry-routes",
                    "; ".join(route_problems),
                )
                active_artifacts = []
            else:
                pass_record(checks, "manifest:artifact-registry-routes")
                active_artifacts = resolve_active_artifacts(
                    artifact_registry,
                    manifest_preview,
                    profile=registry_profile,
                )
                active_artifact_paths = {
                    str(item.get("path") or "") for item in active_artifacts
                }
                view_diagnostics = required_artifact_view_diagnostics(
                    artifact_registry,
                    manifest_preview,
                    profile=registry_profile,
                )
                if view_diagnostics:
                    fail_record(
                        checks,
                        "manifest:artifact-registry-generated-view",
                        "; ".join(view_diagnostics),
                        "warning",
                    )
                else:
                    pass_record(checks, "manifest:artifact-registry-generated-view")
        for artifact in active_artifacts:
            if artifact.get("artifact_role") == "receipt":
                continue
            name = str(artifact.get("path") or "")
            path = workspace / name
            if path.exists() and path.stat().st_size > 0:
                pass_record(checks, f"file:{name}")
            else:
                fail_record(checks, f"file:{name}", "missing or empty active artifact")
    except Exception as exc:
        fail_record(checks, "artifact-registry:load", str(exc))

    model_candidates = [workspace / "model" / "model.xlsx", workspace / "model.xlsx"]
    model_path = next((p for p in model_candidates if p.exists()), None)
    workbook_record = None
    if model_path:
        pass_record(checks, "file:model.xlsx", str(model_path))
        try:
            workbook_record = parse_workbook(model_path)
            pass_record(
                checks,
                "workbook:parsed-dependency-surface",
                f"{len(workbook_record.sheets)} sheets; {workbook_record.formula_count} formula cells (diagnostic only)",
            )
        except Exception as exc:
            fail_record(checks, "workbook:parsed-dependency-surface", str(exc))
    else:
        fail_record(checks, "file:model.xlsx", "expected model/model.xlsx or model.xlsx")

    # Manifest
    manifest = {}
    is_v2 = False
    scope_exception_valid = False
    if manifest_path.exists():
        try:
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            declared_contract_version = str(manifest.get("contract_version") or "").strip()
            declared_v2 = bool(re.match(r"^2(?:\.|$)", declared_contract_version))
            if args.strict:
                # Strict delivery is the current v2 contract.  Treating an
                # absent/old declaration as legacy would also re-enable legacy
                # importance weights and skip every v2 artifact gate.
                is_v2 = True
                if not declared_contract_version:
                    fail_record(
                        checks,
                        "manifest:contract-version-v2",
                        "missing contract_version; strict delivery requires major version 2",
                    )
                elif not declared_v2:
                    fail_record(
                        checks,
                        "manifest:contract-version-v2",
                        f"contract_version {declared_contract_version} is not major version 2",
                    )
                else:
                    pass_record(checks, "manifest:contract-version-v2", declared_contract_version)
            else:
                is_v2 = declared_v2
            if is_v2:
                required = [
                    "contract_version", "method_version", "run_id", "entity", "security", "as_of",
                    "purpose", "fiscal_calendar", "currency", "accounting_basis", "horizons",
                    "analysis_primitives", "readiness_target", "phase_status",
                ]
            else:
                required = [
                    "run_id", "entity", "security", "as_of", "purpose", "fiscal_calendar",
                    "currency", "accounting_basis", "horizons", "selected_mechanisms",
                    "readiness_target", "phase_status",
                ]
            missing = [k for k in required if not manifest.get(k)]
            if missing:
                fail_record(checks, "manifest:required-fields", ", ".join(missing))
            else:
                pass_record(checks, "manifest:required-fields")
            forbidden = sorted(V2_FORBIDDEN_FIELDS & set(manifest)) if is_v2 else []
            if forbidden:
                fail_record(
                    checks,
                    "manifest:v2-no-manual-weights",
                    "v2 forbids analyst-assigned importance fields: " + ", ".join(forbidden),
                )
            elif is_v2:
                pass_record(checks, "manifest:v2-no-manual-weights")
            phases = manifest.get("phase_status")
            if not isinstance(phases, dict) or list(phases) != canonical_stage_ids:
                fail_record(
                    checks,
                    "manifest:canonical-stage-registry",
                    "phase_status must use the ordered method_system stage IDs exactly",
                )
            else:
                pass_record(checks, "manifest:canonical-stage-registry")
                invalid_states = [
                    key for key, value in phases.items()
                    if value not in {"pending", "in_progress", "complete", "blocked"}
                ]
                incomplete = [key for key, value in phases.items() if value != "complete"]
                if invalid_states:
                    fail_record(
                        checks,
                        "manifest:phase-state-types",
                        "invalid states: " + ", ".join(invalid_states),
                    )
                else:
                    pass_record(checks, "manifest:phase-state-types")
                if incomplete:
                    fail_record(
                        checks,
                        "manifest:phase-gates",
                        "not complete: " + ", ".join(incomplete),
                        "error" if args.strict else "warning",
                    )
                else:
                    pass_record(checks, "manifest:phase-gates")
            if is_v2 and args.strict:
                requested_scope_exceptions = [
                    field
                    for field in (
                        "driver_tree_relaxed",
                        "outputs_canonical_relaxed",
                    )
                    if _truthy(manifest.get(field))
                ]
                if (
                    str(manifest.get("readiness_target") or "").strip().lower()
                    == "research-grade"
                    and manifest.get("research_completeness_required") is False
                ):
                    requested_scope_exceptions.append("research_completeness_disabled")
                scope_errors = validate_narrow_scope_exception(
                    manifest,
                    requested_exceptions=requested_scope_exceptions,
                )
                scope_exception_valid = bool(requested_scope_exceptions) and not scope_errors
                if scope_errors:
                    fail_record(
                        checks,
                        "manifest:narrow-scope-exception",
                        "; ".join(scope_errors),
                    )
                else:
                    pass_record(
                        checks,
                        "manifest:narrow-scope-exception",
                        "typed narrow audit" if scope_exception_valid else "no waiver requested",
                    )
        except Exception as exc:
            fail_record(checks, "manifest:json", str(exc))

    # Source pack
    source_path = workspace / "source_manifest.json"
    if source_path.exists():
        try:
            src = json.loads(source_path.read_text(encoding="utf-8"))
            sources = src.get("sources", [])
            parse_datetime(src.get("as_of") or manifest.get("as_of"))
            if is_v2:
                required_fields = [
                    "source_id", "source_type", "origin_record_kind", "epistemic_class", "publisher", "published_at", "retrieved_at",
                    "period_scope", "content_hash", "location", "authority", "independence",
                    "directness", "role", "scope_match",
                ]
            else:
                required_fields = [
                    "source_id", "source_type", "publisher", "published_at", "retrieved_at",
                    "period_scope", "evidence_tier", "location", "claim_or_fact", "allowed_use",
                ]
            incomplete_sources = []
            source_class_errors = []
            for s in sources:
                miss = [k for k in required_fields if k not in s or s.get(k) is None or s.get(k) == ""]
                if is_v2:
                    source_class_errors.extend(source_epistemic_class_problems(s))
                    scope = s.get("scope_match")
                    if not isinstance(scope, dict) or any(
                        key not in scope or not isinstance(scope.get(key), bool)
                        for key in ("entity", "product", "geography", "period", "unit")
                    ):
                        miss.append("scope_match.*")
                if miss:
                    incomplete_sources.append(f"{s.get('source_id','UNKNOWN')}:{'/'.join(miss)}")
                try:
                    parse_datetime(s["published_at"])
                    parse_datetime(s["retrieved_at"])
                except Exception:
                    incomplete_sources.append(f"{s.get('source_id','UNKNOWN')}:invalid-date")
            if incomplete_sources:
                fail_record(checks, "sources:required-fields", "; ".join(incomplete_sources[:10]))
            else:
                pass_record(checks, "sources:required-fields")
            if source_class_errors:
                fail_record(
                    checks,
                    "sources:epistemic-class",
                    "; ".join(source_class_errors[:10]),
                )
            elif is_v2:
                pass_record(checks, "sources:epistemic-class")
            pass_record(checks, "sources:date-integrity")
        except Exception as exc:
            fail_record(checks, "sources:json", str(exc))

    # Forward-evidence workspace validator
    forward_validator = Path(__file__).resolve().parent / "validate_forward_evidence_workspace.py"
    if manifest.get("forward_evidence_required", True):
        result = subprocess.run([sys.executable, str(forward_validator), "--workspace", str(workspace), "--strict"], capture_output=True, text=True)
        if result.returncode == 0:
            pass_record(checks, "forward-evidence:workspace", result.stdout.strip())
        else:
            fail_record(checks, "forward-evidence:workspace", (result.stdout + result.stderr).strip())

    # Research-depth and gold-standard parity validator
    research_validator = Path(__file__).resolve().parent / "validate_research_completeness.py"
    if manifest.get("research_completeness_required", True):
        result = subprocess.run([sys.executable, str(research_validator), "--workspace", str(workspace), "--strict"], capture_output=True, text=True)
        if result.returncode == 0:
            pass_record(checks, "research-completeness:workspace", result.stdout.strip())
        else:
            fail_record(checks, "research-completeness:workspace", (result.stdout + result.stderr).strip())

    # Parse the authored scenario surface once.  Every downstream view binds to
    # this catalog; no validator gets to reconstruct IDs, roles, or probability
    # semantics independently.
    scenario_path = workspace / "scenario_set.json"
    scenario_obj: dict = {}
    scenarios: list[dict] = []
    scenario_catalog = None
    scenario_catalog_problems: list[str] = []
    if is_v2:
        if not scenario_path.exists():
            scenario_catalog_problems.append("missing scenario_set.json")
        else:
            try:
                loaded_scenario_obj = json.loads(
                    scenario_path.read_text(encoding="utf-8")
                )
                if isinstance(loaded_scenario_obj, dict):
                    scenario_obj = loaded_scenario_obj
                scenario_rows = scenario_obj.get("scenarios")
                if isinstance(scenario_rows, list):
                    scenarios = scenario_rows
                scenario_catalog, scenario_catalog_problems = (
                    parse_scenario_catalog(loaded_scenario_obj)
                )
            except Exception as exc:
                scenario_catalog_problems.append(f"invalid scenario_set.json: {exc}")
        if scenario_catalog_problems:
            fail_record(
                checks,
                "scenarios:catalog",
                "; ".join(scenario_catalog_problems[:12]),
            )
        else:
            pass_record(
                checks,
                "scenarios:catalog",
                f"{len(scenario_catalog.ids)} authored scenario(s)",
            )

    # Assumption register
    assumption_path = workspace / "assumption_register.csv"
    if assumption_path.exists():
        try:
            with assumption_path.open(encoding="utf-8-sig", newline="") as f:
                reader = csv.DictReader(f)
                fields = set(reader.fieldnames or [])
                if is_v2:
                    required = {
                        "assumption_id", "node_id", "entity", "segment", "primitive", "metric",
                        "period", "frequency", "scenario", "value", "unit", "input_type",
                        "source_ids", "claim_ids", "confidence", "applies_to",
                        "does_not_apply_to", "test_delta", "falsification_id", "next_evidence",
                        "owner", "notes",
                    }
                else:
                    required = {
                        "assumption_id", "entity", "segment", "mechanism", "metric", "period",
                        "scenario", "value", "unit", "evidence_tier", "source_ids", "confidence",
                        "breakpoint", "next_evidence", "owner",
                    }
                missing = sorted(required-fields)
                if missing:
                    fail_record(checks, "assumptions:headers", ", ".join(missing))
                else:
                    pass_record(checks, "assumptions:headers")
                rows = list(reader)
                if rows:
                    pass_record(checks, "assumptions:rows", str(len(rows)))
                    if is_v2 and scenario_catalog is not None:
                        binding_problems = validate_assumption_scenario_bindings(
                            rows, scenario_catalog
                        )
                        if binding_problems:
                            fail_record(
                                checks,
                                "assumptions:scenario-bindings",
                                "; ".join(binding_problems[:12]),
                            )
                        else:
                            pass_record(checks, "assumptions:scenario-bindings")
                else:
                    fail_record(checks, "assumptions:rows", "no assumptions recorded", "error" if args.strict else "warning")
        except Exception as exc:
            fail_record(checks, "assumptions:csv", str(exc))

    # Narrative quality is judged from frozen artifacts by an independent
    # reviewer.  A word count or a phrase checklist is not evidence that the
    # report understood the business.
    report_path = workspace / "report.md"
    if report_path.exists():
        text = report_path.read_text(encoding="utf-8")
        if text.strip():
            pass_record(checks, "report:present-for-independent-review")
        else:
            fail_record(checks, "report:present-for-independent-review", "empty report")

    # The red-team artifact is also assessed independently.  Deterministic
    # validation below only enforces unresolved material findings; it does not
    # reward a finding count or the presence of fashionable keywords.
    red_path = workspace / "red_team.md"
    if red_path.exists():
        text = red_path.read_text(encoding="utf-8")
        if text.strip():
            pass_record(checks, "red-team:present-for-independent-review")
        else:
            fail_record(checks, "red-team:present-for-independent-review", "empty red-team artifact")

    # Snapshot
    snap_path = workspace / "forecast_snapshot.json"
    snap: dict = {}
    if snap_path.exists():
        try:
            snap = json.loads(snap_path.read_text(encoding="utf-8"))
            if is_v2:
                required = [
                    "forecast_contract_version", "schema_version", "forecast_id", "as_of",
                    "model_version", "accounting_basis_id", "source_pack_hash", "scenario_probabilities", "outputs",
                    "investment_case", "driver_tree", "integrated_model", "value_creation",
                    "valuation", "market_implied_expectations", "valuation_summary", "monitoring",
                    "breakpoints", "human_required", "confidence_and_limits",
                ]
            else:
                required = [
                    "forecast_id", "as_of", "model_version", "source_pack_hash",
                    "mechanism_weights", "scenario_probabilities", "outputs", "breakpoints",
                    "human_required", "confidence_and_limits",
                ]
            missing = [k for k in required if k not in snap]
            if missing:
                fail_record(checks, "snapshot:fields", ", ".join(missing))
            else:
                pass_record(checks, "snapshot:fields")
            forbidden = sorted(V2_FORBIDDEN_FIELDS & set(snap)) if is_v2 else []
            if forbidden:
                fail_record(
                    checks,
                    "snapshot:v2-no-manual-weights",
                    "v2 forbids analyst-assigned importance fields: " + ", ".join(forbidden),
                )
            elif is_v2:
                pass_record(checks, "snapshot:v2-no-manual-weights")
            def _num(value):
                return isinstance(value, (int, float)) and not isinstance(value, bool)

            # Driver tree replaces mechanism weights (weights = factor-scoring
            # smell; a model is one arithmetic tree, see driver-tree-modeling.md).
            tree = snap.get("driver_tree") or {}
            segments = tree.get("segments") if isinstance(tree, dict) else None
            relaxed_tree = bool(manifest.get("driver_tree_relaxed", False))
            if isinstance(segments, list) and segments:
                seg_errors = []
                if not (tree.get("main_line_id") or tree.get("main_line") or any(s.get("main_line") for s in segments)):
                    seg_errors.append("main line (主线) not declared")
                for seg in segments:
                    if not seg.get("name"):
                        seg_errors.append("segment missing name")
                    if _placeholder(seg.get("basis")):
                        seg_errors.append(
                            f"segment {seg.get('name')}: name the case-selected causal decomposition"
                        )
                    if not _json_number(seg.get("revenue_point")):
                        seg_errors.append(f"segment {seg.get('name')}: revenue_point must be numeric")
                # Name the material drivers that carry the call.  Focus is a
                # research judgment, not a universal maximum-list-size rule.
                carriers = tree.get("thesis_carriers")
                if not _named_list(carriers):
                    seg_errors.append(
                        "driver_tree.thesis_carriers missing: name the material driver quantities whose variation carries the call"
                    )
                y1_rev = ((snap.get("outputs") or {}).get("year_1") or {}).get("revenue_point")
                seg_errors.extend(
                    validate_driver_tree_partitions(
                        tree,
                        consolidated_revenue=y1_rev,
                    )
                )
                if seg_errors:
                    fail_record(checks, "snapshot:driver-tree", "; ".join(seg_errors))
                else:
                    pass_record(checks, "snapshot:driver-tree")
            elif relaxed_tree:
                pass_record(checks, "snapshot:driver-tree")
            else:
                fail_record(checks, "snapshot:driver-tree",
                            "driver_tree.segments required: revenue must decompose into segment leaves "
                            "(volume x price / capacity ramp / subscriber economics...), with the main line declared - "
                            "see references/driver-tree-modeling.md",
                            "error" if args.strict else "warning")
            probs = snap.get("scenario_probabilities", {})
            if is_v2:
                if scenario_catalog is None:
                    fail_record(
                        checks,
                        "snapshot:scenario-probabilities",
                        "cannot validate probabilities because scenario_set catalog is invalid",
                    )
                else:
                    probability_problems = validate_probability_view(
                        probs,
                        scenario_catalog,
                        label="forecast_snapshot.scenario_probabilities",
                    )
                    if probability_problems:
                        fail_record(
                            checks,
                            "snapshot:scenario-probabilities",
                            "; ".join(probability_problems[:12]),
                        )
                    else:
                        pass_record(checks, "snapshot:scenario-probabilities")
            elif probs and abs(sum(float(v) for v in probs.values())-1.0) <= 0.0001:
                pass_record(checks, "snapshot:scenario-probabilities")
            else:
                fail_record(checks, "snapshot:scenario-probabilities", "probabilities must sum to 1")

            if is_v2:
                if scenario_catalog is None:
                    fail_record(
                        checks,
                        "snapshot:valuation-summary",
                        "cannot validate valuation_summary because scenario_set catalog is invalid",
                    )
                else:
                    valuation_summary_problems = validate_valuation_summary(
                        snap.get("valuation_summary"),
                        snap.get("valuation"),
                        scenario_catalog,
                    )
                    if valuation_summary_problems:
                        fail_record(
                            checks,
                            "snapshot:valuation-summary",
                            "; ".join(valuation_summary_problems[:12]),
                        )
                    else:
                        pass_record(checks, "snapshot:valuation-summary")
            # Canonical outputs contract: every horizon must use canonical keys.
            # Dialect keys (revenue_M / revenue_base / revenue_p50 / nested scenario
            # dicts / non_gaap_eps_*) are a delivery failure - downstream consumers
            # (dashboard, scorer, exports) read canonical keys only.
            relaxed_outputs = bool(manifest.get("outputs_canonical_relaxed", False))
            outputs = snap.get("outputs") or {}
            for period_key, needs_range in (("year_1", False), ("year_2", True), ("year_3_distribution", True)):
                out = outputs.get(period_key)
                label = f"snapshot:canonical-{period_key}"
                output_problems = validate_canonical_output_period(
                    out,
                    needs_range=needs_range,
                    strict_full_company=args.strict,
                )
                has_numbers = isinstance(out, dict) and any(
                    _json_number(value)
                    or (isinstance(value, dict) and any(_json_number(x) for x in value.values()))
                    for key, value in out.items() if key not in ("period", "point_evaluable")
                )
                if not output_problems:
                    pass_record(checks, label)
                elif has_numbers or args.strict:
                    fail_record(checks, label,
                                "; ".join(output_problems) + "; strict full-company canonical keys are "
                                "period, revenue_point, operating_profit_point, pretax_profit_point, "
                                "tax_expense_point and profit_point (GAAP net income); year_2/year_3 also "
                                "require revenue/profit low and high")
                elif relaxed_outputs and not args.strict:
                    pass_record(checks, label)
                else:
                    fail_record(checks, label, "outputs not populated with canonical keys", "error" if args.strict else "warning")
        except Exception as exc:
            fail_record(checks, "snapshot:json", str(exc))

    # V2 causal/value contracts.  The spreadsheet remains the presentation and
    # calculation surface; these small machine-readable artifacts make its
    # logic, evidence lineage and accounting identities independently auditable.
    if is_v2:
        scripts_dir = Path(__file__).resolve().parent
        graph_path = workspace / "model_graph.json"
        graph_obj: dict = {}
        graph_nodes: dict[str, dict] = {}
        main_line_carriers: set[str] = set()
        main_line_relevant_nodes: set[str] = set()
        main_line_falsifications: set[str] = set()
        main_line_competitor_nodes: set[str] = set()
        if graph_path.exists():
            try:
                graph_obj = json.loads(graph_path.read_text(encoding="utf-8"))
                graph_nodes = {
                    str(node.get("id")): node
                    for node in graph_obj.get("nodes", [])
                    if isinstance(node, dict) and node.get("id")
                }
                main_line = graph_obj.get("main_line") or {}
                main_line_carriers = {str(item) for item in main_line.get("carrier_node_ids", [])}
                main_line_relevant_nodes = _causal_upstream_nodes(
                    graph_obj, main_line_carriers
                )
                main_line_falsifications = {str(item) for item in main_line.get("falsification_ids", [])}
                main_line_competitor_nodes = {
                    str(item)
                    for item in main_line.get("competitor_response_node_ids", [])
                    if str(item).strip()
                }
            except Exception as exc:
                fail_record(checks, "model-graph:json", str(exc))

        if graph_path.exists():
            command = [sys.executable, str(scripts_dir / "validate_model_graph.py"), "--graph", str(graph_path)]
            if args.strict:
                command.append("--strict")
            result = subprocess.run(command, capture_output=True, text=True)
            if result.returncode == 0:
                pass_record(checks, "model-graph:contract", result.stdout.strip())
            else:
                fail_record(checks, "model-graph:contract", (result.stdout + result.stderr).strip())

        if snap_path.exists():
            command = [sys.executable, str(scripts_dir / "validate_investment_case.py"), "--snapshot", str(snap_path)]
            if args.strict:
                command.append("--strict")
            result = subprocess.run(command, capture_output=True, text=True)
            if result.returncode == 0:
                pass_record(checks, "investment-case:contract", result.stdout.strip())
            else:
                fail_record(checks, "investment-case:contract", (result.stdout + result.stderr).strip())

        source_ids: set[str] = set()
        independent_source_ids: set[str] = set()
        source_records: list[dict] = []
        source_records_by_id: dict[str, dict] = {}
        if source_path.exists():
            try:
                source_records = [
                    item
                    for item in json.loads(source_path.read_text(encoding="utf-8")).get("sources", [])
                    if isinstance(item, dict) and item.get("source_id")
                ]
                source_ids = {str(item.get("source_id")) for item in source_records}
                source_records_by_id = {
                    str(item.get("source_id")): item for item in source_records
                }
                independent_source_ids = {
                    str(item.get("source_id"))
                    for item in source_records
                    if _independent_source(item)
                }
            except Exception:
                source_ids = set()
                independent_source_ids = set()
                source_records = []
                source_records_by_id = {}

        data_register_path = workspace / "data_series_register.csv"
        fact_ledger_path = workspace / "financial_fact_ledger.csv"
        accounting_fact_rows: list[dict[str, str]] = []
        if fact_ledger_path.exists():
            try:
                with fact_ledger_path.open(encoding="utf-8-sig", newline="") as handle:
                    accounting_fact_rows = list(csv.DictReader(handle))
            except Exception as exc:
                fail_record(checks, "manifest:accounting-basis", f"cannot read financial facts: {exc}")
        accounting_problems = validate_accounting_basis_contract(
            manifest,
            snapshot=snap,
            financial_fact_rows=accounting_fact_rows,
            source_ids=source_ids,
        )
        if accounting_problems:
            fail_record(
                checks,
                "manifest:accounting-basis",
                "; ".join(accounting_problems[:12]),
            )
        else:
            pass_record(checks, "manifest:accounting-basis")
        registered_series_ids: set[str] = set()
        observation_records_by_id: dict[str, dict[str, str]] = {}
        if data_register_path.exists():
            try:
                with data_register_path.open(encoding="utf-8-sig", newline="") as handle:
                    observation_rows = list(csv.DictReader(handle))
                observation_records_by_id = {
                    str(row.get("series_id") or "").strip(): row
                    for row in observation_rows
                    if str(row.get("series_id") or "").strip()
                }
                registered_series_ids = set(observation_records_by_id)
            except Exception:
                registered_series_ids = set()
                observation_records_by_id = {}
        if data_register_path.exists() and fact_ledger_path.exists() and source_path.exists() and graph_path.exists():
            command = [
                sys.executable,
                str(scripts_dir / "validate_data_series.py"),
                "--register", str(data_register_path),
                "--sources", str(source_path),
                "--graph", str(graph_path),
                "--facts", str(fact_ledger_path),
                "--manifest", str(manifest_path),
                "--independence-map", str(workspace / "source_independence_map.csv"),
            ]
            if args.strict:
                command.append("--strict")
            result = subprocess.run(command, capture_output=True, text=True)
            if result.returncode == 0:
                pass_record(checks, "data-series:lineage-vintage", result.stdout.strip())
            else:
                fail_record(checks, "data-series:lineage-vintage", (result.stdout + result.stderr).strip())

        claim_path = workspace / "claim_ledger.jsonl"
        if claim_path.exists():
            claim_problems: list[str] = []
            claims: list[dict] = []
            try:
                for line_no, raw in enumerate(claim_path.read_text(encoding="utf-8").splitlines(), 1):
                    if not raw.strip():
                        continue
                    try:
                        claim = json.loads(raw)
                    except Exception as exc:
                        claim_problems.append(f"line {line_no}: invalid JSON ({exc})")
                        continue
                    if not isinstance(claim, dict):
                        claim_problems.append(f"line {line_no}: claim must be an object")
                        continue
                    claims.append(claim)
                authority_judgments, _review_binding_problems = (
                    load_frozen_claim_authority_judgments(workspace, claim_path)
                )
                # A stale review returns no permissions. The research
                # validator reports the hash/independence defect, while any
                # affected Base claim fails here for lacking frozen permission.
                claim_problems.extend(
                    validate_claim_records(
                        claims,
                        source_records=source_records_by_id,
                        graph_node_ids=set(graph_nodes),
                        main_line_carriers=main_line_carriers,
                        authority_judgments=authority_judgments,
                        observation_records=observation_records_by_id,
                    )
                )
            except Exception as exc:
                claim_problems.append(str(exc))
            if claim_problems:
                fail_record(checks, "claims:ledger", "; ".join(claim_problems[:8]))
            else:
                pass_record(checks, "claims:ledger", f"{len(claims)} claims")

        scenario_ids: set[str] = (
            set(scenario_catalog.ids) if scenario_catalog is not None else set()
        )
        if scenario_path.exists():
            scenario_problems: list[str] = list(scenario_catalog_problems)
            try:
                presence_problems = validate_scenario_collection_presence(scenarios)
                if presence_problems:
                    scenario_problems.extend(presence_problems)
                    scenarios = []
                for scenario in scenarios:
                    if not isinstance(scenario, dict):
                        continue
                    scenario_id = str(scenario.get("id") or "").strip()
                    shocks = scenario.get("shocks")
                    if not isinstance(shocks, list):
                        scenario_problems.append(f"{scenario_id}: shocks must be an array")
                        shocks = []
                    for shock in shocks:
                        if not isinstance(shock, dict):
                            scenario_problems.append(f"{scenario_id}: shock must be an object")
                            continue
                        node_id = str(shock.get("node_id") or "").strip()
                        node = graph_nodes.get(node_id)
                        if not node:
                            scenario_problems.append(f"{scenario_id}: shock references unknown node {node_id or '<blank>'}")
                        elif node.get("kind") not in {"input", "assumption", "state", "observable", "competitor_response"}:
                            scenario_problems.append(f"{scenario_id}: cannot shock derived/output node {node_id}")
                        if shock.get("value") is None or not str(shock.get("operation") or "").strip():
                            scenario_problems.append(f"{scenario_id}:{node_id}: operation and value are required")
                forecast_periods = {
                    str(output.get("period") or "").strip()
                    for output in ((snap.get("outputs") or {}).values())
                    if isinstance(output, dict) and not _placeholder(output.get("period"))
                }
                forecast_periods.update(
                    str(period_row.get("period") or "").strip()
                    for period_row in ((snap.get("integrated_model") or {}).get("periods") or [])
                    if isinstance(period_row, dict) and not _placeholder(period_row.get("period"))
                )
                scenario_problems.extend(validate_scenario_shocks(
                    scenarios,
                    graph_nodes=graph_nodes,
                    forecast_periods=forecast_periods,
                ))
                scenario_problems.extend(validate_scenario_profit_chains(
                    scenarios,
                    forecast_periods=forecast_periods,
                    snapshot_outputs=(snap.get("outputs") or {}),
                    integrated_periods=(
                        (snap.get("integrated_model") or {}).get("periods") or []
                    ),
                ))
                if workbook_record is not None:
                    scenario_problems.extend(
                        validate_scenario_workbook_bindings(workbook_record, scenarios)
                    )
                primitive_names = {
                    str(item).strip().lower().replace("_", "-")
                    for item in (manifest.get("analysis_primitives") or [])
                }
                if primitive_names & {"recurring-contract", "platform-usage"}:
                    scenario_problems.extend(validate_recurring_scenario_dimensions(scenarios))
            except Exception as exc:
                scenario_problems.append(str(exc))
            if scenario_problems:
                fail_record(checks, "scenarios:named-node-shocks", "; ".join(scenario_problems[:10]))
            else:
                pass_record(checks, "scenarios:named-node-shocks")

        internal_intangible_path = workspace / "internal_intangible_investment.json"
        if (
            "internal_intangible_investment.json" in active_artifact_paths
            and internal_intangible_path.exists()
        ):
            internal_intangible_problems: list[str] = []
            try:
                internal_intangible_payload = json.loads(
                    internal_intangible_path.read_text(encoding="utf-8")
                )
                internal_intangible_problems.extend(
                    validate_internal_intangible_schedule(
                        internal_intangible_payload,
                        known_source_ids=source_ids,
                        known_node_ids=set(graph_nodes),
                        scenario_ids=scenario_ids,
                        accounting_basis_id=str(
                            (manifest.get("accounting_basis") or {}).get(
                                "forecast_basis_id", ""
                            )
                        ),
                        readiness=str(manifest.get("readiness_target") or ""),
                        strict=args.strict,
                    )
                )
            except Exception as exc:
                internal_intangible_problems.append(str(exc))
            if internal_intangible_problems:
                fail_record(
                    checks,
                    "internal-intangibles:investment-cohorts",
                    "; ".join(internal_intangible_problems[:12]),
                )
            else:
                pass_record(checks, "internal-intangibles:investment-cohorts")

        persistence_problems = validate_persistence_analysis(
            snap.get("persistence_analysis") if isinstance(snap, dict) else None,
            known_node_ids=set(graph_nodes),
            main_line_relevant_node_ids=(
                main_line_relevant_nodes | main_line_carriers | main_line_competitor_nodes
            ),
            falsification_node_ids=main_line_falsifications,
            known_source_ids=source_ids,
            independent_source_ids=independent_source_ids,
            scenario_ids=scenario_ids,
            strict=args.strict,
        )
        if persistence_problems:
            fail_record(
                checks,
                "persistence:mean-reversion-cost-behavior",
                "; ".join(persistence_problems[:12]),
            )
        else:
            pass_record(checks, "persistence:mean-reversion-cost-behavior")

        checks_path = workspace / "model_checks.json"
        if checks_path.exists():
            model_check_problems: list[str] = []
            try:
                check_rows = json.loads(checks_path.read_text(encoding="utf-8")).get("checks")
                if not isinstance(check_rows, list) or not check_rows:
                    model_check_problems.append("no executable model checks")
                    check_rows = []
                for row in check_rows:
                    check_id = str(row.get("id") or "").strip()
                    value = row.get("value")
                    tolerance = row.get("tolerance")
                    status = str(row.get("status") or "").strip().lower()
                    if check_id.upper() in {"", "REPLACE", "TBD"}:
                        model_check_problems.append("placeholder check id")
                    if not isinstance(value, (int, float)) or isinstance(value, bool):
                        model_check_problems.append(f"{check_id}: check value must be computed")
                    if not isinstance(tolerance, (int, float)) or isinstance(tolerance, bool):
                        model_check_problems.append(f"{check_id}: tolerance must be numeric")
                    if status not in {"pass", "passed", "ok"}:
                        model_check_problems.append(f"{check_id}: status is {status or 'blank'}, not passed")
                if workbook_record is None:
                    model_check_problems.append(
                        "model checks require the bound workbook so residuals can be recomputed"
                    )
                else:
                    model_check_problems.extend(
                        validate_model_check_bindings(workbook_record, check_rows)
                    )
            except Exception as exc:
                model_check_problems.append(str(exc))
            if model_check_problems:
                fail_record(checks, "model-checks:executed", "; ".join(model_check_problems[:8]))
            else:
                pass_record(checks, "model-checks:executed")

        monitoring_path = workspace / "driver_monitoring.csv"
        if monitoring_path.exists():
            try:
                with monitoring_path.open(encoding="utf-8-sig", newline="") as handle:
                    rows = list(csv.DictReader(handle))
                material_technology_node_ids: set[str] = set()
                technology_path = workspace / "technology_commercialization_register.csv"
                if (
                    "technology_commercialization_register.csv" in active_artifact_paths
                    and technology_path.exists()
                ):
                    with technology_path.open(encoding="utf-8-sig", newline="") as handle:
                        technology_rows = list(csv.DictReader(handle))
                    for technology_row in technology_rows:
                        if str(technology_row.get("materiality") or "").strip().lower() not in {"critical", "high"}:
                            continue
                        if str(technology_row.get("current_stage") or "").strip().lower() in {"", "tbd", "pending", "unknown"}:
                            continue
                        material_technology_node_ids |= _split_ids(technology_row.get("driver_node_ids"))
                monitoring_problems, active_rows = validate_monitor_rows(
                    rows,
                    graph_nodes=graph_nodes,
                    main_line_carriers=main_line_carriers,
                    main_line_falsifications=main_line_falsifications,
                    source_ids=source_ids,
                    material_technology_node_ids=material_technology_node_ids,
                )
            except Exception as exc:
                monitoring_problems, active_rows = [str(exc)], []
            if monitoring_problems:
                fail_record(checks, "monitoring:driver-contract", "; ".join(monitoring_problems[:10]))
            else:
                pass_record(checks, "monitoring:driver-contract", f"{len(active_rows)} monitored nodes")

        earnings_path = workspace / "earnings_power_bridge.csv"
        if earnings_path.exists():
            try:
                with earnings_path.open(encoding="utf-8-sig", newline="") as handle:
                    earnings_rows = list(csv.DictReader(handle))
                earnings_problems = validate_earnings_power_rows(
                    earnings_rows,
                    source_ids=source_ids,
                    graph_node_ids=set(graph_nodes),
                    snapshot=snap,
                    readiness_target=str(manifest.get("readiness_target") or ""),
                    material_profit_impact_pct=manifest.get("material_profit_impact_pct"),
                )
            except Exception as exc:
                earnings_problems, earnings_rows = [str(exc)], []
            if earnings_problems:
                fail_record(checks, "earnings-power:bridge", "; ".join(earnings_problems[:10]))
            else:
                pass_record(checks, "earnings-power:bridge", f"{len(earnings_rows)} rows")

        product_customer_path = workspace / "product_customer_driver_schedule.csv"
        if (
            "product_customer_driver_schedule.csv" in active_artifact_paths
            and product_customer_path.exists()
        ):
            try:
                with product_customer_path.open(encoding="utf-8-sig", newline="") as handle:
                    product_customer_rows = list(csv.DictReader(handle))
                product_customer_problems = validate_product_customer_driver_rows(
                    product_customer_rows
                )
            except Exception as exc:
                product_customer_problems, product_customer_rows = [str(exc)], []
            if product_customer_problems:
                fail_record(
                    checks,
                    "tables:product-customer-driver",
                    "; ".join(product_customer_problems[:10]),
                )
            else:
                pass_record(
                    checks,
                    "tables:product-customer-driver",
                    f"{len(product_customer_rows)} rows",
                )

        table_specs = {
            "industry-profit-pool": (
                "industry_profit_pool.csv", "boundary_id", validate_industry_profit_pool_rows
            ),
            "operating-cycle": (
                "operating_cycle_register.csv", "branch_id", validate_operating_cycle_rows
            ),
            "historical-segment-bridge": (
                "historical_segment_bridge.csv", "period", validate_historical_segment_bridge_rows
            ),
        }
        profit_pool_rows: list[dict[str, str]] = []
        for check_name, (file_name, identity_field, row_validator) in table_specs.items():
            path = workspace / file_name
            if file_name not in active_artifact_paths or not path.exists():
                continue
            problems: list[str] = []
            rows: list[dict[str, str]] = []
            try:
                with path.open(encoding="utf-8-sig", newline="") as handle:
                    rows = [
                        row for row in csv.DictReader(handle)
                        if str(row.get(identity_field) or "").strip().upper() not in {"", "TBD"}
                    ]
                for row in rows:
                    identity = str(row.get(identity_field) or "UNKNOWN")
                    if str(row.get("status") or "").strip().lower() in {"", "pending", "tbd"}:
                        problems.append(f"{identity}: status is pending")
                    if not str(row.get("source_ids") or "").strip():
                        problems.append(f"{identity}: source_ids missing")
                    if not str(row.get("driver_node_ids") or "").strip() and file_name != "historical_segment_bridge.csv":
                        problems.append(f"{identity}: driver_node_ids missing")
                if file_name == "historical_segment_bridge.csv" and len({row.get("period") for row in rows}) < 3:
                    problems.append("historical bridge must cover at least three distinct periods")
                if file_name == "industry_profit_pool.csv":
                    profit_pool_rows = rows
                if row_validator is not None:
                    if file_name == "operating_cycle_register.csv":
                        problems.extend(validate_operating_cycle_rows(
                            rows,
                            strict=args.strict,
                            readiness_target=str(manifest.get("readiness_target") or ""),
                            manifest_entity=str(manifest.get("entity") or ""),
                            source_ids=source_ids,
                            data_series_ids=registered_series_ids,
                            graph_node_ids=set(graph_nodes),
                            main_line_carriers=main_line_carriers,
                            main_line_relevant_nodes=main_line_relevant_nodes,
                            profit_pool_rows=profit_pool_rows,
                        ))
                    elif file_name == "historical_segment_bridge.csv":
                        problems.extend(validate_historical_segment_bridge_rows(
                            rows,
                            strict=args.strict,
                            readiness_target=str(manifest.get("readiness_target") or ""),
                            graph_node_ids=set(graph_nodes),
                        ))
                    else:
                        problems.extend(row_validator(rows))
            except Exception as exc:
                problems.append(str(exc))
            if problems:
                fail_record(checks, f"tables:{check_name}", "; ".join(problems[:8]))
            else:
                pass_record(checks, f"tables:{check_name}", f"{len(rows)} rows")

    # Workbook shape and formula counts are diagnostics, not objectives.  The
    # scenario validator above binds every published profit layer to a real
    # formula cell; the structured model_checks artifact owns reconciliations.
    if workbook_record is not None:
        broken = (
            workbook_record.cached_errors["#REF!"]
            + workbook_record.cached_errors["#NAME?"]
        )
        if broken:
            fail_record(checks, "workbook:broken-references", f"#REF!/#NAME? cached errors: {broken}")
        else:
            pass_record(checks, "workbook:broken-references")
        soft = (
            workbook_record.cached_errors["#DIV/0!"]
            + workbook_record.cached_errors["#VALUE!"]
        )
        if soft:
            fail_record(checks, "workbook:error-values", f"#DIV/0!/#VALUE! cached errors: {soft}", "warning")
        else:
            pass_record(checks, "workbook:error-values")

    # Red-team findings must bind the numbers: open P0/P1 findings are only
    # acceptable when the run's readiness target is capped at screen-grade.
    if red_path.exists():
        open_p1 = []
        for line in red_path.read_text(encoding="utf-8").splitlines():
            if not line.strip().startswith("|") or "RT-" not in line:
                continue
            cells = [c.strip() for c in line.strip().strip("|").split("|")]
            if len(cells) < 3:
                continue
            severity = next((c.upper() for c in cells if c.upper() in {"P0", "P1"}), None)
            status = cells[-1].lower()
            if severity and status not in {"closed", "resolved", "mitigated"}:
                open_p1.append(cells[0])
        if open_p1:
            readiness = str(manifest.get("readiness_target", "")).lower()
            if readiness in {"screen-grade", "not-decision-ready"}:
                pass_record(checks, "red-team:open-findings-capped", ",".join(open_p1))
            else:
                fail_record(checks, "red-team:open-findings-bind",
                            f"open P0/P1 findings {','.join(open_p1)} require resolution or readiness_target capped at screen-grade (current: {readiness or 'unset'})",
                            "error" if args.strict else "warning")

    # Forecast diagnostics remain separate views, never a scalar objective.
    if snap_path.exists():
        try:
            snap_acc = json.loads(snap_path.read_text(encoding="utf-8"))
        except Exception:
            snap_acc = {}
        # (a) Symmetric growth challengers.  The four-case historical error
        # sample is a diagnostic, not an interval floor or a one-way optimism
        # rule.  Each relevant baseline receives a named status; every material
        # acceleration or deceleration must reconcile through named driver
        # nodes and named operating states.
        growth_problems = validate_growth_challenger_review(
            snap_acc.get("growth_challenger_review")
        )
        if growth_problems:
            fail_record(
                checks,
                "accuracy:growth-challengers",
                "; ".join(growth_problems[:10]),
                "error" if args.strict else "warning",
            )
        else:
            pass_record(checks, "accuracy:growth-challengers")

        # (b) Error budget: say in advance where the forecast will be wrong.
        budget = snap_acc.get("error_budget")
        if isinstance(budget, dict) and budget:
            missing_b = [h for h in ("year_1", "year_2", "year_3_distribution")
                         if not isinstance(budget.get(h), dict)]
            if missing_b:
                fail_record(checks, "accuracy:error-budget", "missing horizons: " + ", ".join(missing_b),
                            "error" if args.strict else "warning")
            else:
                pass_record(checks, "accuracy:error-budget")
        else:
            fail_record(checks, "accuracy:error-budget",
                        "snapshot.error_budget missing - state per horizon the expected revenue error and the "
                        "expected margin-error contribution, and which dominates",
                        "error" if args.strict else "warning")

    # Search lanes are a discovery diagnostic, not a readiness quota.  The
    # research-completeness validator owns causal lineage and frozen independent
    # judgment; do not duplicate it here with source/lane counts.
    RESEARCH_LANES = {
        "L1_filings": ["10-k", "10-q", "8-k", "annual report", "prospectus", "sec edgar", "sec.gov",
                       "filing", "earnings release", "press release", "年报", "招股"],
        "L2_management": ["earnings call", "transcript", "investor day", "analyst day", "keynote",
                          "fireside", "interview", "ceo", "cfo", "guidance call", "conference presentation",
                          "业绩说明会", "投资者交流", "调研纪要", "管理层"],
        "L3_cross_company": ["supplier", "customer", "competitor", "partner", "value chain",
                             "cross-company", "同行", "客户", "供应商"],
        "L4_industry_data": ["trendforce", "idc", "gartner", "counterpoint", "yole", "techinsights",
                             "omdia", "semi.org", "market research", "shipment data", "行业数据"],
        "L5_sellside": ["research report", "broker", "sell-side", "analyst note", "initiation",
                        "morgan", "goldman", "jefferies", "bernstein", "研报", "券商"],
        "L6_expert_channel": ["expert", "channel check", "supply chain check", "tegus", "gerson",
                              "distributor", "dealer check", "专家", "产业链调研", "渠道调研"],
        "L7_technical": ["arxiv", "ieee", "isscc", "iedm", "jedec", "patent", "paper", "standard",
                         "ofc", "vlsi", "hot chips", "roadmap", "论文", "专利", "标准"],
        "L8_press": ["news", "article", "reuters", "bloomberg", "nikkei", "digitimes", "the information",
                     "报道", "媒体"],
    }

    def _lanes_of(text: str) -> set:
        low = str(text or "").lower()
        return {lane for lane, kws in RESEARCH_LANES.items() if any(k in low for k in kws)}

    query_path = workspace / "historical_query_log.csv"
    if query_path.exists():
        try:
            with query_path.open(encoding="utf-8-sig", newline="") as fh:
                qrows = list(csv.DictReader(fh))
            covered = set()
            for q in qrows:
                covered |= _lanes_of(str(q.get("query_text", "")) + " " + str(q.get("domains", "")) + " " + str(q.get("notes", "")))
            pass_record(
                checks,
                "research:search-route-diagnostic",
                "observed search routes: "
                + (",".join(sorted(covered)) or "none recorded")
                + "; route breadth is diagnostic only",
            )
        except Exception as exc:
            fail_record(checks, "research:search-route-diagnostic", str(exc), "warning")

    # Provenance honesty: hashes are either real or explicitly absent - never invented.
    if source_path.exists():
        try:
            fake = []
            for s in json.loads(source_path.read_text(encoding="utf-8")).get("sources", []):
                h = str(s.get("content_hash", "") or "")
                if h and not (re.fullmatch(r"sha256:[0-9a-f]{64}", h) or h.startswith("unhashed:")):
                    fake.append(s.get("source_id", "UNKNOWN"))
            if fake:
                fail_record(checks, "sources:content-hash-honesty",
                            "content_hash must be a real sha256:<64hex> or 'unhashed:<reason>' - fabricated-looking hashes: " + ",".join(fake[:8]),
                            "error" if args.strict else "warning")
            else:
                pass_record(checks, "sources:content-hash-honesty")
        except Exception:
            pass

    validated_hash = None
    try:
        validated_hash = validated_input_pack_hash(
            workspace,
            skill_root=skill_root,
            profile=registry_profile,
        )
        pass_record(
            checks,
            "publication:validated-input-pack",
            "strict validation is bound to the registry-resolved non-receipt input pack",
        )
    except PublicationContractError as exc:
        fail_record(checks, "publication:validated-input-pack", str(exc))

    errors = [c for c in checks if not c["passed"] and c["severity"] == "error"]
    warnings = [c for c in checks if not c["passed"] and c["severity"] == "warning"]
    passed = not errors
    result = {
        "workspace": str(workspace),
        "passed": passed,
        "strict": args.strict,
        "errors": len(errors),
        "warnings": len(warnings),
        "validated_input_pack_hash": validated_hash,
        "checks": checks,
    }
    output = workspace / "delivery_validation.json"
    output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if passed else 2


if __name__ == "__main__":
    raise SystemExit(main())
