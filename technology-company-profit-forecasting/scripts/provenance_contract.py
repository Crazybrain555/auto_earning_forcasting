#!/usr/bin/env python3
"""Shared ingest-time provenance graph and structured numeric bridge contract."""
from __future__ import annotations

import csv
import hashlib
import json
import math
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable


UNKNOWN = {"", "unknown", "tbd", "pending", "n/a", "na", "none", "not provided"}
CONTROLLED_BRIDGE_OPERATIONS = {"identity", "additive", "scale_then_add"}
CONTROLLED_ADJUSTMENT_OPERATIONS = {"add", "subtract"}
SOURCE_EPISTEMIC_CLASSES = (
    "official_reported_fact",
    "independent_external_observation",
    "management_statement_or_plan",
    "expert_or_analyst_opinion",
    "technical_evidence",
    "discovery_only",
)
SOURCE_ORIGIN_RECORD_KINDS = (
    "entity_primary_disclosure",
    "public_authority_primary_record",
    "original_measurement_observation",
    "scholarly_or_engineering_record",
    "expert_or_analyst_interpretation",
    "secondary_discovery_material",
)
ORIGIN_KIND_EPISTEMIC_PERMISSIONS = {
    "entity_primary_disclosure": frozenset({
        "official_reported_fact", "management_statement_or_plan", "discovery_only",
    }),
    "public_authority_primary_record": frozenset({
        "official_reported_fact", "discovery_only",
    }),
    "original_measurement_observation": frozenset({
        "independent_external_observation", "discovery_only",
    }),
    "scholarly_or_engineering_record": frozenset({
        "technical_evidence", "expert_or_analyst_opinion", "discovery_only",
    }),
    "expert_or_analyst_interpretation": frozenset({
        "expert_or_analyst_opinion", "discovery_only",
    }),
    "secondary_discovery_material": frozenset({"discovery_only"}),
}


def canonical_text(value: object) -> str:
    return " ".join(str(value or "").strip().casefold().split())


def _canonical_fingerprint_value(value: object) -> object:
    """Normalize storage representations without dropping semantic content."""

    if isinstance(value, dict):
        normalized: dict[str, object] = {}
        for raw_key, raw_value in value.items():
            key = str(raw_key).strip()
            if key in normalized:
                raise ValueError(f"duplicate canonical key {key!r}")
            normalized[key] = _canonical_fingerprint_value(raw_value)
        return normalized
    if isinstance(value, (list, tuple)):
        return [_canonical_fingerprint_value(item) for item in value]
    if isinstance(value, str):
        return value.replace("\r\n", "\n").replace("\r", "\n").strip()
    if value is None or isinstance(value, (bool, int, float)):
        return value
    return str(value).strip()


def canonical_observation_fingerprint(observation: dict[str, object]) -> str:
    """Fingerprint every authored observation field after minimal normalization.

    The data-series contract is extensible, so an allow-list would silently
    exclude newly added semantics.  Hashing the complete normalized mapping
    makes any material row change invalidate a frozen authority judgment while
    ignoring only storage trivia such as line endings and outer whitespace.
    """

    payload = _canonical_fingerprint_value(observation)
    return "sha256:" + hashlib.sha256(
        json.dumps(
            payload,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
        ).encode("utf-8")
    ).hexdigest()


def substantive(value: object) -> bool:
    return canonical_text(value) not in UNKNOWN


def finite_number(value: object) -> float | None:
    if isinstance(value, bool):
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if math.isfinite(number) else None


def id_set(value: object) -> set[str]:
    if isinstance(value, list):
        return {str(item).strip() for item in value if str(item).strip()}
    return {
        item.strip()
        for item in re.split(r"[;,|]", str(value or ""))
        if item.strip()
    }


def author_set(value: object) -> frozenset[str]:
    if isinstance(value, list):
        values = value
    else:
        values = re.split(r"[;|]", str(value or ""))
    return frozenset(canonical_text(item) for item in values if substantive(item))


def parsed_bool(value: object) -> bool | None:
    if isinstance(value, bool):
        return value
    text = canonical_text(value)
    if text in {"true", "yes", "1"}:
        return True
    if text in {"false", "no", "0"}:
        return False
    return None


def _controlled_slug(value: object) -> str:
    return re.sub(r"[^a-z0-9]+", "_", canonical_text(value)).strip("_")


