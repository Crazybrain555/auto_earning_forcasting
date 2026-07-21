#!/usr/bin/env python3
"""Validate observation-level data lineage without producing a quality score."""
from __future__ import annotations

import argparse
import csv
import json
import math
from datetime import datetime, timezone
from pathlib import Path

from provenance_contract import (
    ProvenanceNode,
    build_provenance_graph,
    independence_problems,
    read_independence_map,
    source_epistemic_class_problems,
    validate_structured_numeric_bridge,
)


# Explicit "N/A" and "none" are valid values for non-monetary currency and an
# untransformed raw series.  They are not silently missing; placeholders remain
# rejected by field-specific and status checks below.
UNKNOWN = {"", "tbd", "pending", "unknown", "not provided"}
ALLOWED_STATUS = {"accepted", "scenario_only", "monitoring", "human_required", "not_material_with_reason"}
LIMITED_USE = {"scenario_only", "monitoring", "discovery_only", "human_required", "cross_check"}
FACT_STATUS = {"accepted", "human_required"}
OBSERVATION_TYPES = {"stock", "flow", "average", "rate", "price", "index", "count", "other"}
COMPARABILITY_FIELDS = (
    "metric_construct_id",
    "unit",
    "currency",
    "entity_scope",
    "product_scope",
    "geography_scope",
    "period_start",
    "period_end",
    "frequency",
)


def split_ids(raw: object) -> set[str]:
    text = str(raw or "").replace(",", ";")
    return {item.strip() for item in text.split(";") if item.strip()}


def substantive(value: object) -> bool:
    return str(value or "").strip().lower() not in UNKNOWN


def meaningful(value: object) -> bool:
    return substantive(value) and str(value or "").strip().lower() not in {"n/a", "na", "none"}


def canonical_basis(value: object) -> str:
    return " ".join(str(value or "").strip().lower().split())


def finite_number(value: object) -> float | None:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if math.isfinite(number) else None


def parse_bridge_map(raw: object, sid: str, errors: list[str]) -> dict[str, dict]:
    text = str(raw or "").strip()
    if not text:
        return {}
    try:
        payload = json.loads(text)
    except (TypeError, ValueError, json.JSONDecodeError):
        errors.append(f"{sid}: cross_check_bridge_json must be valid JSON")
        return {}
    if not isinstance(payload, dict):
        errors.append(f"{sid}: cross_check_bridge_json must map cross-check series ids to bridges")
        return {}
    invalid = sorted(str(key) for key, value in payload.items() if not isinstance(value, dict))
    if invalid:
        errors.append(f"{sid}: bridge entries must be objects: " + ", ".join(invalid))
    return {str(key): value for key, value in payload.items() if isinstance(value, dict)}


def validate_quantified_bridge(
    sid: str,
    check_id: str,
    row: dict[str, str],
    cross_check_row: dict[str, str],
    bridge: dict,
    mismatches: list[str],
    source_ids: set[str],
    eligible_source_ids: set[str],
) -> list[str]:
    errors: list[str] = []
    label = f"{sid}: cross-check {check_id} quantified basis bridge"
    if str(bridge.get("input_series_id") or "").strip() != check_id:
        errors.append(f"{label} input_series_id must be {check_id}")
    if str(bridge.get("target_series_id") or "").strip() != sid:
        errors.append(f"{label} target_series_id must be {sid}")
    declared_mismatches = bridge.get("mismatch_fields")
    if not isinstance(declared_mismatches, list):
        errors.append(f"{label} mismatch_fields must be a list")
    else:
        declared = {str(item).strip() for item in declared_mismatches if str(item).strip()}
        if declared != set(mismatches):
            errors.append(
                f"{label} mismatch_fields must equal actual mismatches: "
                + ", ".join(mismatches)
            )
    errors.extend(
        validate_structured_numeric_bridge(
            bridge,
            label=label,
            known_source_ids=source_ids,
            eligible_source_ids=eligible_source_ids,
            expected_source_ids={str(cross_check_row.get("source_id") or "").strip()},
            expected_target_ids={str(row.get("source_id") or "").strip()},
            expected_source_unit=str(cross_check_row.get("unit") or "").strip(),
            expected_target_unit=str(row.get("unit") or "").strip(),
        )
    )

    target_basis = bridge.get("target_basis")
    if not isinstance(target_basis, dict):
        errors.append(f"{label} target_basis must be an object")
    else:
        for field in COMPARABILITY_FIELDS:
            if canonical_basis(target_basis.get(field)) != canonical_basis(row.get(field)):
                errors.append(f"{label} target_basis.{field} must match target series {sid}")

    return errors


