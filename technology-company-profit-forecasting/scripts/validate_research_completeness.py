#!/usr/bin/env python3
"""Validate research lineage and bind independent judgment to a frozen case.

This validator deliberately does not decide research quality from document,
word, source, lane, topic, dimension or row counts.  Deterministic code owns
only objective contracts: provenance, definition/vintage compatibility,
main-line linkage, falsifier linkage, frozen review inputs and faithful
enforcement of the independent reviewer's readiness decision.
"""
from __future__ import annotations

import argparse
import csv
import json
import re
from datetime import datetime
from pathlib import Path

from artifact_registry import (
    load_registry,
    resolve_active_paths,
    validate_manifest_routes,
    validate_registry,
)
from provenance_contract import (
    ProvenanceNode,
    build_provenance_graph,
    id_set,
    independence_problems,
    read_independence_map,
    source_epistemic_class,
    source_epistemic_class_problems,
    source_origin_record_kind,
)
from runtime_context import load_profile
from scenario_contract import parse_scenario_catalog
from validate_data_series import (
    parse_date,
    upstream_nodes,
    validate_series,
)
from validate_persistence_contract import validate_moat_rows
from validate_technical_evidence import (
    validate_workspace as validate_technical_evidence_workspace,
)
from validate_delivery import (
    external_observation_review_binding,
    frozen_artifact_hash_problems,
)


UNKNOWN = {
    "", "unknown", "pending", "not provided", "not available", "unavailable",
    "tbd", "replace", "n/a", "na", "none",
}
ALLOWED_COVERAGE_STATUS = {
    "accepted",
    "partial_human_required",
    "searched_no_qualified_source",
    "not_material_with_reason",
    "unavailable_due_to_access_or_compliance",
}
UNSUPPORTED_REFERENCE_STATES = {"", "analyst_only", "human_required", "scenario_only"}
REVIEW_SUFFICIENCY = {"adequate", "limited", "inadequate"}
READINESS_ORDER = {
    "not-model-ready": 0,
    "not-decision-ready": 0,
    "hypothesis-grade": 1,
    "screen-grade": 2,
    "research-grade": 3,
    "decision-support": 4,
    "decision-grade": 4,
}
FROZEN_RESEARCH_INPUTS = (
    "source_manifest.json",
    "source_independence_map.csv",
    "forward_signal_cards.csv",
    "model_graph.json",
    "scenario_set.json",
    "data_series_register.csv",
    "material_assumption_support.csv",
    "claim_ledger.jsonl",
)
ORCHESTRATION_RECEIPT_BOUNDARY = "orchestration_receipt_only_not_cryptographic_identity"
CLAIM_PERMISSION_USES = {
    "historical_anchor",
    "base_parameter",
    "technical_bound",
    "scenario_only",
    "monitoring_only",
    "discovery_only",
    "blocked",
}


def substantive(value: object) -> bool:
    return str(value or "").strip().casefold() not in UNKNOWN


def truthy(value: object) -> bool:
    if isinstance(value, bool):
        return value
    return str(value or "").strip().casefold() in {"true", "1", "yes", "y"}


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def read_json(path: Path, errors: list[str]) -> dict:
    if not path.exists():
        errors.append(f"missing {path.name}")
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        errors.append(f"invalid {path.name}: {exc}")
        return {}
    if not isinstance(payload, dict):
        errors.append(f"invalid {path.name}: root must be an object")
        return {}
    return payload


def _aware_datetime(value: object) -> datetime | None:
    if not substantive(value):
        return None
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return None
    return parsed if parsed.utcoffset() is not None else None


