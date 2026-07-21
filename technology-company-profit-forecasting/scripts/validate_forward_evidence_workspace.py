#!/usr/bin/env python3
"""Validate dated forward-signal permissions without collection quotas.

SignalCards are an evidence-to-model ledger, not a scorecard.  This validator
checks objective provenance, permission and graph-link contracts for
the rows an analyst actually accepts.  It deliberately does not require a
number of signals, source families, technical papers, searches or prose
sections; independent research review judges whether material uncertainty was
adequately investigated.
"""
from __future__ import annotations

import argparse
import csv
import json
from datetime import datetime, timezone
from pathlib import Path

from provenance_contract import (
    build_provenance_graph,
    canonical_text,
    read_independence_map,
    source_epistemic_class_problems,
)
from validate_delivery import (
    claim_requires_independent_authority,
    load_frozen_claim_authority_judgments,
    source_authority_semantics,
    validate_claim_source_authority,
)


BASE_USES = {"base_point", "base_driver", "base_parameter"}
MONITOR_USES = {"monitor", "monitor_trigger", "search_trigger"}
DISCOVERY_USES = {"discovery", "discovery_only"}
SCENARIO_USES = {"scenario_only", "scenario_probability", "technical_bound"}
HISTORICAL_USES = {"historical_anchor"}
ACTUAL_USES = {"actual_only"}
MODEL_CHANGING_SIGNAL_USES = BASE_USES | SCENARIO_USES | HISTORICAL_USES
NON_MODEL_SIGNAL_USES = MONITOR_USES | DISCOVERY_USES | ACTUAL_USES
SIGNAL_ALLOWED_USES = MODEL_CHANGING_SIGNAL_USES | NON_MODEL_SIGNAL_USES
SIGNAL_TO_CLAIM_USES = {
    "base_point": {"historical_anchor", "base_parameter"},
    "base_driver": {"historical_anchor", "base_parameter"},
    "base_parameter": {"historical_anchor", "base_parameter"},
    "historical_anchor": {"historical_anchor"},
    "technical_bound": {"technical_bound"},
    "scenario_only": {"scenario_only"},
    "scenario_probability": {"scenario_only"},
}
BOUNDARY_ROLES = {"failure_boundary", "feasibility_bound", "technical_bound"}
BASE_COMPATIBLE_CLAIM_USES = {"historical_anchor", "base_parameter"}
HARD_ANCHOR_CLAIM_TYPES = {"reported_fact", "derived_fact"}
HARD_ANCHOR_PROPOSITION_SCOPES = {"reported_history", "current_observed_state"}
SUBJECTIVE_CLAIM_TYPES = {"management_claim", "analyst_assumption", "scenario"}


def parse_datetime(value: object) -> datetime:
    text = str(value or "").strip()
    if len(text) == 10:
        text += "T23:59:59+00:00"
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    parsed = datetime.fromisoformat(text)
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def _active(rows: list[dict[str, str]], key: str) -> list[dict[str, str]]:
    return [
        row for row in rows
        if str(row.get(key) or "").strip().casefold() not in {"", "tbd", "replace"}
    ]


def _split_ids(value: object) -> set[str]:
    return {
        item.strip()
        for item in str(value or "").replace(",", ";").split(";")
        if item.strip()
    }


def _source_is_subjective(source: dict) -> bool:
    """Classify controlled SourceRecord semantics, never source-family names."""

    return bool(
        source_authority_semantics(source) & {"management", "expert_or_analyst"}
    )


def _support_link(claim: dict, source_id: str) -> dict | None:
    for link in claim.get("evidence_links") or []:
        if not isinstance(link, dict):
            continue
        if (
            str(link.get("source_id") or "").strip() == source_id
            and str(link.get("relation") or "").strip() == "support"
        ):
            return link
    return None


def _claim_matches_signal_driver(claim: dict, model_driver: str) -> bool:
    return bool(model_driver) and model_driver in {
        str(item).strip()
        for item in (claim.get("driver_node_ids") or [])
        if str(item).strip()
    }


def validate_signal_allowed_use(signal_id: str, allowed_use: str) -> list[str]:
    """Validate a permission type without assigning quality or evidence weight."""

    if not allowed_use:
        return [f"signal {signal_id} has no allowed_use"]
    if allowed_use not in SIGNAL_ALLOWED_USES:
        return [
            f"signal {signal_id} has unknown allowed_use {allowed_use}; "
            "use a declared permission type"
        ]
    return []