def source_epistemic_class(source: dict[str, object]) -> str:
    """Return the controlled SourceRecord epistemic class.

    ``source_type`` and ``role`` are deliberately excluded: they describe
    retrieval and workflow routing, not what a proposition is allowed to prove.
    """

    return _controlled_slug(source.get("epistemic_class"))


def source_origin_record_kind(source: dict[str, object]) -> str:
    """Return the controlled affirmative origin-record kind.

    Unlike free-form retrieval metadata, this is a permission ceiling.  It can
    only narrow an epistemic class; no genre, role or publisher label can
    promote a source into an original observation.
    """

    return _controlled_slug(source.get("origin_record_kind"))


def source_epistemic_class_problems(
    source: dict[str, object],
    *,
    label: str | None = None,
) -> list[str]:
    """Validate an explicit epistemic class against its objective provenance.

    This is a type-and-lineage check, not a judgment that the source was copied
    faithfully.  In particular, an opinion document cannot become an external
    observation by changing its free-form source type.  Its underlying measured
    fact must be represented as a separate original SourceRecord.
    """

    source_id = str(source.get("source_id") or "UNKNOWN").strip()
    prefix = label or f"source {source_id}"
    epistemic_class = source_epistemic_class(source)
    if epistemic_class not in SOURCE_EPISTEMIC_CLASSES:
        return [
            f"{prefix}: epistemic_class must be one of "
            + ", ".join(SOURCE_EPISTEMIC_CLASSES)
            + "; source_type and role do not grant epistemic authority"
        ]

    origin_record_kind = source_origin_record_kind(source)
    if origin_record_kind not in SOURCE_ORIGIN_RECORD_KINDS:
        return [
            f"{prefix}: origin_record_kind must be one of "
            + ", ".join(SOURCE_ORIGIN_RECORD_KINDS)
            + "; free-form source_type and role cannot create an original observation"
        ]
    if epistemic_class not in ORIGIN_KIND_EPISTEMIC_PERMISSIONS[origin_record_kind]:
        return [
            f"{prefix}: epistemic_class={epistemic_class} exceeds the permission ceiling "
            f"of origin_record_kind={origin_record_kind}; represent the underlying original "
            "measurement as a separate observation instead of relabeling commentary"
        ]

    authority = _controlled_slug(source.get("authority"))
    independence = _controlled_slug(source.get("independence"))
    directness = _controlled_slug(source.get("directness"))
    problems: list[str] = []

    if epistemic_class == "official_reported_fact":
        if authority not in {"audited_filing", "regulator"}:
            problems.append(
                f"{prefix}: official_reported_fact requires audited_filing or regulator authority"
            )
        if directness != "direct":
            problems.append(f"{prefix}: official_reported_fact must be direct")
    elif epistemic_class == "independent_external_observation":
        if authority not in {"third_party", "regulator"}:
            problems.append(
                f"{prefix}: independent_external_observation requires third_party or regulator authority"
            )
        if independence != "independent":
            problems.append(
                f"{prefix}: independent_external_observation requires independence=independent"
            )
        if directness != "direct":
            problems.append(
                f"{prefix}: independent_external_observation must be a direct observation"
            )
        root_id = str(source.get("root_original_source_id") or "").strip()
        parent_id = str(source.get("derived_from_source_id") or "").strip()
        common_origin = parsed_bool(source.get("common_origin"))
        if (
            root_id != source_id
            or parent_id
            or common_origin is not False
            or not substantive(source.get("measurement_method_id"))
        ):
            problems.append(
                f"{prefix}: independent_external_observation must be a separate original "
                "root record with a declared measurement_method_id; an expert or analyst "
                "summary must link the underlying observation instead of self-declaring factual"
            )
    elif epistemic_class == "management_statement_or_plan":
        if authority != "company" or independence not in {"first_party", "firstparty"}:
            problems.append(
                f"{prefix}: management_statement_or_plan requires company authority and "
                "first_party independence"
            )
    elif epistemic_class == "expert_or_analyst_opinion":
        if authority != "third_party":
            problems.append(
                f"{prefix}: expert_or_analyst_opinion requires third_party authority"
            )
    elif epistemic_class == "technical_evidence":
        if authority not in {
            "standard", "peer_reviewed", "regulator", "company", "third_party"
        }:
            problems.append(
                f"{prefix}: technical_evidence has incompatible authority {authority or '<blank>'}"
            )

    return problems