def validate_orchestration_receipt(
    raw: object,
    *,
    reviewed_at: object,
) -> list[str]:
    """Validate orchestration evidence, not the reviewer's substantive judgment.

    The receipt is a locally auditable chronology and session-separation
    record.  It is deliberately labelled as non-cryptographic: it cannot prove
    who controlled a session, and must never be described as strong identity
    authentication.
    """

    errors: list[str] = []
    label = "research quality review orchestration_receipt"
    if not isinstance(raw, dict):
        return [f"{label} is required; role labels and booleans do not prove independence"]
    if raw.get("assurance_boundary") != ORCHESTRATION_RECEIPT_BOUNDARY:
        errors.append(
            f"{label}.assurance_boundary must state {ORCHESTRATION_RECEIPT_BOUNDARY}"
        )
    for field in (
        "receipt_id",
        "orchestrator",
        "reviewer_session_id",
        "reviewer_task_id",
        "builder_session_id",
    ):
        if not substantive(raw.get(field)):
            errors.append(f"{label}.{field} is required")
    if (
        substantive(raw.get("reviewer_session_id"))
        and raw.get("reviewer_session_id") == raw.get("builder_session_id")
    ):
        errors.append(f"{label}.reviewer_session_id must differ from builder_session_id")

    timestamps: dict[str, datetime | None] = {}
    for field in (
        "frozen_inputs_delivered_at",
        "review_started_at",
        "initial_conclusion_at",
        "review_completed_at",
        "receipt_issued_at",
    ):
        timestamps[field] = _aware_datetime(raw.get(field))
        if timestamps[field] is None:
            errors.append(f"{label}.{field} must be a timezone-aware ISO timestamp")
    ordered = (
        "frozen_inputs_delivered_at",
        "review_started_at",
        "initial_conclusion_at",
        "review_completed_at",
        "receipt_issued_at",
    )
    if all(timestamps[field] is not None for field in ordered):
        for earlier, later in zip(ordered, ordered[1:]):
            if timestamps[earlier] > timestamps[later]:
                if earlier == "frozen_inputs_delivered_at":
                    errors.append(f"{label}: frozen inputs must be delivered before review starts")
                else:
                    errors.append(f"{label}: {earlier} must not be after {later}")

    reviewed_time = _aware_datetime(reviewed_at)
    completed = timestamps.get("review_completed_at")
    if reviewed_time is None:
        errors.append(f"{label}: reviewed_at must be timezone-aware")
    elif completed is not None and reviewed_time < completed:
        errors.append(f"{label}: reviewed_at predates review_completed_at")

    rebuttal = raw.get("builder_rebuttal")
    if not isinstance(rebuttal, dict):
        errors.append(f"{label}.builder_rebuttal must explicitly state provided or not_provided")
        return errors
    status = str(rebuttal.get("status") or "").strip()
    provided_at = rebuttal.get("provided_at")
    if status == "not_provided":
        if provided_at is not None and provided_at != "":
            errors.append(f"{label}: builder rebuttal marked not_provided cannot have provided_at")
    elif status == "provided":
        rebuttal_time = _aware_datetime(provided_at)
        if rebuttal_time is None:
            errors.append(f"{label}: builder rebuttal provided_at must be timezone-aware")
        else:
            initial = timestamps.get("initial_conclusion_at")
            if initial is not None and rebuttal_time < initial:
                errors.append(f"{label}: builder rebuttal cannot predate reviewer initial conclusion")
            if completed is not None and rebuttal_time > completed:
                errors.append(f"{label}: builder rebuttal cannot postdate review completion")
    else:
        errors.append(f"{label}.builder_rebuttal.status must be provided or not_provided")
    return errors


def _active_csv_rows(path: Path, id_fields: tuple[str, ...]) -> list[dict[str, str]]:
    if not path.exists() or path.stat().st_size == 0:
        return []
    rows = read_csv(path)
    return [
        row for row in rows
        if any(substantive(row.get(field)) for field in id_fields)
    ]


def _independent_pair_exists(
    source_ids: set[str],
    provenance_graph: dict[str, ProvenanceNode],
) -> bool:
    ordered = sorted(source_ids)
    for index, primary in enumerate(ordered):
        for corroborating in ordered[index + 1:]:
            if not independence_problems(
                primary,
                corroborating,
                provenance_graph,
                label="corroboration",
            ):
                return True
    return False


def validate_main_line(
    graph: dict,
) -> tuple[list[str], set[str], set[str], set[str]]:
    """Validate only the objective identity/linkage of thesis carrier nodes."""

    errors: list[str] = []
    nodes = {
        str(node.get("id") or "").strip()
        for node in graph.get("nodes", [])
        if isinstance(node, dict) and substantive(node.get("id"))
    }
    main_line = graph.get("main_line")
    if not isinstance(main_line, dict):
        return ["model_graph.main_line must be an object"], nodes, set(), set()
    carriers = id_set(main_line.get("carrier_node_ids"))
    falsifiers = id_set(main_line.get("falsification_ids"))
    if not carriers:
        errors.append("research contract requires named main-line carrier nodes")
    if not falsifiers:
        errors.append("research contract requires named main-line falsification nodes")
    unknown_carriers = sorted(carriers - nodes)
    unknown_falsifiers = sorted(falsifiers - nodes)
    if unknown_carriers:
        errors.append("main-line carrier nodes are unknown: " + ", ".join(unknown_carriers))
    if unknown_falsifiers:
        errors.append("main-line falsification nodes are unknown: " + ", ".join(unknown_falsifiers))
    return errors, nodes, carriers, falsifiers