def validate_model_changing_signal_permissions(
    signal_rows: list[dict[str, str]],
    source_records_by_id: dict[str, dict],
    claims_by_id: dict[str, dict] | None = None,
    authority_judgments: dict[str, dict] | None = None,
    observation_records_by_id: dict[str, dict] | None = None,
) -> list[str]:
    """Bind each model-changing signal to its proposition-level permission.

    Deterministic checks prove identity, source-link, use and driver alignment.
    They do not infer semantic authority from a publisher or source-family
    label.  Independent review retains the qualitative decision about whether
    the proposition and measurement actually deserve the declared permission.
    """

    claims_by_id = claims_by_id or {}
    authority_judgments = authority_judgments or {}
    observation_records_by_id = observation_records_by_id or {}
    problems: list[str] = []
    for row in signal_rows:
        signal_id = str(row.get("signal_id") or "UNKNOWN").strip()
        signal_use = str(row.get("allowed_use") or "").strip().casefold()
        compatible_claim_uses = SIGNAL_TO_CLAIM_USES.get(signal_use)
        if compatible_claim_uses is None:
            continue
        source_id = str(row.get("source_id") or "").strip()
        model_driver = str(row.get("model_driver") or "").strip()
        claim_ids = _split_ids(row.get("claim_ids"))
        if not claim_ids:
            problems.append(
                f"Model-changing signal {signal_id} ({signal_use}) requires claim_ids; "
                "source directness alone "
                "does not grant model permission"
            )
            continue

        for claim_id in sorted(claim_ids):
            claim = claims_by_id.get(claim_id)
            if not isinstance(claim, dict):
                problems.append(
                    f"Model-changing signal {signal_id} has unknown claim_id {claim_id}"
                )
                continue
            if str(claim.get("status") or "").strip() != "accepted":
                problems.append(
                    f"Model-changing signal {signal_id} claim {claim_id} is not accepted"
                )
            claim_use = str(claim.get("allowed_use") or "").strip()
            if claim_use not in compatible_claim_uses:
                problems.append(
                    f"Model-changing signal {signal_id} claim {claim_id} does not permit "
                    f"{signal_use} use"
                )
            if source_id not in {
                str(item).strip()
                for item in (claim.get("source_ids") or [])
                if str(item).strip()
            }:
                problems.append(
                    f"Model-changing signal {signal_id} claim {claim_id} does not name "
                    f"source_id {source_id or '<blank>'}"
                )
            if not _claim_matches_signal_driver(claim, model_driver):
                problems.append(
                    f"Model-changing signal {signal_id} claim {claim_id} does not bind "
                    f"model_driver {model_driver or '<blank>'}"
                )
            link = _support_link(claim, source_id)
            if link is None:
                problems.append(
                    f"Model-changing signal {signal_id} claim {claim_id} has no source-specific "
                    f"support evidence link for {source_id or '<blank>'}"
                )
            problems.extend(
                f"Model-changing signal {signal_id}: {problem}"
                for problem in validate_claim_source_authority(
                    claim,
                    source_records=source_records_by_id,
                    authority_judgments=authority_judgments,
                    observation_records=observation_records_by_id,
                )
            )
    return problems