def read_independence_map(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


@dataclass(frozen=True)
class ProvenanceNode:
    source_id: str
    root_original_source_id: str
    derived_from_source_id: str
    common_origin: bool
    independence_cluster: str
    publisher: str
    authors: frozenset[str]
    measurement_method_id: str
    source_type: str


def build_provenance_graph(
    source_records: Iterable[dict[str, object]],
    independence_rows: Iterable[dict[str, object]] | None,
    *,
    strict: bool,
) -> tuple[dict[str, ProvenanceNode], list[str]]:
    """Resolve each source to one immutable root and reconcile the ingest map."""

    errors: list[str] = []
    records: dict[str, dict[str, object]] = {}
    for index, record in enumerate(source_records, 1):
        if not isinstance(record, dict):
            errors.append(f"source provenance row {index} must be an object")
            continue
        source_id = str(record.get("source_id") or "").strip()
        if not source_id:
            errors.append(f"source provenance row {index} has no source_id")
            continue
        if source_id in records:
            errors.append(f"duplicate source provenance id {source_id}")
            continue
        records[source_id] = record

    roots: dict[str, str] = {}
    visiting: set[str] = set()

    def resolve_root(source_id: str) -> str:
        if source_id in roots:
            return roots[source_id]
        if source_id in visiting:
            errors.append(f"source provenance cycle includes {source_id}")
            return source_id
        visiting.add(source_id)
        record = records[source_id]
        parent = str(record.get("derived_from_source_id") or "").strip()
        if not parent:
            root = source_id
        elif parent not in records:
            errors.append(f"source {source_id}: unknown derived_from_source_id {parent}")
            root = source_id
        else:
            root = resolve_root(parent)
        visiting.discard(source_id)
        roots[source_id] = root
        return root

    graph: dict[str, ProvenanceNode] = {}
    for source_id, record in records.items():
        root = resolve_root(source_id)
        declared_root = str(record.get("root_original_source_id") or "").strip()
        parent = str(record.get("derived_from_source_id") or "").strip()
        common_origin = parsed_bool(record.get("common_origin"))
        cluster = str(record.get("independence_cluster") or "").strip()
        publisher = canonical_text(record.get("publisher"))
        authors = author_set(record.get("authors"))
        method = canonical_text(record.get("measurement_method_id"))
        if strict:
            for field, value in (
                ("root_original_source_id", declared_root),
                ("independence_cluster", cluster),
                ("publisher", publisher),
                ("authors", authors),
                ("measurement_method_id", method),
            ):
                if not value:
                    errors.append(f"source {source_id}: missing provenance field {field}")
            if "derived_from_source_id" not in record:
                errors.append(f"source {source_id}: derived_from_source_id must be explicit (null for a root)")
            if common_origin is None:
                errors.append(f"source {source_id}: common_origin must be boolean")
        if declared_root and declared_root != root:
            errors.append(
                f"source {source_id}: declared root_original_source_id {declared_root} "
                f"does not match resolved root {root}"
            )
        if parent and common_origin is not True:
            errors.append(f"source {source_id}: a derived source must declare common_origin=true")
        if not parent and common_origin is True:
            errors.append(f"source {source_id}: a root source cannot declare common_origin=true")
        graph[source_id] = ProvenanceNode(
            source_id=source_id,
            root_original_source_id=root,
            derived_from_source_id=parent,
            common_origin=bool(common_origin),
            independence_cluster=cluster,
            publisher=publisher,
            authors=authors,
            measurement_method_id=method,
            source_type=canonical_text(record.get("source_type")),
        )

    clusters_by_root: dict[str, set[str]] = {}
    for node in graph.values():
        if node.independence_cluster:
            clusters_by_root.setdefault(node.root_original_source_id, set()).add(
                node.independence_cluster
            )
    for root, clusters in clusters_by_root.items():
        if len(clusters) > 1:
            errors.append(
                f"root original source {root} is assigned multiple independence clusters: "
                + ", ".join(sorted(clusters))
            )

    map_rows = list(independence_rows or [])
    if strict and not map_rows:
        errors.append("source_independence_map.csv has no provenance rows")
        return graph, errors
    mapped: dict[str, dict[str, object]] = {}
    for index, row in enumerate(map_rows, 1):
        source_id = str(row.get("source_id") or "").strip()
        if not source_id:
            errors.append(f"source independence map row {index} has no source_id")
            continue
        if source_id in mapped:
            errors.append(f"source independence map duplicates source_id {source_id}")
            continue
        mapped[source_id] = row
        node = graph.get(source_id)
        if node is None:
            errors.append(f"source independence map references unknown source_id {source_id}")
            continue
        comparisons = {
            "cluster_id": (str(row.get("cluster_id") or "").strip(), node.independence_cluster),
            "root_original_source_id": (
                str(row.get("root_original_source_id") or "").strip(),
                node.root_original_source_id,
            ),
            "derived_from_source_id": (
                str(row.get("derived_from_source_id") or "").strip(),
                node.derived_from_source_id,
            ),
            "publisher": (canonical_text(row.get("publisher")), node.publisher),
            "measurement_method_id": (
                canonical_text(row.get("measurement_method_id")),
                node.measurement_method_id,
            ),
        }
        for field, (mapped_value, source_value) in comparisons.items():
            if mapped_value != source_value:
                errors.append(
                    f"source {source_id}: independence map {field} does not match source manifest"
                )
        if author_set(row.get("authors")) != node.authors:
            errors.append(f"source {source_id}: independence map authors do not match source manifest")
        mapped_common = parsed_bool(row.get("common_origin"))
        if mapped_common is None or mapped_common != node.common_origin:
            errors.append(
                f"source {source_id}: independence map common_origin does not match source manifest"
            )
    if strict:
        missing = sorted(set(graph) - set(mapped))
        if missing:
            errors.append("source independence map is missing source_ids: " + ", ".join(missing))
    return graph, errors


def independence_problems(
    primary_source_id: str,
    corroborating_source_id: str,
    graph: dict[str, ProvenanceNode],
    *,
    label: str,
) -> list[str]:
    """Require independent root, originator/team and measurement method."""

    primary = graph.get(primary_source_id)
    other = graph.get(corroborating_source_id)
    if primary is None or other is None:
        missing = primary_source_id if primary is None else corroborating_source_id
        return [f"{label}: unknown provenance source {missing}"]
    errors: list[str] = []
    if primary.root_original_source_id == other.root_original_source_id:
        errors.append(
            f"{label}: sources share root original {primary.root_original_source_id} and are common origin"
        )
    if primary.independence_cluster == other.independence_cluster:
        errors.append(f"{label}: sources share independence cluster")
    if primary.publisher == other.publisher:
        errors.append(f"{label}: sources share publisher/originating organization")
    if not primary.authors or not other.authors:
        errors.append(f"{label}: source author/experimental-team provenance is incomplete")
    elif primary.authors & other.authors:
        errors.append(f"{label}: sources share authors or experimental team")
    if primary.measurement_method_id == other.measurement_method_id:
        errors.append(f"{label}: sources share measurement method")
    return errors


def validate_structured_numeric_bridge(
    payload: object,
    *,
    label: str,
    known_source_ids: set[str],
    eligible_source_ids: set[str] | None = None,
    expected_source_ids: set[str] | None = None,
    expected_target_ids: set[str] | None = None,
    expected_source_unit: str | None = None,
    expected_target_unit: str | None = None,
) -> list[str]:
    """Recompute a controlled source→adjustments→target bridge and residual."""

    if not isinstance(payload, dict):
        return [
            f"{label} must be a structured numeric bridge object; narrative formula is not executable"
        ]
    errors: list[str] = []
    if substantive(payload.get("formula")):
        errors.append(f"{label} narrative formula is forbidden; use a controlled operation")
    operation = canonical_text(payload.get("operation"))
    if operation not in CONTROLLED_BRIDGE_OPERATIONS:
        errors.append(
            f"{label} operation must be one of "
            + ", ".join(sorted(CONTROLLED_BRIDGE_OPERATIONS))
        )
    source_value = finite_number(payload.get("source_value"))
    bridged_value = finite_number(payload.get("bridged_value"))
    target_value = finite_number(payload.get("target_value"))
    residual_value = finite_number(payload.get("residual_value"))
    for field, value in (
        ("source_value", source_value),
        ("bridged_value", bridged_value),
        ("target_value", target_value),
        ("residual_value", residual_value),
    ):
        if value is None:
            errors.append(f"{label} {field} must be finite numeric")
    for field in ("source_unit", "target_unit"):
        if not substantive(payload.get(field)):
            errors.append(f"{label} {field} is required")
    if expected_source_unit is not None and canonical_text(
        payload.get("source_unit")
    ) != canonical_text(expected_source_unit):
        errors.append(f"{label} source_unit does not match the source observation")
    if expected_target_unit is not None and canonical_text(
        payload.get("target_unit")
    ) != canonical_text(expected_target_unit):
        errors.append(f"{label} target_unit does not match the target observation")

    source_ids = id_set(payload.get("source_source_ids"))
    target_ids = id_set(payload.get("target_source_ids"))
    if not source_ids:
        errors.append(f"{label} source_source_ids is required")
    if not target_ids:
        errors.append(f"{label} target_source_ids is required")
    unknown = sorted((source_ids | target_ids) - known_source_ids)
    if unknown:
        errors.append(f"{label} has unknown endpoint source_ids: " + ", ".join(unknown))
    if eligible_source_ids is not None:
        ineligible = sorted((source_ids | target_ids) - eligible_source_ids)
        if ineligible:
            errors.append(
                f"{label} has rejected/ineligible endpoint source_ids: "
                + ", ".join(ineligible)
            )
    if expected_source_ids is not None and source_ids != expected_source_ids:
        errors.append(f"{label} source_source_ids do not match the input observation")
    if expected_target_ids is not None and target_ids != expected_target_ids:
        errors.append(f"{label} target_source_ids do not match the target observation")

    adjustments = payload.get("adjustments")
    if not isinstance(adjustments, list):
        errors.append(f"{label} adjustments must be an array")
        adjustments = []
    computed = source_value
    if operation == "scale_then_add":
        scale = finite_number(payload.get("scale"))
        if scale is None:
            errors.append(f"{label} scale_then_add requires a finite scale")
            computed = None
        elif computed is not None:
            computed *= scale
    elif operation == "identity" and adjustments:
        errors.append(f"{label} identity operation cannot carry adjustments")

    for index, adjustment in enumerate(adjustments, 1):
        item_label = f"{label} adjustment[{index}]"
        if not isinstance(adjustment, dict):
            errors.append(f"{item_label} must be an object")
            computed = None
            continue
        if not substantive(adjustment.get("adjustment_id")):
            errors.append(f"{item_label} adjustment_id is required")
        adjustment_operation = canonical_text(adjustment.get("operation"))
        if adjustment_operation not in CONTROLLED_ADJUSTMENT_OPERATIONS:
            errors.append(f"{item_label} operation must be add or subtract")
        value = finite_number(adjustment.get("value"))
        if value is None:
            errors.append(f"{item_label} value must be finite numeric")
            computed = None
        adjustment_sources = id_set(adjustment.get("source_ids"))
        if not adjustment_sources:
            errors.append(f"{item_label} source_ids is required")
        unknown_adjustment_sources = sorted(adjustment_sources - known_source_ids)
        if unknown_adjustment_sources:
            errors.append(
                f"{item_label} has unknown source_ids: "
                + ", ".join(unknown_adjustment_sources)
            )
        if eligible_source_ids is not None:
            ineligible_adjustment_sources = sorted(
                adjustment_sources - eligible_source_ids
            )
            if ineligible_adjustment_sources:
                errors.append(
                    f"{item_label} has rejected/ineligible source_ids: "
                    + ", ".join(ineligible_adjustment_sources)
                )
        if computed is not None and value is not None:
            if adjustment_operation == "add":
                computed += value
            elif adjustment_operation == "subtract":
                computed -= value

    if computed is not None and bridged_value is not None and not math.isclose(
        computed, bridged_value, rel_tol=1e-9, abs_tol=1e-9
    ):
        errors.append(
            f"{label} bridged_value is not recomputable: expected {computed:g}, "
            f"got {bridged_value:g}"
        )

    residual_unit = canonical_text(payload.get("residual_unit"))
    if residual_unit not in {"absolute", "percent"}:
        errors.append(f"{label} residual_unit must be absolute or percent")
    if bridged_value is not None and target_value is not None and residual_value is not None:
        if residual_unit == "absolute":
            expected_residual = bridged_value - target_value
        elif residual_unit == "percent" and target_value != 0:
            expected_residual = (bridged_value - target_value) / abs(target_value) * 100.0
        elif residual_unit == "percent":
            errors.append(f"{label} percent residual is undefined when target_value is zero")
            expected_residual = None
        else:
            expected_residual = None
        if expected_residual is not None and not math.isclose(
            expected_residual, residual_value, rel_tol=1e-9, abs_tol=1e-9
        ):
            errors.append(
                f"{label} residual_value is not recomputable: expected "
                f"{expected_residual:g}, got {residual_value:g}"
            )
    return errors