def validate_coverage_diagnostics(
    path: Path,
    *,
    known_source_ids: set[str],
) -> tuple[list[str], list[str], dict[str, object]]:
    """Validate authored links while leaving breadth/depth judgment to review."""

    errors: list[str] = []
    warnings: list[str] = []
    rows = _active_csv_rows(path, ("topic",))
    for row in rows:
        topic = str(row.get("topic") or "UNKNOWN").strip()
        status = str(row.get("status") or "").strip().casefold()
        if status not in ALLOWED_COVERAGE_STATUS:
            errors.append(f"research route {topic}: invalid status {status or '<blank>'}")
        accepted_ids = id_set(row.get("accepted_source_ids"))
        rejected_ids = id_set(row.get("rejected_source_ids"))
        unknown = sorted((accepted_ids | rejected_ids) - known_source_ids)
        if unknown:
            errors.append(
                f"research route {topic}: unknown source ids " + ", ".join(unknown)
            )
        if status == "accepted" and not accepted_ids:
            errors.append(f"research route {topic}: accepted status needs source lineage")
        if status != "accepted" and not substantive(row.get("unresolved_questions")):
            errors.append(
                f"research route {topic}: unresolved, unavailable or not-material status "
                "needs a reason/question"
            )
        if not substantive(row.get("model_link")):
            warnings.append(
                f"research route {topic}: no model link; independent reviewer must decide "
                "whether this route can affect the forecast"
            )
    diagnostics = {
        "authored_research_routes": len(rows),
        "unresolved_research_routes": sum(
            1 for row in rows
            if str(row.get("status") or "").strip().casefold() != "accepted"
        ),
        "research_route_topics": [str(row.get("topic") or "").strip() for row in rows],
    }
    return errors, warnings, diagnostics


def validate_material_assumption_lineage(
    rows: list[dict[str, str]],
    *,
    graph: dict,
    carriers: set[str],
    falsifiers: set[str],
    known_scenario_ids: set[str],
    reference_scenario_ids: set[str],
    known_source_ids: set[str],
    eligible_source_ids: set[str],
    provenance_graph: dict[str, ProvenanceNode],
) -> tuple[list[str], dict[str, object]]:
    """Validate reference-path thesis permissions without fixed scenario labels."""

    errors: list[str] = []
    active = [
        row for row in rows
        if substantive(row.get("assumption_id"))
    ]
    main_line_nodes: set[str] = set()
    for carrier in carriers:
        main_line_nodes |= upstream_nodes(graph, carrier)
    thesis_rows = 0
    for row in active:
        assumption_id = str(row.get("assumption_id") or "UNKNOWN").strip()
        scenario_ids = id_set(row.get("scenario"))
        driver_ids = id_set(row.get("driver_link"))
        changes_conclusion = truthy(row.get("changes_conclusion"))
        thesis_carrying = bool(driver_ids & main_line_nodes) or changes_conclusion
        if thesis_carrying and not scenario_ids:
            errors.append(
                f"main-line assumption {assumption_id}: scenario must bind one or more "
                "scenario_set IDs"
            )
            continue
        unknown_scenarios = sorted(scenario_ids - known_scenario_ids)
        if thesis_carrying and unknown_scenarios:
            errors.append(
                f"main-line assumption {assumption_id}: unknown scenario IDs "
                + ", ".join(unknown_scenarios)
            )
            continue
        if not (scenario_ids & reference_scenario_ids) or not thesis_carrying:
            continue
        thesis_rows += 1
        if not substantive(row.get("test_delta")):
            errors.append(
                f"reference-scenario main-line assumption {assumption_id}: test_delta is required so its "
                "forecast consequence can be re-executed"
            )
        unknown_drivers = sorted(driver_ids - {
            str(node.get("id") or "").strip()
            for node in graph.get("nodes", []) if isinstance(node, dict)
        })
        if unknown_drivers:
            errors.append(
                f"reference-scenario main-line assumption {assumption_id}: unknown driver nodes "
                + ", ".join(unknown_drivers)
            )
        support_status = str(row.get("support_status") or "").strip().casefold()
        if support_status in UNSUPPORTED_REFERENCE_STATES:
            errors.append(
                f"reference-scenario main-line assumption {assumption_id}: support_status="
                f"{support_status or '<blank>'} cannot authorize a reference-path thesis carrier"
            )
        source_ids = id_set(row.get("source_ids"))
        if not source_ids:
            errors.append(
                f"reference-scenario main-line assumption {assumption_id}: source_ids are required"
            )
        unknown_sources = sorted(source_ids - known_source_ids)
        if unknown_sources:
            errors.append(
                f"reference-scenario main-line assumption {assumption_id}: unknown source ids "
                + ", ".join(unknown_sources)
            )
        ineligible_sources = sorted(source_ids - eligible_source_ids)
        if ineligible_sources:
            errors.append(
                f"reference-scenario main-line assumption {assumption_id}: rejected/ineligible source ids "
                + ", ".join(ineligible_sources)
            )
        if support_status == "corroborated" and not _independent_pair_exists(
            source_ids & eligible_source_ids,
            provenance_graph,
        ):
            errors.append(
                f"reference-scenario main-line assumption {assumption_id}: corroborated status has no "
                "genuinely independent root/team/method pair"
            )
        trigger_ids = id_set(row.get("falsification_trigger"))
        if not trigger_ids:
            errors.append(
                f"reference-scenario main-line assumption {assumption_id}: falsification_trigger is required"
            )
        elif not trigger_ids & falsifiers:
            errors.append(
                f"reference-scenario main-line assumption {assumption_id}: falsification_trigger must "
                "reference a declared main-line falsification node"
            )
    return errors, {
        "authored_assumptions": len(active),
        "reference_thesis_assumptions": thesis_rows,
    }


