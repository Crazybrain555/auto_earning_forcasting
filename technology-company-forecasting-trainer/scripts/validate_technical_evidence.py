#!/usr/bin/env python3
"""Validate proposition-level technical evidence and its narrowly allowed model use.

This is deliberately not a literature manager.  Its only job is to stop a
paper citation from silently becoming a factory-yield, adoption, or revenue
assumption.  A record may support a technical parameter, bound, scenario, or
monitor; commercialization always requires separate operating evidence.
"""
from __future__ import annotations

import argparse
import csv
import datetime as dt
import json
import re
from pathlib import Path
from typing import Any

from equation_contract import strict_finite_number
from provenance_contract import (
    ProvenanceNode,
    build_provenance_graph,
    independence_problems,
    read_independence_map,
    source_epistemic_class,
    source_epistemic_class_problems,
    validate_structured_numeric_bridge,
)
from scenario_contract import parse_scenario_catalog


UNKNOWN = {"", "unknown", "tbd", "pending", "n/a", "na", "none", "not provided"}
MODEL_USES = {"base_technical_parameter", "technical_bound", "scenario_only", "monitoring"}
ALLOWED_USES = MODEL_USES | {"background", "rejected", "human_required"}
EVIDENCE_DESIGNS = {
    "experimental", "observational", "theoretical", "methods",
    "review_or_meta_analysis", "standard_or_specification",
}
EMPIRICAL_DESIGNS = {"experimental", "observational"}
NON_EMPIRICAL_DESIGNS = EVIDENCE_DESIGNS - EMPIRICAL_DESIGNS
APPLICABILITY = {"applicable", "not_applicable", "unknown"}
SCHOLARLY_STATUSES = {
    "current", "corrected_current", "expression_of_concern", "retracted", "withdrawn", "unknown",
}
RESTRICTED_STATUSES = {"expression_of_concern", "retracted", "withdrawn"}
AVAILABILITY = {"available", "restricted", "not_available", "unknown"}
REPRODUCIBILITY = {"reproduced", "partially_reproduced", "failed", "not_attempted", "not_applicable"}
REPLICATION = {"replicated", "partially_replicated", "failed", "not_found", "not_checked", "not_applicable"}
TRANSFER = {
    "matched_with_quantified_bridge", "mismatch_scenario_only", "laboratory_only",
    "production_evidence_missing", "not_applicable",
}
DOI_RE = re.compile(r"^10\.\d{4,9}/\S+$", re.I)

REQUIRED_TEXT = (
    "schema_version", "record_id", "technology_or_product", "source_id", "stable_identifier",
    "version", "publication_status", "scholarly_record_status", "status_checked_at",
    "evidence_design", "exact_claim", "uncertainty",
    "data_availability", "data_location_or_reason", "code_availability",
    "code_location_or_reason", "computational_reproducibility", "independent_replication_status",
    "orthogonal_engineering_evidence", "funding", "conflicts_of_interest",
    "competing_technologies", "negative_results", "production_transfer_status",
    "production_transfer_differences", "technical_boundary",
    "allowed_use", "limitations",
)
REQUIRED_ARRAYS = (
    "status_source_ids", "reproduction_source_ids", "independent_replication_source_ids",
    "orthogonal_engineering_evidence_source_ids", "driver_node_ids", "scenario_ids",
)
CONDITIONAL_FIELDS = (
    "experimental_conditions", "sample_applicability", "sample_applicability_reason",
    "sample_description", "sample_size_value", "sample_size_unit",
    "benchmark_applicability", "benchmark_applicability_reason", "benchmark_name",
    "benchmark_version", "benchmark_result",
)


def _substantive(value: Any) -> bool:
    return str(value or "").strip().lower() not in UNKNOWN


def _split_ids(value: Any) -> set[str]:
    if isinstance(value, list):
        return {str(item).strip() for item in value if str(item).strip()}
    return {item.strip() for item in re.split(r"[;,|]", str(value or "")) if item.strip()}


def _load_json(path: Path, default: Any) -> tuple[Any, list[str]]:
    if not path.exists():
        return default, [f"missing {path.name}"]
    try:
        return json.loads(path.read_text(encoding="utf-8")), []
    except Exception as exc:
        return default, [f"invalid {path.name}: {exc}"]