def validate_base_anchor_permissions(
    accepted_base: list[dict[str, str]],
    source_records_by_id: dict[str, dict],
    claims_by_id: dict[str, dict] | None = None,
    authority_judgments: dict[str, dict] | None = None,
    observation_records_by_id: dict[str, dict] | None = None,
) -> list[str]:
    """Apply common bindings and require one factual direct Base anchor."""

    if not accepted_base:
        return []
    claims_by_id = claims_by_id or {}
    authority_judgments = authority_judgments or {}
    normalized_base = [
        row if str(row.get("allowed_use") or "").strip() else {**row, "allowed_use": "base_driver"}
        for row in accepted_base
    ]
    problems = validate_model_changing_signal_permissions(
        normalized_base,
        source_records_by_id,
        claims_by_id,
        authority_judgments,
        observation_records_by_id,
    )
    direct_anchor_found = False
    for row in accepted_base:
        signal_id = str(row.get("signal_id") or "UNKNOWN").strip()
        source_id = str(row.get("source_id") or "").strip()
        source = source_records_by_id.get(source_id, {})
        role = str(row.get("evidence_role") or "").strip().casefold()
        source_role = str(source.get("role") or "").strip().casefold()
        model_driver = str(row.get("model_driver") or "").strip()
        claim_ids = _split_ids(row.get("claim_ids"))
        bound_claims = [
            (claim, link)
            for claim_id in sorted(claim_ids)
            if isinstance((claim := claims_by_id.get(claim_id)), dict)
            if (link := _support_link(claim, source_id)) is not None
        ]

        if _source_is_subjective(source) and not any(
            str(claim.get("claim_type") or "").strip() in SUBJECTIVE_CLAIM_TYPES
            and claim_requires_independent_authority(claim, source_records_by_id)
            for claim, _link in bound_claims
        ):
            problems.append(
                f"Base signal {signal_id}: management/expert directness cannot become "
                "an external operating anchor without a proposition-compatible "
                "management or analyst claim permission"
            )

        if (
            role not in BOUNDARY_ROLES
            and source_role != "technical_boundary"
            and not _source_is_subjective(source)
            and str(source.get("directness") or "").strip().casefold() == "direct"
            and any(
                str(claim.get("status") or "").strip() == "accepted"
                and str(claim.get("claim_type") or "").strip()
                in HARD_ANCHOR_CLAIM_TYPES
                and str(claim.get("proposition_scope") or "").strip()
                in HARD_ANCHOR_PROPOSITION_SCOPES
                and str(claim.get("allowed_use") or "").strip()
                in BASE_COMPATIBLE_CLAIM_USES
                and str(link.get("evidence_function") or "").strip()
                == "direct_anchor"
                and _claim_matches_signal_driver(claim, model_driver)
                for claim, link in bound_claims
            )
        ):
            direct_anchor_found = True
    if not direct_anchor_found:
        problems.append(
            "Base forward evidence has no proposition-compatible direct operating "
            "or measurement anchor"
        )
    return problems


def read_claim_ledger(path: Path) -> tuple[dict[str, dict], list[str]]:
    claims: dict[str, dict] = {}
    problems: list[str] = []
    if not path.exists() or path.stat().st_size == 0:
        return {}, ["Model-changing forward evidence requires non-empty claim_ledger.jsonl"]
    for line_no, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not raw.strip():
            continue
        try:
            claim = json.loads(raw)
        except Exception as exc:
            problems.append(f"claim_ledger.jsonl line {line_no} is invalid JSON: {exc}")
            continue
        if not isinstance(claim, dict):
            problems.append(f"claim_ledger.jsonl line {line_no} must be an object")
            continue
        claim_id = str(claim.get("claim_id") or "").strip()
        if not claim_id:
            problems.append(f"claim_ledger.jsonl line {line_no} has no claim_id")
        elif claim_id in claims:
            problems.append(f"duplicate claim_id {claim_id} in claim_ledger.jsonl")
        else:
            claims[claim_id] = claim
    return claims, problems