def validate_claim_authority_judgments(
    items: object,
    *,
    known_claim_ids: set[str],
    known_source_ids: set[str],
    known_source_epistemic_classes: dict[str, str],
    known_source_origin_record_kinds: dict[str, str],
    known_observation_bindings: dict[str, dict[str, str]],
    claim_observation_ids: dict[str, set[str]],
) -> tuple[list[str], dict[str, dict]]:
    """Validate review-authored claim permissions without judging them by score.

    This function checks that the reviewer made a complete, resolvable and
    claim-specific decision.  Whether the sources are authoritative enough for
    that bounded proposition remains the reviewer's qualitative judgment.
    """

    errors: list[str] = []
    judgments: dict[str, dict] = {}
    if not isinstance(items, list):
        return ["research quality review: claim_authority_judgments must be an array"], {}
    for index, item in enumerate(items, 1):
        label = f"research quality review claim_authority_judgments[{index}]"
        if not isinstance(item, dict):
            errors.append(f"{label} must be an object")
            continue
        claim_id = str(item.get("claim_id") or "").strip()
        if not claim_id:
            errors.append(f"{label}: claim_id is required")
        elif claim_id not in known_claim_ids:
            errors.append(f"{label}: unknown claim_id {claim_id}")
        if claim_id in judgments:
            errors.append(f"{label}: duplicate claim_id {claim_id}")
        elif claim_id:
            judgments[claim_id] = item

        sufficiency = str(item.get("authority_sufficiency") or "").strip().casefold()
        if sufficiency not in REVIEW_SUFFICIENCY:
            errors.append(
                f"{label}: authority_sufficiency must be adequate, limited or inadequate"
            )
        permitted_use = str(item.get("permitted_use") or "").strip()
        if permitted_use not in CLAIM_PERMISSION_USES:
            errors.append(f"{label}: permitted_use is unknown")
        reviewed_raw = item.get("reviewed_source_ids")
        if not isinstance(reviewed_raw, list):
            errors.append(f"{label}: reviewed_source_ids must be an array")
            reviewed_raw = []
        reviewed_items = [str(source_id).strip() for source_id in reviewed_raw]
        reviewed_source_ids = {source_id for source_id in reviewed_items if source_id}
        if not reviewed_source_ids:
            errors.append(f"{label}: reviewed_source_ids must be non-empty")
        if len(reviewed_items) != len(reviewed_source_ids):
            errors.append(f"{label}: reviewed_source_ids must be unique non-empty ids")
        unknown_sources = sorted(reviewed_source_ids - known_source_ids)
        if unknown_sources:
            errors.append(
                f"{label}: unknown reviewed_source_ids " + ", ".join(unknown_sources)
            )
        reviewed_classes_raw = item.get("reviewed_source_epistemic_classes")
        if not isinstance(reviewed_classes_raw, dict):
            errors.append(
                f"{label}: reviewed_source_epistemic_classes must be an object"
            )
        else:
            reviewed_classes = {
                str(source_id).strip(): str(epistemic_class or "").strip()
                for source_id, epistemic_class in reviewed_classes_raw.items()
                if str(source_id).strip()
            }
            if set(reviewed_classes) != reviewed_source_ids:
                errors.append(
                    f"{label}: reviewed_source_epistemic_classes keys must match "
                    "reviewed_source_ids exactly"
                )
            expected_classes = {
                source_id: known_source_epistemic_classes[source_id]
                for source_id in reviewed_source_ids
                if source_id in known_source_epistemic_classes
            }
            if reviewed_classes != expected_classes:
                errors.append(
                    f"{label}: reviewed_source_epistemic_classes must match the frozen "
                    "SourceRecords exactly"
                )
        reviewed_origins_raw = item.get("reviewed_source_origin_record_kinds")
        if not isinstance(reviewed_origins_raw, dict):
            errors.append(
                f"{label}: reviewed_source_origin_record_kinds must be an object"
            )
        else:
            reviewed_origins = {
                str(source_id).strip(): str(origin_kind or "").strip()
                for source_id, origin_kind in reviewed_origins_raw.items()
                if str(source_id).strip()
            }
            expected_origins = {
                source_id: known_source_origin_record_kinds[source_id]
                for source_id in reviewed_source_ids
                if source_id in known_source_origin_record_kinds
            }
            if reviewed_origins != expected_origins:
                errors.append(
                    f"{label}: reviewed_source_origin_record_kinds must match the frozen "
                    "SourceRecords exactly"
                )
        reviewed_observations_raw = item.get("reviewed_observation_bindings")
        expected_observation_ids = claim_observation_ids.get(claim_id, set())
        if not isinstance(reviewed_observations_raw, dict):
            errors.append(f"{label}: reviewed_observation_bindings must be an object")
        else:
            if set(reviewed_observations_raw) != expected_observation_ids:
                errors.append(
                    f"{label}: reviewed_observation_bindings keys must match the "
                    "claim observation_ids exactly"
                )
            for observation_id in sorted(expected_observation_ids):
                reviewed = reviewed_observations_raw.get(observation_id)
                expected = known_observation_bindings.get(observation_id)
                if not isinstance(reviewed, dict) or expected is None:
                    errors.append(
                        f"{label}: observation {observation_id} has no resolvable frozen binding"
                    )
                    continue
                objective = {key: reviewed.get(key) for key in expected}
                if objective != expected:
                    errors.append(
                        f"{label}: reviewed_observation_bindings does not match the frozen "
                        f"observation {observation_id}"
                    )
                if not substantive(reviewed.get("classification_rationale")):
                    errors.append(
                        f"{label}: observation {observation_id} requires a substantive "
                        "classification_rationale"
                    )
        if not substantive(item.get("rationale")):
            errors.append(f"{label}: rationale is required")
    return errors, judgments