def read_jsonl(path: Path) -> tuple[list[dict[str, Any]], list[str]]:
    if not path.exists():
        return [], [f"missing {path.name}"]
    records: list[dict[str, Any]] = []
    errors: list[str] = []
    for line_number, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not raw.strip():
            continue
        try:
            record = json.loads(raw)
        except Exception as exc:
            errors.append(f"{path.name}:{line_number}: invalid JSON: {exc}")
            continue
        if not isinstance(record, dict):
            errors.append(f"{path.name}:{line_number}: record must be an object")
            continue
        records.append(record)
    return records, errors


def _accepted_source(source: dict[str, Any] | None) -> bool:
    return bool(source) and str(source.get("decision_status") or "accepted").strip().lower() not in {
        "rejected", "not_material",
    }


def _iso_timestamp(value: Any) -> bool:
    try:
        text = str(value).strip().replace("Z", "+00:00")
        dt.datetime.fromisoformat(text)
        return True
    except Exception:
        return False


def validate_technical_evidence_records(
    records: list[dict[str, Any]],
    *,
    source_records: dict[str, dict[str, Any]],
    provenance_graph: dict[str, ProvenanceNode],
    known_node_ids: set[str],
    known_scenario_ids: set[str],
    technology_rows: list[dict[str, Any]],
    strict: bool = True,
) -> tuple[list[str], list[str], dict[str, Any]]:
    errors: list[str] = []
    warnings: list[str] = []
    seen_ids: set[str] = set()
    matched_keys: set[tuple[str, str]] = set()
    base_count = 0

    for index, record in enumerate(records, 1):
        record_id = str(record.get("record_id") or f"row-{index}").strip()
        label = f"technical evidence {record_id}"
        if record_id in seen_ids:
            errors.append(f"{label}: duplicate record_id")
        seen_ids.add(record_id)

        for field in REQUIRED_TEXT:
            if not _substantive(record.get(field)):
                errors.append(f"{label}: {field} must be substantive")
        for field in REQUIRED_ARRAYS:
            if field not in record or not isinstance(record.get(field), list):
                errors.append(f"{label}: {field} must be an array")
        for field in CONDITIONAL_FIELDS:
            if field not in record:
                errors.append(f"{label}: {field} must be explicitly declared")

        if record.get("schema_version") != "technical-evidence-record/v2":
            errors.append(f"{label}: schema_version must be technical-evidence-record/v2")

        evidence_design = str(record.get("evidence_design") or "").strip().lower()
        sample_applicability = str(record.get("sample_applicability") or "").strip().lower()
        benchmark_applicability = str(record.get("benchmark_applicability") or "").strip().lower()
        allowed_use = str(record.get("allowed_use") or "").strip().lower()

        if evidence_design not in EVIDENCE_DESIGNS:
            errors.append(f"{label}: invalid evidence_design {evidence_design or 'blank'}")
        if sample_applicability not in APPLICABILITY:
            errors.append(f"{label}: invalid sample_applicability {sample_applicability or 'blank'}")
        if benchmark_applicability not in APPLICABILITY:
            errors.append(f"{label}: invalid benchmark_applicability {benchmark_applicability or 'blank'}")

        if sample_applicability == "applicable":
            for field in (
                "experimental_conditions", "sample_description", "sample_size_unit",
            ):
                if not _substantive(record.get(field)):
                    errors.append(f"{label}: {field} must be substantive when sample_applicability=applicable")
            sample_size = strict_finite_number(record.get("sample_size_value"))
            if sample_size is None or sample_size <= 0:
                errors.append(
                    f"{label}: sample_size_value must be a declared positive finite JSON number "
                    "when sample_applicability=applicable"
                )
        elif sample_applicability in {"not_applicable", "unknown"}:
            if not _substantive(record.get("sample_applicability_reason")):
                errors.append(
                    f"{label}: sample_applicability_reason must explain "
                    f"sample_applicability={sample_applicability}"
                )
            if record.get("sample_size_value") is not None:
                errors.append(
                    f"{label}: sample_size_value must be null when "
                    f"sample_applicability={sample_applicability}; missing is never zero"
                )
            if sample_applicability == "not_applicable":
                for field in (
                    "experimental_conditions", "sample_description", "sample_size_unit",
                ):
                    if record.get(field) is not None:
                        errors.append(
                            f"{label}: {field} must be null when sample_applicability=not_applicable"
                        )

        if benchmark_applicability == "applicable":
            for field in ("benchmark_name", "benchmark_version", "benchmark_result"):
                if not _substantive(record.get(field)):
                    errors.append(
                        f"{label}: {field} must be substantive when benchmark_applicability=applicable"
                    )
        elif benchmark_applicability in {"not_applicable", "unknown"}:
            if not _substantive(record.get("benchmark_applicability_reason")):
                errors.append(
                    f"{label}: benchmark_applicability_reason must explain "
                    f"benchmark_applicability={benchmark_applicability}"
                )
            if benchmark_applicability == "not_applicable":
                for field in ("benchmark_name", "benchmark_version", "benchmark_result"):
                    if record.get(field) is not None:
                        errors.append(
                            f"{label}: {field} must be null when benchmark_applicability=not_applicable"
                        )

        if (
            evidence_design in EMPIRICAL_DESIGNS
            and allowed_use in MODEL_USES
            and sample_applicability != "applicable"
        ):
            errors.append(
                f"{label}: empirical model use requires sample_applicability=applicable "
                "with declared conditions and positive sample size"
            )
        if evidence_design in NON_EMPIRICAL_DESIGNS and allowed_use == "base_technical_parameter":
            errors.append(
                f"{label}: non-empirical evidence cannot itself support base_technical_parameter; "
                "use theory/boundary/background/scenario permission and separate production evidence"
            )

        doi = str(record.get("doi") or "").strip()
        if doi and not DOI_RE.match(doi):
            errors.append(f"{label}: doi is not a valid DOI")
        if not doi and (
            not _substantive(record.get("doi_unavailable_reason"))
            or not _substantive(record.get("stable_identifier"))
        ):
            errors.append(f"{label}: missing DOI requires stable_identifier and doi_unavailable_reason")
        if not _iso_timestamp(record.get("status_checked_at")):
            errors.append(f"{label}: status_checked_at must be an ISO timestamp")

        status = str(record.get("scholarly_record_status") or "").strip().lower()
        if status not in SCHOLARLY_STATUSES:
            errors.append(f"{label}: invalid scholarly_record_status {status or 'blank'}")
        if allowed_use not in ALLOWED_USES:
            errors.append(f"{label}: invalid allowed_use {allowed_use or 'blank'}")
        if status in RESTRICTED_STATUSES and allowed_use not in {"rejected", "background"}:
            qualifier = "retracted" if status == "retracted" else status
            errors.append(f"{label}: {qualifier} scholarly record is limited to rejected/background history")
        if status == "unknown" and allowed_use in {"base_technical_parameter", "technical_bound"}:
            errors.append(f"{label}: unknown scholarly status cannot support a Base parameter or bound")

        if str(record.get("data_availability") or "").lower() not in AVAILABILITY:
            errors.append(f"{label}: invalid data_availability")
        if str(record.get("code_availability") or "").lower() not in AVAILABILITY:
            errors.append(f"{label}: invalid code_availability")
        if str(record.get("computational_reproducibility") or "").lower() not in REPRODUCIBILITY:
            errors.append(f"{label}: invalid computational_reproducibility")
        replication_status = str(record.get("independent_replication_status") or "").lower()
        if replication_status not in REPLICATION:
            errors.append(f"{label}: invalid independent_replication_status")
        transfer_status = str(record.get("production_transfer_status") or "").lower()
        if transfer_status not in TRANSFER:
            errors.append(f"{label}: invalid production_transfer_status")

        source_id = str(record.get("source_id") or "").strip()
        primary = source_records.get(source_id)
        if not _accepted_source(primary):
            errors.append(f"{label}: source_id {source_id or 'blank'} is missing or not accepted")
            primary = {}
        matched_keys.add((str(record.get("technology_or_product") or "").strip(), source_id))

        all_source_fields = (
            "status_source_ids", "reproduction_source_ids", "independent_replication_source_ids",
            "orthogonal_engineering_evidence_source_ids",
        )
        for field in all_source_fields:
            for linked_source_id in _split_ids(record.get(field)):
                if not _accepted_source(source_records.get(linked_source_id)):
                    errors.append(f"{label}: {field} contains unknown or rejected source {linked_source_id}")

        replication_ids = _split_ids(record.get("independent_replication_source_ids"))
        independent_replication = bool(replication_ids) and all(
            item != source_id
            and _accepted_source(source_records.get(item))
            and not independence_problems(
                source_id,
                item,
                provenance_graph,
                label=f"{label}: independent replication {item}",
            )
            for item in replication_ids
        )
        if replication_status == "replicated" and not independent_replication:
            detail = []
            for item in sorted(replication_ids):
                detail.extend(
                    independence_problems(
                        source_id,
                        item,
                        provenance_graph,
                        label=f"{label}: independent replication {item}",
                    )
                )
            errors.append(
                f"{label}: replicated status requires a different root original, "
                "publisher/experimental team and measurement method"
                + ("; " + "; ".join(detail) if detail else "")
            )

        orthogonal_ids = _split_ids(record.get("orthogonal_engineering_evidence_source_ids"))
        orthogonal_evidence = bool(orthogonal_ids) and all(
            item != source_id
            and _accepted_source(source_records.get(item))
            and source_epistemic_class(source_records[item])
            in {"technical_evidence", "independent_external_observation"}
            and not independence_problems(
                source_id,
                item,
                provenance_graph,
                label=f"{label}: orthogonal engineering evidence {item}",
            )
            for item in orthogonal_ids
        )
        if orthogonal_ids and not orthogonal_evidence:
            errors.append(f"{label}: orthogonal engineering evidence must use an independent source and method")

        driver_ids = _split_ids(record.get("driver_node_ids"))
        scenario_ids = _split_ids(record.get("scenario_ids"))
        unknown_nodes = driver_ids - known_node_ids
        unknown_scenarios = scenario_ids - known_scenario_ids
        if unknown_nodes:
            errors.append(f"{label}: unknown driver_node_ids {sorted(unknown_nodes)}")
        if unknown_scenarios:
            errors.append(f"{label}: unknown scenario_ids {sorted(unknown_scenarios)}")
        if allowed_use in MODEL_USES and not driver_ids:
            errors.append(f"{label}: driver_node_ids must bind every model use")
        if allowed_use == "scenario_only" and not scenario_ids:
            errors.append(f"{label}: scenario_only requires scenario_ids")

        if allowed_use == "base_technical_parameter":
            base_count += 1
            if not (replication_status == "replicated" and independent_replication) and not orthogonal_evidence:
                errors.append(
                    f"{label}: single-laboratory evidence cannot support base_technical_parameter; "
                    "downgrade to technical_bound/scenario_only or add independent replication/orthogonal engineering evidence"
                )
            if transfer_status != "matched_with_quantified_bridge":
                errors.append(
                    f"{label}: base_technical_parameter requires matched_with_quantified_bridge production transfer"
                )

        transfer_bridge = record.get("production_transfer_bridge")
        if transfer_status == "matched_with_quantified_bridge":
            transfer_errors = validate_structured_numeric_bridge(
                transfer_bridge,
                label=f"{label}: production_transfer_bridge",
                known_source_ids=set(source_records),
                eligible_source_ids={
                    item for item, source in source_records.items()
                    if _accepted_source(source)
                },
                expected_source_ids={source_id},
            )
            errors.extend(transfer_errors)
            if isinstance(transfer_bridge, dict):
                for target_source_id in sorted(
                    _split_ids(transfer_bridge.get("target_source_ids"))
                ):
                    errors.extend(
                        independence_problems(
                            source_id,
                            target_source_id,
                            provenance_graph,
                            label=(
                                f"{label}: production transfer target "
                                f"{target_source_id}"
                            ),
                        )
                    )
        elif transfer_bridge not in (None, "", {}):
            errors.append(
                f"{label}: production_transfer_bridge is allowed only for "
                "matched_with_quantified_bridge"
            )

        if str(record.get("commercialization_permission") or "").strip().lower() != "none":
            errors.append(f"{label}: commercialization_permission must be none")

    # Every material paper cited by the technology register must have a
    # paper-level quality record.  The register may be less permissive, never
    # more permissive, than that record.
    use_rank = {
        "rejected": 0, "human_required": 0, "background": 0, "monitoring": 1,
        "scenario_only": 2, "technical_bound": 3, "base": 4,
        "base_parameter": 4, "base_technical_parameter": 4,
    }
    records_by_key = {
        (str(r.get("technology_or_product") or "").strip(), str(r.get("source_id") or "").strip()): r
        for r in records
    }
    material_paper_links = 0
    for row in technology_rows:
        if str(row.get("materiality") or "").strip().lower() not in {"critical", "high"}:
            continue
        technology = str(row.get("technology_or_product") or "").strip()
        row_use = str(row.get("allowed_model_use") or "background").strip().lower()
        for paper_source_id in _split_ids(row.get("paper_source_ids")):
            material_paper_links += 1
            key = (technology, paper_source_id)
            evidence = records_by_key.get(key)
            if evidence is None:
                errors.append(f"missing technical evidence record for {technology} / {paper_source_id}")
                continue
            evidence_use = str(evidence.get("allowed_use") or "background").strip().lower()
            if use_rank.get(row_use, 99) > use_rank.get(evidence_use, -1):
                errors.append(
                    f"technology-commercialization {technology}: allowed_model_use={row_use} exceeds "
                    f"paper permission={evidence_use}"
                )

    if strict and not records and material_paper_links:
        errors.append("material paper citations require technical_evidence_records.jsonl")
    metrics = {
        "technical_evidence_records": len(records),
        "material_paper_links": material_paper_links,
        "base_technical_parameter_records": base_count,
        "records_with_independent_replication": sum(
            1 for r in records if str(r.get("independent_replication_status") or "").lower() == "replicated"
        ),
        "records_with_orthogonal_engineering_evidence": sum(
            1 for r in records if _split_ids(r.get("orthogonal_engineering_evidence_source_ids"))
        ),
    }
    return errors, warnings, metrics