def parse_date(value: object) -> datetime | None:
    text = str(value or "").strip()
    if not text:
        return None
    try:
        return datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        try:
            return datetime.fromisoformat(text + "T00:00:00")
        except ValueError:
            return None


def utc(value: datetime) -> datetime:
    return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value.astimezone(timezone.utc)


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def upstream_nodes(graph: dict, target: str) -> set[str]:
    """Return the target and every node that causally feeds it.

    A series may measure an observable upstream of a thesis carrier rather than
    the carrier itself.  Walking declared equations keeps that linkage explicit
    without pretending that any unrelated, well-documented series supports the
    investment main line.
    """

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
    pending = [target]
    seen: set[str] = set()
    while pending:
        current = pending.pop()
        if current in seen:
            continue
        seen.add(current)
        pending.extend(reverse.get(current, set()) - seen)
    return seen


def validate_series(
    rows: list[dict[str, str]],
    source_ids: set[str],
    eligible_source_ids: set[str],
    provenance_graph: dict[str, ProvenanceNode],
    graph: dict,
    strict: bool,
) -> list[str]:
    errors: list[str] = []
    active = [row for row in rows if substantive(row.get("series_id"))]
    ids = [str(row.get("series_id") or "").strip() for row in active]
    if not active:
        return ["no substantive data series rows"]
    duplicates = sorted({item for item in ids if ids.count(item) > 1})
    if duplicates:
        errors.append("duplicate series ids: " + ", ".join(duplicates))
    by_id = {str(row.get("series_id") or "").strip(): row for row in active}
    graph_nodes = {str(node.get("id")): node for node in graph.get("nodes", []) if isinstance(node, dict)}
    if active and "cross_check_bridge_json" not in active[0]:
        errors.append("data series register missing cross_check_bridge_json column")

    always_required = {
        "metric_name", "metric_construct_id", "observation_value", "observation_type",
        "available_at", "vintage_id", "revision_of_series_id", "classification_version",
        "input_series_ids", "source_id", "original_source_id", "independence_cluster",
        "measurement_method_id", "published_at", "retrieved_at", "vintage_at", "revision_at",
        "period_start", "period_end",
        "frequency", "unit", "currency", "metric_definition", "entity_scope",
        "product_scope", "geography_scope", "population_coverage", "transformation",
        "revision_policy", "lag_days", "known_bias", "allowed_model_use",
        "driver_node_ids", "conclusion_critical", "status",
    }
    for row in active:
        sid = str(row.get("series_id") or "UNKNOWN").strip()
        missing = sorted(field for field in always_required if not substantive(row.get(field)))
        if missing:
            errors.append(f"{sid}: missing " + ", ".join(missing))
        for field in (
            "published_at", "retrieved_at", "available_at", "vintage_at", "revision_at",
            "period_start", "period_end",
        ):
            if substantive(row.get(field)) and parse_date(row.get(field)) is None:
                errors.append(f"{sid}: invalid {field}")
        available_at = parse_date(row.get("available_at"))
        published_at = parse_date(row.get("published_at"))
        period_end = parse_date(row.get("period_end"))
        if available_at is not None and published_at is not None and utc(available_at) < utc(published_at):
            errors.append(f"{sid}: available_at cannot precede published_at")
        lag_days = finite_number(row.get("lag_days"))
        if lag_days is None or not float(lag_days).is_integer():
            errors.append(f"{sid}: lag_days must be an integer calendar-day availability lag")
        elif available_at is not None and period_end is not None:
            recomputed_lag = (utc(available_at).date() - utc(period_end).date()).days
            if int(lag_days) != recomputed_lag:
                errors.append(
                    f"{sid}: lag_days {int(lag_days)} does not equal period_end-to-available_at lag {recomputed_lag}"
                )
        source = str(row.get("source_id") or "").strip()
        if source and source not in source_ids:
            errors.append(f"{sid}: unknown source_id {source}")
        if source and source not in eligible_source_ids:
            errors.append(f"{sid}: source_id {source} is rejected or ineligible")
        provenance = provenance_graph.get(source)
        original_source = str(row.get("original_source_id") or "").strip()
        if original_source and original_source not in source_ids:
            errors.append(f"{sid}: unknown original_source_id {original_source}")
        if provenance is not None:
            if original_source != provenance.root_original_source_id:
                errors.append(
                    f"{sid}: original_source_id must equal resolved root original "
                    f"{provenance.root_original_source_id}"
                )
            if str(row.get("independence_cluster") or "").strip() != provenance.independence_cluster:
                errors.append(f"{sid}: independence_cluster does not match source provenance")
            if canonical_basis(row.get("measurement_method_id")) != provenance.measurement_method_id:
                errors.append(f"{sid}: measurement_method_id does not match source provenance")
        node_ids = split_ids(row.get("driver_node_ids"))
        unknown_nodes = sorted(node_ids - set(graph_nodes))
        if unknown_nodes:
            errors.append(f"{sid}: unknown driver nodes " + ", ".join(unknown_nodes))
        status = str(row.get("status") or "").strip().lower()
        if status not in ALLOWED_STATUS:
            errors.append(f"{sid}: invalid status {status or '<blank>'}")

        critical = str(row.get("conclusion_critical") or "").strip().lower() in {"true", "1", "yes"}
        if strict and critical and status != "accepted":
            errors.append(
                f"{sid}: conclusion-critical series cannot be {status or '<blank>'} in strict mode"
            )
        if status == "accepted":
            for field in (
                "metric_name", "metric_construct_id", "independence_cluster", "measurement_method_id",
                "metric_definition", "entity_scope", "product_scope", "geography_scope",
                "population_coverage", "revision_policy", "known_bias",
            ):
                if not meaningful(row.get(field)):
                    errors.append(f"{sid}: accepted series needs substantive {field}")
        if status != "human_required" and finite_number(row.get("observation_value")) is None:
            errors.append(f"{sid}: observation_value must be finite for a usable quantitative observation")
        observation_type = str(row.get("observation_type") or "").strip().lower()
        if observation_type not in OBSERVATION_TYPES:
            errors.append(f"{sid}: invalid observation_type {observation_type or '<blank>'}")
        checks = split_ids(row.get("cross_check_series_ids"))
        bridges = parse_bridge_map(row.get("cross_check_bridge_json"), sid, errors)
        cross_check_result = row.get("cross_check_result")
        claims_cross_check = bool(
            checks
            or meaningful(cross_check_result)
            or meaningful(row.get("cross_check_bridge_json"))
        )
        if claims_cross_check:
            if not checks:
                errors.append(
                    f"{sid}: cross-check claim needs at least one bound cross_check_series_id"
                )
            if not meaningful(cross_check_result):
                errors.append(f"{sid}: cross-check claim needs a substantive cross_check_result")
            orphan_bridges = sorted(set(bridges) - checks)
            if orphan_bridges:
                errors.append(
                    f"{sid}: cross-check bridge has no declared series id: "
                    + ", ".join(orphan_bridges)
                )
        for check_id in sorted(checks):
            other = by_id.get(check_id)
            if other is None:
                errors.append(f"{sid}: unknown cross-check series {check_id}")
                continue
            if str(other.get("status") or "").strip().lower() != "accepted":
                errors.append(f"{sid}: cross-check {check_id} is not an accepted measurement")
            errors.extend(
                independence_problems(
                    str(row.get("source_id") or "").strip(),
                    str(other.get("source_id") or "").strip(),
                    provenance_graph,
                    label=f"{sid}: cross-check {check_id}",
                )
            )
            mismatches = [
                field
                for field in COMPARABILITY_FIELDS
                if canonical_basis(other.get(field)) != canonical_basis(row.get(field))
            ]
            if mismatches:
                bridge = bridges.get(check_id)
                if bridge is None:
                    errors.append(
                        f"{sid}: cross-check {check_id} is not comparable on "
                        + ", ".join(mismatches)
                        + "; a quantified basis bridge is required"
                    )
                else:
                    errors.extend(
                        validate_quantified_bridge(
                            sid, check_id, row, other, bridge, mismatches,
                            source_ids, eligible_source_ids,
                        )
                    )

        if status in {"scenario_only", "monitoring", "human_required"} and str(row.get("allowed_model_use") or "").lower() not in LIMITED_USE:
            errors.append(f"{sid}: limited status cannot support {row.get('allowed_model_use')}")

    for sid, row in by_id.items():
        predecessor_id = str(row.get("revision_of_series_id") or "").strip()
        if predecessor_id.lower() in {"", "none", "n/a", "na"}:
            continue
        if predecessor_id == sid:
            errors.append(f"{sid}: revision_of_series_id cannot reference itself")
            continue
        predecessor = by_id.get(predecessor_id)
        if predecessor is None:
            errors.append(f"{sid}: revision_of_series_id {predecessor_id} is unknown")
            continue
        for field in (
            "metric_construct_id", "unit", "currency", "entity_scope", "product_scope",
            "geography_scope", "period_start", "period_end",
        ):
            if canonical_basis(row.get(field)) != canonical_basis(predecessor.get(field)):
                errors.append(f"{sid}: revision_of_series_id changes {field}; use a new construct or basis bridge")
        current_available = parse_date(row.get("available_at"))
        predecessor_available = parse_date(predecessor.get("available_at"))
        if (
            current_available is not None
            and predecessor_available is not None
            and utc(current_available) <= utc(predecessor_available)
        ):
            errors.append(f"{sid}: revised observation must become available after its predecessor")

    for node_id, node in graph_nodes.items():
        declared = {str(item) for item in (node.get("data_series_ids") or []) if str(item).strip()}
        if str(node.get("kind") or "") == "observable" and not declared:
            errors.append(f"observable node {node_id} has no data_series_ids")
        unknown = sorted(declared - set(by_id))
        if unknown:
            errors.append(f"node {node_id} references unknown data series: " + ", ".join(unknown))

    if strict:
        main_line = graph.get("main_line")
        carriers = {
            str(item).strip()
            for item in ((main_line or {}).get("carrier_node_ids") or [])
            if str(item).strip()
        }
        if not carriers:
            errors.append("strict data-series validation requires model_graph main-line carrier nodes")
        for carrier in sorted(carriers):
            relevant_nodes = upstream_nodes(graph, carrier)
            supported = False
            for row in active:
                if str(row.get("status") or "").strip().lower() != "accepted":
                    continue
                critical = str(row.get("conclusion_critical") or "").strip().lower() in {
                    "true", "1", "yes",
                }
                if critical and split_ids(row.get("driver_node_ids")) & relevant_nodes:
                    supported = True
                    break
            if not supported:
                errors.append(
                    f"main-line carrier {carrier} has no accepted conclusion-critical "
                    "measurement on the carrier or a declared causal upstream node"
                )
    return errors