def validate_research_quality_review(
    workspace: Path,
    *,
    manifest: dict,
    graph: dict,
    known_source_ids: set[str],
    known_source_epistemic_classes: dict[str, str],
    known_source_origin_record_kinds: dict[str, str],
    known_observation_bindings: dict[str, dict[str, str]],
    eligible_source_ids: set[str],
    strict: bool,
) -> tuple[list[str], list[str], dict[str, object]]:
    """Bind independent qualitative judgment to immutable, resolvable inputs."""

    errors: list[str] = []
    warnings: list[str] = []
    path = workspace / "research_quality_review.json"
    if not path.exists():
        message = (
            "missing research_quality_review.json: deterministic checks cannot judge "
            "industry boundary, noise, cycle, competition, moat or paper-to-production transfer"
        )
        (errors if strict else warnings).append(message)
        return errors, warnings, {"status": "missing"}
    review = read_json(path, errors)
    if review.get("schema_version") != "research-quality-review/v1":
        errors.append("research quality review schema_version must be research-quality-review/v1")
    for field in ("review_id", "reviewed_at", "builder_id", "reviewer_id"):
        if not substantive(review.get(field)):
            errors.append(f"research quality review: {field} is required")
    builder_id = str(review.get("builder_id") or "").strip()
    reviewer_id = str(review.get("reviewer_id") or "").strip()
    if builder_id and reviewer_id and builder_id == reviewer_id:
        errors.append("research quality review: reviewer_id must differ from builder_id")
    if review.get("independent_of_builder") is not True:
        errors.append("research quality review: independent_of_builder must be true")
    errors.extend(
        validate_orchestration_receipt(
            review.get("orchestration_receipt"),
            reviewed_at=review.get("reviewed_at"),
        )
    )

    errors.extend(
        frozen_artifact_hash_problems(
            workspace,
            review.get("frozen_artifacts"),
            FROZEN_RESEARCH_INPUTS,
            label="research quality review frozen input",
        )
    )

    known_claim_ids: set[str] = set()
    claim_observation_ids: dict[str, set[str]] = {}
    claim_path = workspace / "claim_ledger.jsonl"
    if claim_path.exists():
        for line_number, raw in enumerate(
            claim_path.read_text(encoding="utf-8").splitlines(), 1
        ):
            if not raw.strip():
                continue
            try:
                claim = json.loads(raw)
            except Exception as exc:
                errors.append(
                    f"research quality review: invalid claim_ledger.jsonl line "
                    f"{line_number} ({exc})"
                )
                continue
            if not isinstance(claim, dict) or not substantive(claim.get("claim_id")):
                errors.append(
                    f"research quality review: claim_ledger.jsonl line {line_number} "
                    "must name a claim_id"
                )
                continue
            claim_id = str(claim.get("claim_id") or "").strip()
            if claim_id in known_claim_ids:
                errors.append(
                    f"research quality review: duplicate claim_id {claim_id} in claim ledger"
                )
            known_claim_ids.add(claim_id)
            claim_observation_ids[claim_id] = {
                str(observation_id).strip()
                for link in (claim.get("evidence_links") or [])
                if isinstance(link, dict)
                for observation_id in (link.get("observation_ids") or [])
                if str(observation_id).strip()
            }

    authority_errors, authority_judgments = validate_claim_authority_judgments(
        review.get("claim_authority_judgments"),
        known_claim_ids=known_claim_ids,
        known_source_ids=known_source_ids,
        known_source_epistemic_classes=known_source_epistemic_classes,
        known_source_origin_record_kinds=known_source_origin_record_kinds,
        known_observation_bindings=known_observation_bindings,
        claim_observation_ids=claim_observation_ids,
    )
    errors.extend(authority_errors)

    graph_nodes = {
        str(node.get("id") or "").strip()
        for node in graph.get("nodes", []) if isinstance(node, dict)
    }
    main_line = graph.get("main_line") if isinstance(graph.get("main_line"), dict) else {}
    graph_carriers = id_set(main_line.get("carrier_node_ids"))
    graph_falsifiers = id_set(main_line.get("falsification_ids"))
    contradiction = review.get("principal_contradiction")
    if not isinstance(contradiction, dict):
        errors.append("research quality review: principal_contradiction must be an object")
        contradiction = {}
    review_carriers = id_set(contradiction.get("carrier_node_ids"))
    review_falsifiers = id_set(contradiction.get("falsification_node_ids"))
    if review_carriers != graph_carriers:
        errors.append(
            "research quality review: principal_contradiction.carrier_node_ids must cover "
            "the frozen graph main line exactly"
        )
    if review_falsifiers != graph_falsifiers:
        errors.append(
            "research quality review: principal_contradiction.falsification_node_ids must "
            "cover the frozen graph main line exactly"
        )
    for field in ("rival_hypothesis", "reasoning"):
        if not substantive(contradiction.get(field)):
            errors.append(f"research quality review: principal_contradiction.{field} is required")
    judgment = str(contradiction.get("judgment") or "").strip().casefold()
    if judgment not in REVIEW_SUFFICIENCY:
        errors.append(
            "research quality review: principal_contradiction.judgment must be "
            "adequate, limited or inadequate"
        )
    contradiction_sources = id_set(contradiction.get("source_ids"))
    if contradiction_sources - known_source_ids:
        errors.append(
            "research quality review: principal contradiction references unknown source ids "
            + ", ".join(sorted(contradiction_sources - known_source_ids))
        )
    if contradiction_sources - eligible_source_ids:
        errors.append(
            "research quality review: principal contradiction relies on rejected/ineligible sources "
            + ", ".join(sorted(contradiction_sources - eligible_source_ids))
        )

    material_judgments = review.get("material_judgments")
    if not isinstance(material_judgments, list):
        errors.append("research quality review: material_judgments must be an array")
        material_judgments = []
    seen_ids: set[str] = set()
    for index, item in enumerate(material_judgments, 1):
        label = f"research quality review material_judgments[{index}]"
        if not isinstance(item, dict):
            errors.append(f"{label} must be an object")
            continue
        judgment_id = str(item.get("judgment_id") or "").strip()
        if not judgment_id:
            errors.append(f"{label}: judgment_id is required")
        elif judgment_id in seen_ids:
            errors.append(f"{label}: duplicate judgment_id {judgment_id}")
        seen_ids.add(judgment_id)
        for field in ("question", "status", "reasoning", "forecast_consequence"):
            if not substantive(item.get(field)):
                errors.append(f"{label}: {field} is required")
        # Explicit "none" is a meaningful readiness decision, unlike an empty
        # field.  Do not make reviewers invent impact prose where there is no
        # readiness change.
        if not str(item.get("readiness_effect") or "").strip():
            errors.append(f"{label}: readiness_effect is required")
        unknown_sources = id_set(item.get("source_ids")) - known_source_ids
        unknown_nodes = id_set(item.get("model_node_ids")) - graph_nodes
        if unknown_sources:
            errors.append(f"{label}: unknown source ids " + ", ".join(sorted(unknown_sources)))
        if unknown_nodes:
            errors.append(f"{label}: unknown model nodes " + ", ".join(sorted(unknown_nodes)))

    overall = review.get("overall")
    if not isinstance(overall, dict):
        errors.append("research quality review: overall must be an object")
        overall = {}
    sufficiency = str(overall.get("research_sufficiency") or "").strip().casefold()
    if sufficiency not in REVIEW_SUFFICIENCY:
        errors.append(
            "research quality review: overall.research_sufficiency must be adequate, limited or inadequate"
        )
    if not substantive(overall.get("rationale")):
        errors.append("research quality review: overall.rationale is required")
    disagreements = overall.get("unresolved_material_disagreements")
    if not isinstance(disagreements, list):
        errors.append(
            "research quality review: overall.unresolved_material_disagreements must be an array"
        )
        disagreements = []
    readiness_cap = str(overall.get("readiness_cap") or "").strip().casefold()
    if readiness_cap not in READINESS_ORDER:
        errors.append("research quality review: overall.readiness_cap is unknown")
    target = str(
        manifest.get("readiness_result") or manifest.get("readiness_target") or ""
    ).strip().casefold()
    if target in READINESS_ORDER and readiness_cap in READINESS_ORDER:
        if READINESS_ORDER[target] > READINESS_ORDER[readiness_cap]:
            errors.append(
                f"declared readiness {target} exceeds independent research review cap {readiness_cap}"
            )
    if sufficiency == "inadequate":
        errors.append("independent research review judges the case inadequate")
    if sufficiency == "limited" and not disagreements:
        errors.append(
            "limited independent research review must preserve unresolved material disagreements"
        )
    if judgment == "inadequate" and sufficiency == "adequate":
        errors.append(
            "overall research sufficiency cannot be adequate when the principal contradiction is inadequate"
        )
    return errors, warnings, {
        "status": "bound" if not errors else "invalid",
        "review_id": review.get("review_id"),
        "reviewer_id": reviewer_id,
        "identity_assurance": ORCHESTRATION_RECEIPT_BOUNDARY,
        "research_sufficiency": sufficiency or "unknown",
        "readiness_cap": readiness_cap or "unknown",
        "claim_authority_judgment_count_diagnostic": len(authority_judgments),
        "material_judgment_count_diagnostic": len(material_judgments),
    }