def validate_workspace(workspace: Path, *, strict: bool) -> dict[str, object]:
    errors: list[str] = []
    warnings: list[str] = []
    required = [
        "forward_signal_cards.csv",
        "source_independence_map.csv",
        "source_manifest.json",
    ]
    manifest_path = workspace / "run_manifest.json"
    if not manifest_path.exists():
        return {"passed": False, "errors": ["missing run_manifest.json"], "warnings": []}
    json.loads(manifest_path.read_text(encoding="utf-8"))
    for name in required:
        path = workspace / name
        if not path.exists() or path.stat().st_size == 0:
            errors.append(f"missing {name}")
    if errors:
        return {"passed": False, "errors": errors, "warnings": warnings}

    source_manifest = json.loads(
        (workspace / "source_manifest.json").read_text(encoding="utf-8")
    )
    source_records = [
        row for row in source_manifest.get("sources", []) if isinstance(row, dict)
    ]
    source_records_by_id = {
        str(row.get("source_id") or "").strip(): row
        for row in source_records
        if str(row.get("source_id") or "").strip()
    }
    observation_records_by_id: dict[str, dict] = {}
    observation_path = workspace / "data_series_register.csv"
    if observation_path.exists():
        observation_records_by_id = {
            str(row.get("series_id") or "").strip(): row
            for row in read_csv(observation_path)
            if str(row.get("series_id") or "").strip()
        }
    for source in source_records:
        errors.extend(source_epistemic_class_problems(source))
    provenance, provenance_errors = build_provenance_graph(
        source_records,
        read_independence_map(workspace / "source_independence_map.csv"),
        strict=strict,
    )
    errors.extend(provenance_errors)

    signal_rows = _active(read_csv(workspace / "forward_signal_cards.csv"), "signal_id")
    accepted_base: list[dict[str, str]] = []
    accepted_non_base_model_changes: list[dict[str, str]] = []
    for row in signal_rows:
        signal_id = str(row.get("signal_id") or "UNKNOWN").strip()
        source_id = str(row.get("source_id") or "").strip()
        node = provenance.get(source_id)
        if node is None:
            errors.append(f"signal {signal_id} has unknown provenance source_id {source_id or '<blank>'}")
            continue
        if str(row.get("independence_cluster") or "").strip() != node.independence_cluster:
            errors.append(f"signal {signal_id} independence_cluster does not match source provenance")
        if canonical_text(row.get("publisher")) != node.publisher:
            errors.append(f"signal {signal_id} publisher does not match source provenance")
        try:
            parse_datetime(row.get("published_at"))
        except Exception:
            errors.append(f"invalid date {signal_id}")

        allowed_use = str(row.get("allowed_use") or "").strip().casefold()
        tier = str(row.get("evidence_tier") or "").strip().upper()
        role = str(row.get("evidence_role") or "").strip().casefold()
        source_role = str(source_records_by_id.get(source_id, {}).get("role") or "").strip().casefold()
        model_driver = str(row.get("model_driver") or "").strip()
        errors.extend(validate_signal_allowed_use(signal_id, allowed_use))
        if allowed_use in MODEL_CHANGING_SIGNAL_USES and not model_driver:
            errors.append(f"signal {signal_id} changes the model but has no model_driver")
        if (role in BOUNDARY_ROLES or source_role == "technical_boundary") and allowed_use in BASE_USES:
            errors.append(f"boundary-to-base {signal_id}")
        if tier == "E4" and allowed_use not in (MONITOR_USES | DISCOVERY_USES):
            errors.append(f"E4 permission {signal_id}")
        if role in {"failure_boundary", "feasibility_bound"} and not model_driver:
            errors.append(f"technical boundary {signal_id} is not linked to a model driver")
        if allowed_use in BASE_USES:
            accepted_base.append(row)
        elif allowed_use in MODEL_CHANGING_SIGNAL_USES:
            accepted_non_base_model_changes.append(row)

    # A single direct, definition-matched observation can be a valid hard
    # anchor. Source-family labels are routing metadata, never authority; the
    # accepted claim and its source-specific evidence link carry permission.
    claims_by_id: dict[str, dict] = {}
    authority_judgments: dict[str, dict] = {}
    if accepted_base or accepted_non_base_model_changes:
        claim_path = workspace / "claim_ledger.jsonl"
        claims_by_id, claim_errors = read_claim_ledger(claim_path)
        errors.extend(claim_errors)
        if claim_path.exists() and claim_path.stat().st_size > 0:
            authority_judgments, review_binding_problems = (
                load_frozen_claim_authority_judgments(workspace, claim_path)
            )
            errors.extend(review_binding_problems)
    errors.extend(
        validate_base_anchor_permissions(
            accepted_base,
            source_records_by_id,
            claims_by_id,
            authority_judgments,
            observation_records_by_id,
        )
    )
    errors.extend(
        validate_model_changing_signal_permissions(
            accepted_non_base_model_changes,
            source_records_by_id,
            claims_by_id,
            authority_judgments,
            observation_records_by_id,
        )
    )

    if not signal_rows:
        warnings.append(
            "no forward signal rows were authored; independent research review must "
            "decide whether statutory evidence alone is adequate"
        )
    return {
        "passed": not errors,
        "errors": errors,
        "warnings": warnings,
        "diagnostics": {
            "signal_count": len(signal_rows),
            "source_families": sorted(
                {
                    str(row.get("source_family") or "").strip().casefold()
                    for row in signal_rows
                    if str(row.get("source_family") or "").strip()
                }
            ),
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--workspace", required=True)
    parser.add_argument("--strict", action="store_true")
    args = parser.parse_args()
    result = validate_workspace(Path(args.workspace).resolve(), strict=args.strict)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["passed"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