def validate_workspace(workspace: Path, strict: bool = True) -> tuple[list[str], list[str], dict[str, Any]]:
    records, errors = read_jsonl(workspace / "technical_evidence_records.jsonl")
    source_manifest, source_errors = _load_json(workspace / "source_manifest.json", {})
    graph, graph_errors = _load_json(workspace / "model_graph.json", {})
    scenarios, scenario_errors = _load_json(workspace / "scenario_set.json", {})
    errors.extend(source_errors + graph_errors + scenario_errors)
    technology_rows: list[dict[str, Any]] = []
    technology_path = workspace / "technology_commercialization_register.csv"
    if not technology_path.exists():
        errors.append("missing technology_commercialization_register.csv")
    else:
        try:
            with technology_path.open(encoding="utf-8-sig", newline="") as handle:
                technology_rows = list(csv.DictReader(handle))
        except Exception as exc:
            errors.append(f"invalid technology_commercialization_register.csv: {exc}")
    sources = source_manifest.get("sources", []) if isinstance(source_manifest, dict) else []
    source_records = {
        str(item.get("source_id") or "").strip(): item
        for item in sources if isinstance(item, dict) and str(item.get("source_id") or "").strip()
    }
    for source in source_records.values():
        errors.extend(source_epistemic_class_problems(source))
    known_node_ids = {
        str(item.get("id") or "").strip()
        for item in (graph.get("nodes", []) if isinstance(graph, dict) else [])
        if isinstance(item, dict) and str(item.get("id") or "").strip()
    }
    scenario_catalog, scenario_catalog_problems = parse_scenario_catalog(scenarios)
    errors.extend(
        f"scenario catalog: {problem}" for problem in scenario_catalog_problems
    )
    known_scenario_ids = (
        set(scenario_catalog.ids) if scenario_catalog is not None else set()
    )
    provenance_graph, provenance_errors = build_provenance_graph(
        source_records.values(),
        read_independence_map(workspace / "source_independence_map.csv"),
        strict=strict,
    )
    errors.extend(provenance_errors)
    validation_errors, warnings, metrics = validate_technical_evidence_records(
        records,
        source_records=source_records,
        provenance_graph=provenance_graph,
        known_node_ids=known_node_ids,
        known_scenario_ids=known_scenario_ids,
        technology_rows=technology_rows,
        strict=strict,
    )
    errors.extend(validation_errors)
    return errors, warnings, metrics


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Validate proposition-level technical evidence permissions."
    )
    parser.add_argument("--workspace", required=True)
    parser.add_argument("--strict", action="store_true")
    args = parser.parse_args()
    errors, warnings, metrics = validate_workspace(Path(args.workspace).resolve(), strict=args.strict)
    payload = {"status": "PASS" if not errors else "FAIL", "errors": errors, "warnings": warnings, "metrics": metrics}
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0 if not errors else 2


if __name__ == "__main__":
    raise SystemExit(main())