def validate_research_workspace(workspace: Path, *, strict: bool) -> dict[str, object]:
    workspace = Path(workspace).resolve()
    errors: list[str] = []
    warnings: list[str] = []
    diagnostics: dict[str, object] = {}

    manifest = read_json(workspace / "run_manifest.json", errors)
    source_manifest = read_json(workspace / "source_manifest.json", errors)
    graph = read_json(workspace / "model_graph.json", errors)
    scenario_set = read_json(workspace / "scenario_set.json", errors)

    scenario_catalog, scenario_catalog_problems = parse_scenario_catalog(scenario_set)
    errors.extend(
        f"scenario catalog: {problem}" for problem in scenario_catalog_problems
    )
    known_scenario_ids = (
        set(scenario_catalog.ids) if scenario_catalog is not None else set()
    )
    reference_scenario_ids = (
        {scenario_catalog.reference_id} if scenario_catalog is not None else set()
    )

    active_artifact_paths: set[str] = set()
    try:
        skill_root = Path(__file__).resolve().parents[1]
        registry_profile = (
            str(manifest.get("artifact_profile") or "").strip()
            or str(load_profile(skill_root).get("profile") or "").strip()
            or None
        )
        artifact_registry = load_registry(skill_root / "assets/artifact_registry.json")
        registry_problems = validate_registry(artifact_registry, skill_root=skill_root)
        route_problems = validate_manifest_routes(artifact_registry, manifest)
        if registry_problems:
            errors.extend(f"artifact registry: {problem}" for problem in registry_problems)
        if route_problems:
            errors.extend(f"materiality routes: {problem}" for problem in route_problems)
        if not registry_problems and not route_problems:
            active_artifact_paths = set(
                resolve_active_paths(
                    artifact_registry,
                    manifest,
                    profile=registry_profile,
                )
            )
    except Exception as exc:
        errors.append(f"artifact registry resolution failed: {exc}")

    main_line_errors, graph_nodes, carriers, falsifiers = validate_main_line(graph)
    errors.extend(main_line_errors)

    source_rows = [
        item for item in source_manifest.get("sources", [])
        if isinstance(item, dict)
    ]
    source_records_by_id = {
        str(item.get("source_id") or "").strip(): item
        for item in source_rows
        if substantive(item.get("source_id"))
    }
    known_source_ids = {
        str(item.get("source_id") or "").strip()
        for item in source_rows if substantive(item.get("source_id"))
    }
    source_epistemic_classes = {
        str(item.get("source_id") or "").strip(): source_epistemic_class(item)
        for item in source_rows
        if substantive(item.get("source_id"))
    }
    source_origin_record_kinds = {
        source_id: source_origin_record_kind(item)
        for source_id, item in source_records_by_id.items()
    }
    for item in source_rows:
        errors.extend(source_epistemic_class_problems(item))
    eligible_source_ids = {
        str(item.get("source_id") or "").strip()
        for item in source_rows
        if substantive(item.get("source_id"))
        and str(item.get("decision_status") or "accepted").strip().casefold()
        not in {"rejected", "not_material"}
    }
    diagnostics["accepted_source_count"] = len(eligible_source_ids)
    diagnostics["declared_source_words"] = sum(
        max(0, int(float(item.get("word_count") or 0)))
        for item in source_rows
        if str(item.get("word_count") or "").strip().replace(".", "", 1).isdigit()
    )

    provenance_graph, provenance_errors = build_provenance_graph(
        source_rows,
        read_independence_map(workspace / "source_independence_map.csv"),
        strict=strict,
    )
    errors.extend(provenance_errors)
    recorded_at = parse_date(manifest.get("as_of"))
    if recorded_at is None:
        errors.append("run_manifest.as_of must be a valid snapshot timestamp")

    data_path = workspace / "data_series_register.csv"
    series_rows: list[dict[str, str]] = []
    if not data_path.exists():
        errors.append("missing data_series_register.csv")
    else:
        try:
            series_rows = read_csv(data_path)
            errors.extend(
                validate_series(
                    series_rows,
                    known_source_ids,
                    eligible_source_ids,
                    provenance_graph,
                    graph,
                    strict,
                )
            )
            diagnostics["data_series_count"] = sum(
                1 for row in series_rows if substantive(row.get("series_id"))
            )
        except Exception as exc:
            errors.append(f"invalid data_series_register.csv: {exc}")
    observation_bindings: dict[str, dict[str, str]] = {}
    for row in series_rows:
        observation_id = str(row.get("series_id") or "").strip()
        source = source_records_by_id.get(str(row.get("source_id") or "").strip())
        if observation_id and isinstance(source, dict):
            observation_bindings[observation_id] = external_observation_review_binding(
                row, source
            )

    coverage_errors, coverage_warnings, coverage_diagnostics = validate_coverage_diagnostics(
        workspace / "research_coverage_matrix.csv",
        known_source_ids=known_source_ids,
    )
    errors.extend(coverage_errors)
    warnings.extend(coverage_warnings)
    diagnostics.update(coverage_diagnostics)

    support_path = workspace / "material_assumption_support.csv"
    if not support_path.exists():
        errors.append("missing material_assumption_support.csv")
    else:
        try:
            support_errors, support_diagnostics = validate_material_assumption_lineage(
                read_csv(support_path),
                graph=graph,
                carriers=carriers,
                falsifiers=falsifiers,
                known_scenario_ids=known_scenario_ids,
                reference_scenario_ids=reference_scenario_ids,
                known_source_ids=known_source_ids,
                eligible_source_ids=eligible_source_ids,
                provenance_graph=provenance_graph,
            )
            errors.extend(support_errors)
            diagnostics.update(support_diagnostics)
        except Exception as exc:
            errors.append(f"invalid material_assumption_support.csv: {exc}")

    # Optional routes are validated when authored as material.  Their absence
    # is not a universal row-count failure; the independent review judges
    # whether omitting the route is economically defensible for this company.
    quality_rows = _active_csv_rows(
        workspace / "company_quality_moat_register.csv", ("dimension", "claim")
    )
    quality_rows = [
        row for row in quality_rows
        if str(row.get("status") or "").strip().casefold()
        in {"accepted", "partial_human_required"}
    ]
    diagnostics["authored_quality_claims"] = len(quality_rows)
    if quality_rows:
        independent_source_ids = {
            str(source.get("source_id") or "").strip()
            for source in source_rows
            if str(source.get("independence") or "").strip().casefold()
            not in {"", "first_party", "issuer", "company"}
        }
        monitor_nodes = set(falsifiers)
        monitor_path = workspace / "driver_monitoring.csv"
        if monitor_path.exists():
            monitor_nodes |= {
                str(row.get("driver_node_id") or "").strip()
                for row in read_csv(monitor_path)
                if substantive(row.get("driver_node_id"))
            }
        errors.extend(
            validate_moat_rows(
                quality_rows,
                known_source_ids=eligible_source_ids,
                independent_source_ids=independent_source_ids,
                known_node_ids=graph_nodes,
                monitor_node_ids=monitor_nodes,
            )
        )

    technology_route_active = (
        "technology_commercialization_register.csv" in active_artifact_paths
    )
    technology_rows = (
        _active_csv_rows(
            workspace / "technology_commercialization_register.csv",
            ("technology_or_product",),
        )
        if technology_route_active
        else []
    )
    material_technology_rows = [
        row for row in technology_rows
        if str(row.get("materiality") or "").strip().casefold()
        in {"critical", "high", "material"}
        and str(row.get("allowed_model_use") or "").strip().casefold()
        not in {"", "not_material", "background", "discovery_only"}
    ]
    diagnostics["technology_route_active"] = technology_route_active
    diagnostics["authored_material_technology_routes"] = len(material_technology_rows)
    if technology_route_active:
        technical_errors, technical_warnings, technical_diagnostics = (
            validate_technical_evidence_workspace(workspace, strict=strict)
        )
        errors.extend(technical_errors)
        warnings.extend(technical_warnings)
        diagnostics.update(technical_diagnostics)

    review_errors, review_warnings, review_summary = validate_research_quality_review(
        workspace,
        manifest=manifest,
        graph=graph,
        known_source_ids=known_source_ids,
        known_source_epistemic_classes=source_epistemic_classes,
        known_source_origin_record_kinds=source_origin_record_kinds,
        known_observation_bindings=observation_bindings,
        eligible_source_ids=eligible_source_ids,
        strict=strict,
    )
    errors.extend(review_errors)
    warnings.extend(review_warnings)

    passed = not errors
    result: dict[str, object] = {
        "workspace": str(workspace),
        "passed": passed,
        "strict": strict,
        "errors": errors,
        "warnings": warnings,
        "hard_gate_inputs": [
            "point-in-time source provenance",
            "definition-compatible main-line measurements",
            "main-line assumption and falsifier lineage",
            "frozen independent research judgment",
            "independent review readiness cap",
        ],
        "diagnostics": diagnostics,
        "independent_judgment": review_summary,
        "research_sufficiency": (
            review_summary.get("research_sufficiency", "unknown")
            if passed else "research-contract-failed"
        ),
        "process_integrity_note": (
            "Counts and prose depth are diagnostics only. Passing means the objective "
            "research contract is traceable and the independent judgment is bound; it "
            "does not mechanically certify that the thesis is insightful."
        ),
    }
    (workspace / "research_completeness.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return result


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Validate causal research lineage and frozen independent judgment."
    )
    parser.add_argument("--workspace", required=True)
    parser.add_argument("--strict", action="store_true")
    args = parser.parse_args()
    result = validate_research_workspace(Path(args.workspace), strict=args.strict)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["passed"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