def validate_facts(
    rows: list[dict[str, str]],
    source_ids: set[str],
    strict: bool,
) -> list[str]:
    errors: list[str] = []
    active = [row for row in rows if substantive(row.get("fact_id"))]
    if not active:
        return ["no substantive financial fact rows"]
    ids = [str(row.get("fact_id") or "").strip() for row in active]
    known = set(ids)
    if len(known) != len(ids):
        errors.append("duplicate financial fact ids")
    required = {
        "entity_id", "source_id", "accession_or_filing_id", "filed_at", "retrieved_at",
        "form", "fiscal_year", "fiscal_period", "period_start", "period_end",
        "fact_name", "taxonomy", "tag", "dimensions", "unit", "decimals", "scale", "sign",
        "reported_value", "normalized_value", "currency", "statement_or_note_anchor",
        "extraction_method", "amendment_or_restatement", "comparability_adjustment", "status",
    }
    for row in active:
        fid = str(row.get("fact_id") or "UNKNOWN").strip()
        label = f"financial fact {fid}"
        missing = sorted(field for field in required if not substantive(row.get(field)))
        if missing:
            errors.append(f"{label}: missing " + ", ".join(missing))
        source = str(row.get("source_id") or "").strip()
        if source and source not in source_ids:
            errors.append(f"{label}: unknown source_id {source}")
        date_fields = ["filed_at", "retrieved_at", "period_start", "period_end"]
        for field in date_fields:
            if parse_date(row.get(field)) is None:
                errors.append(f"{label}: invalid {field}")
        for field in ("reported_value", "normalized_value"):
            try:
                value = float(str(row.get(field) or "").strip())
            except Exception:
                value = float("nan")
            if value != value or value in {float("inf"), float("-inf")}:
                errors.append(f"{label}: {field} must be finite numeric")
        for field in (
            "entity_id", "accession_or_filing_id", "form", "fiscal_year", "fiscal_period",
            "fact_name", "taxonomy", "tag", "unit", "currency",
            "statement_or_note_anchor", "extraction_method",
        ):
            if not meaningful(row.get(field)):
                errors.append(f"{label}: substantive {field} required")
        status = str(row.get("status") or "").strip().lower()
        if status not in FACT_STATUS:
            errors.append(f"{label}: invalid status {status or '<blank>'}")
        elif strict and status != "accepted":
            errors.append(f"{label}: unresolved fact cannot pass strict mode")
        filed = parse_date(row.get("filed_at"))
        predecessor = str(row.get("predecessor_fact_id") or "").strip()
        amended = str(row.get("amendment_or_restatement") or "").strip().lower()
        if amended not in {"none", "original", "false", "no"} and not predecessor:
            errors.append(f"{label}: amendment/restatement needs predecessor_fact_id")
        if predecessor and predecessor not in known:
            errors.append(f"{label}: unknown predecessor_fact_id {predecessor}")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--register", required=True, type=Path)
    parser.add_argument("--sources", required=True, type=Path)
    parser.add_argument("--graph", required=True, type=Path)
    parser.add_argument("--manifest", required=True, type=Path)
    parser.add_argument("--independence-map", required=True, type=Path)
    parser.add_argument("--facts", type=Path)
    parser.add_argument("--strict", action="store_true")
    args = parser.parse_args()
    errors: list[str] = []
    try:
        sources = json.loads(args.sources.read_text(encoding="utf-8"))
        graph = json.loads(args.graph.read_text(encoding="utf-8"))
        manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
        recorded_at = parse_date(manifest.get("as_of"))
        if recorded_at is None:
            errors.append("run_manifest.as_of must be a valid snapshot timestamp")
        source_rows = [item for item in sources.get("sources", []) if isinstance(item, dict)]
        for source in source_rows:
            errors.extend(source_epistemic_class_problems(source))
        source_ids = {str(item.get("source_id")) for item in source_rows}
        eligible_source_ids = {
            str(item.get("source_id"))
            for item in source_rows
            if str(item.get("decision_status") or "accepted").strip().lower()
            not in {"rejected", "not_material"}
        }
        provenance_graph, provenance_errors = build_provenance_graph(
            source_rows,
            read_independence_map(args.independence_map),
            strict=args.strict,
        )
        errors.extend(provenance_errors)
        rows = read_csv(args.register)
        errors.extend(
            validate_series(
                rows, source_ids, eligible_source_ids, provenance_graph,
                graph, args.strict
            )
        )
        if args.facts is not None:
            errors.extend(validate_facts(read_csv(args.facts), source_ids, args.strict))
    except Exception as exc:
        errors.append(str(exc))
    result = {"valid": not errors, "strict": args.strict, "errors": errors}
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if not errors else 2


if __name__ == "__main__":
    raise SystemExit(main())
