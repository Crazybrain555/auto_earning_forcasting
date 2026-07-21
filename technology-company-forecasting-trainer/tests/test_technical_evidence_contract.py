import copy
import csv
import json
import subprocess
import sys
import tempfile
from pathlib import Path


SKILL = Path(__file__).resolve().parents[1]
VALIDATOR = SKILL / "scripts" / "validate_technical_evidence.py"


def _write_json(path: Path, payload: object) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _write_records(path: Path, records: list[dict]) -> None:
    path.write_text(
        "".join(json.dumps(record, ensure_ascii=False) + "\n" for record in records),
        encoding="utf-8",
    )


def _write_technology_register(path: Path, allowed_model_use: str = "base_parameter") -> None:
    headers = [
        "technology_or_product", "materiality", "paper_source_ids",
        "allowed_model_use", "driver_node_ids",
    ]
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=headers)
        writer.writeheader()
        writer.writerow({
            "technology_or_product": "Core accelerator",
            "materiality": "critical",
            "paper_source_ids": "PAPER1",
            "allowed_model_use": allowed_model_use,
            "driver_node_ids": "tech_yield",
        })


def _base_record() -> dict:
    return {
        "schema_version": "technical-evidence-record/v2",
        "record_id": "TE1",
        "technology_or_product": "Core accelerator",
        "source_id": "PAPER1",
        "doi": "10.1234/example.2026.1",
        "doi_unavailable_reason": "",
        "stable_identifier": "doi:10.1234/example.2026.1",
        "version": "version of record, 2026-03-01",
        "publication_status": "peer_reviewed",
        "scholarly_record_status": "current",
        "status_checked_at": "2026-07-18T00:00:00Z",
        "status_source_ids": ["PAPER1"],
        "evidence_design": "experimental",
        "exact_claim": "At 25C and the declared workload, median device yield was 92%.",
        "experimental_conditions": "25C; 1.0V; benchmark workload B; laboratory process P3.",
        "sample_applicability": "applicable",
        "sample_applicability_reason": None,
        "sample_description": "64 independently fabricated devices from four wafers.",
        "sample_size_value": 64,
        "sample_size_unit": "devices",
        "benchmark_applicability": "applicable",
        "benchmark_applicability_reason": None,
        "benchmark_name": "Benchmark B",
        "benchmark_version": "v3.2",
        "benchmark_result": "Median yield 92% versus comparator 84%.",
        "uncertainty": "95% bootstrap interval 88%-95%; wafer-cluster resampling.",
        "data_availability": "available",
        "data_location_or_reason": "https://example.org/data/TE1",
        "code_availability": "available",
        "code_location_or_reason": "https://example.org/code/TE1",
        "computational_reproducibility": "reproduced",
        "reproduction_source_ids": ["REPL1"],
        "independent_replication_status": "replicated",
        "independent_replication_source_ids": ["REPL1"],
        "orthogonal_engineering_evidence": "No separate orthogonal production test is used.",
        "orthogonal_engineering_evidence_source_ids": [],
        "funding": "University grant G1; no issuer funding.",
        "conflicts_of_interest": "Authors report no financial interest in the issuer.",
        "competing_technologies": "Comparator architecture C under the same benchmark.",
        "negative_results": "Thermal stress above 70C erased half the measured advantage.",
        "production_transfer_status": "matched_with_quantified_bridge",
        "production_transfer_differences": "Production is 60C; apply the paper's measured -0.10 yield delta.",
        "production_transfer_bridge": {
            "operation": "additive",
            "source_value": 0.92,
            "source_unit": "ratio",
            "source_source_ids": ["PAPER1"],
            "adjustments": [{
                "adjustment_id": "temperature_delta",
                "operation": "subtract",
                "value": 0.10,
                "source_ids": ["ENG1"],
            }],
            "bridged_value": 0.82,
            "target_value": 0.82,
            "target_unit": "ratio",
            "target_source_ids": ["ENG1"],
            "residual_value": 0.0,
            "residual_unit": "absolute",
        },
        "technical_boundary": "Yield only; no permission for demand, customer qualification or revenue timing.",
        "allowed_use": "base_technical_parameter",
        "driver_node_ids": ["tech_yield"],
        "scenario_ids": ["base", "bear"],
        "commercialization_permission": "none",
        "limitations": "Laboratory evidence does not establish factory yield, cost or commercial adoption.",
    }


def _non_empirical_record(evidence_design: str, allowed_use: str) -> dict:
    record = _base_record()
    record.update({
        "evidence_design": evidence_design,
        "exact_claim": (
            "Under the declared assumptions, the mechanism imposes a qualitative "
            "boundary; no measured device-performance claim is made."
        ),
        "experimental_conditions": None,
        "sample_applicability": "not_applicable",
        "sample_applicability_reason": (
            "This claim is a non-empirical derivation or research method, not a sampled estimate."
        ),
        "sample_description": None,
        "sample_size_value": None,
        "sample_size_unit": None,
        "benchmark_applicability": "not_applicable",
        "benchmark_applicability_reason": (
            "The proposition does not report a benchmark comparison."
        ),
        "benchmark_name": None,
        "benchmark_version": None,
        "benchmark_result": None,
        "uncertainty": "Validity is conditional on the stated assumptions and scope.",
        "computational_reproducibility": "not_applicable",
        "reproduction_source_ids": [],
        "independent_replication_status": "not_applicable",
        "independent_replication_source_ids": [],
        "orthogonal_engineering_evidence": "No production measurement is claimed.",
        "orthogonal_engineering_evidence_source_ids": [],
        "negative_results": "No empirical failure rate is claimed; assumption failures remain a boundary.",
        "production_transfer_status": "not_applicable",
        "production_transfer_differences": (
            "There is no measured laboratory parameter to transfer into production."
        ),
        "production_transfer_bridge": None,
        "technical_boundary": (
            "May support a theory or technical boundary only; no yield, adoption or revenue permission."
        ),
        "allowed_use": allowed_use,
        "driver_node_ids": ["tech_yield"] if allowed_use in {
            "technical_bound", "scenario_only", "monitoring", "base_technical_parameter",
        } else [],
        "scenario_ids": ["bear"] if allowed_use == "scenario_only" else [],
        "limitations": (
            "Non-empirical evidence does not establish a factory parameter or commercial outcome."
        ),
    })
    return record


def _workspace(tmp_path: Path, records: list[dict]) -> Path:
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    _write_records(workspace / "technical_evidence_records.jsonl", records)
    _write_json(workspace / "source_manifest.json", {
        "sources": [
            {
                "source_id": "PAPER1", "source_type": "technical-paper",
                "origin_record_kind": "scholarly_or_engineering_record",
                "epistemic_class": "technical_evidence",
                "decision_status": "accepted", "independence_cluster": "lab-a",
                "authority": "peer_reviewed", "independence": "first_party",
                "directness": "direct",
                "publisher": "Lab A", "authors": ["Lab A Device Team"],
                "root_original_source_id": "PAPER1", "derived_from_source_id": None,
                "common_origin": False,
                "measurement_method_id": "device-experiment",
            },
            {
                "source_id": "REPL1", "source_type": "technical-paper",
                "origin_record_kind": "scholarly_or_engineering_record",
                "epistemic_class": "technical_evidence",
                "decision_status": "accepted", "independence": "independent",
                "authority": "peer_reviewed", "directness": "direct",
                "publisher": "Lab B", "authors": ["Lab B Replication Team"],
                "root_original_source_id": "REPL1", "derived_from_source_id": None,
                "common_origin": False,
                "independence_cluster": "lab-b", "measurement_method_id": "independent-fabrication",
            },
            {
                "source_id": "ENG1", "source_type": "independent-engineering-test",
                "origin_record_kind": "scholarly_or_engineering_record",
                "epistemic_class": "technical_evidence",
                "decision_status": "accepted", "independence": "independent",
                "authority": "third_party", "directness": "direct",
                "publisher": "Customer Q", "authors": ["Customer Q Qualification Team"],
                "root_original_source_id": "ENG1", "derived_from_source_id": None,
                "common_origin": False,
                "independence_cluster": "customer-test", "measurement_method_id": "qualification-test",
            },
        ]
    })
    _write_json(workspace / "model_graph.json", {
        "nodes": [{"id": "tech_yield", "kind": "input", "unit": "ratio"}]
    })
    _write_json(workspace / "scenario_set.json", {
        "scenarios": [
            {
                "id": "base", "role": "reference", "probability": 0.6,
                "shocks": [],
            },
            {
                "id": "bear", "role": "alternative", "probability": 0.4,
                "shocks": [{"node_id": "tech_yield"}],
            },
        ]
    })
    with (workspace / "source_independence_map.csv").open(
        "w", encoding="utf-8-sig", newline=""
    ) as handle:
        writer = csv.writer(handle)
        writer.writerow([
            "source_id", "cluster_id", "root_original_source_id",
            "derived_from_source_id", "relationship", "common_origin", "publisher",
            "authors", "measurement_method_id", "independence_basis", "notes",
        ])
        writer.writerows([
            ["PAPER1", "lab-a", "PAPER1", "", "original", "false", "Lab A",
             "Lab A Device Team", "device-experiment", "original experiment", ""],
            ["REPL1", "lab-b", "REPL1", "", "original", "false", "Lab B",
             "Lab B Replication Team", "independent-fabrication", "new fabrication", ""],
            ["ENG1", "customer-test", "ENG1", "", "original", "false", "Customer Q",
             "Customer Q Qualification Team", "qualification-test", "production qualification", ""],
        ])
    evidence_use = records[0].get("allowed_use") if records else "background"
    register_use = {
        "base_technical_parameter": "base_parameter",
        "technical_bound": "technical_bound",
        "scenario_only": "scenario_only",
        "monitoring": "monitoring",
        "background": "background",
        "rejected": "background",
        "human_required": "human_required",
    }.get(str(evidence_use), "background")
    _write_technology_register(
        workspace / "technology_commercialization_register.csv",
        register_use,
    )
    return workspace


def _run(workspace: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(VALIDATOR), "--workspace", str(workspace), "--strict"],
        capture_output=True,
        text=True,
    )


def test_scaffold_creates_technical_evidence_register(tmp_path: Path) -> None:
    workspace = tmp_path / "delivery"
    result = subprocess.run(
        [
            sys.executable, str(SKILL / "scripts" / "scaffold_delivery.py"),
            "--workspace", str(workspace), "--entity", "TEST", "--as-of", "2026-07-18",
        ],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert (workspace / "technical_evidence_records.jsonl").exists()


def test_independently_replicated_paper_can_support_base_technical_parameter(tmp_path: Path) -> None:
    result = _run(_workspace(tmp_path, [_base_record()]))
    assert result.returncode == 0, result.stdout + result.stderr
    payload = json.loads(result.stdout)
    assert payload["metrics"]["base_technical_parameter_records"] == 1


def test_theoretical_and_methods_records_do_not_invent_samples_or_benchmarks(tmp_path: Path) -> None:
    cases = [
        ("theoretical", "technical_bound"),
        ("methods", "background"),
    ]
    for index, (evidence_design, allowed_use) in enumerate(cases):
        case_root = tmp_path / f"case-{index}"
        case_root.mkdir()
        result = _run(_workspace(
            case_root,
            [_non_empirical_record(evidence_design, allowed_use)],
        ))
        assert result.returncode == 0, result.stdout + result.stderr


def test_not_applicable_or_unknown_fields_require_a_specific_reason(tmp_path: Path) -> None:
    cases = [
        ("sample_applicability_reason", ""),
        ("benchmark_applicability_reason", None),
    ]
    for index, (field, value) in enumerate(cases):
        record = _non_empirical_record("theoretical", "technical_bound")
        record[field] = value
        case_root = tmp_path / f"case-{index}"
        case_root.mkdir()
        result = _run(_workspace(case_root, [record]))
        assert result.returncode != 0
        assert field in result.stdout + result.stderr


def test_rejected_record_preserves_unknown_sample_without_fabricating_zero(tmp_path: Path) -> None:
    record = _base_record()
    record.update({
        "scholarly_record_status": "retracted",
        "allowed_use": "rejected",
        "driver_node_ids": [],
        "scenario_ids": [],
        "sample_applicability": "unknown",
        "sample_applicability_reason": (
            "The withdrawn supplement no longer exposes the sampling table."
        ),
        "sample_description": None,
        "sample_size_value": None,
        "sample_size_unit": None,
        "experimental_conditions": None,
        "benchmark_applicability": "unknown",
        "benchmark_applicability_reason": (
            "The retraction notice does not preserve the benchmark version."
        ),
        "benchmark_name": None,
        "benchmark_version": None,
        "benchmark_result": None,
        "production_transfer_status": "not_applicable",
        "production_transfer_differences": "Rejected history has no production permission.",
        "production_transfer_bridge": None,
    })
    result = _run(_workspace(tmp_path, [record]))
    assert result.returncode == 0, result.stdout + result.stderr


def test_empirical_model_use_rejects_zero_or_missing_sample_size(tmp_path: Path) -> None:
    for index, mutation in enumerate(("zero", "missing")):
        record = _base_record()
        if mutation == "zero":
            record["sample_size_value"] = 0
        else:
            record.pop("sample_size_value")
        case_root = tmp_path / f"case-{index}"
        case_root.mkdir()
        result = _run(_workspace(case_root, [record]))
        assert result.returncode != 0
        assert "sample_size_value" in result.stdout + result.stderr


def test_empirical_base_sample_size_rejects_coerced_or_non_finite_values(tmp_path: Path) -> None:
    for index, value in enumerate((True, "64", "NaN", "Infinity", float("nan"), float("inf"))):
        record = _base_record()
        record["sample_size_value"] = value
        case_root = tmp_path / f"case-{index}"
        case_root.mkdir()
        result = _run(_workspace(case_root, [record]))
        assert result.returncode != 0, (repr(value), result.stdout + result.stderr)
        assert "sample_size_value" in result.stdout + result.stderr


def test_non_empirical_record_cannot_escalate_to_base_parameter(tmp_path: Path) -> None:
    record = _non_empirical_record("methods", "base_technical_parameter")
    result = _run(_workspace(tmp_path, [record]))
    assert result.returncode != 0
    output = result.stdout + result.stderr
    assert "non-empirical evidence cannot itself support base_technical_parameter" in output
    assert "single-laboratory evidence cannot support base_technical_parameter" in output
    assert "requires matched_with_quantified_bridge production transfer" in output


def test_single_lab_paper_cannot_support_base_parameter(tmp_path: Path) -> None:
    record = _base_record()
    record.update({
        "computational_reproducibility": "reproduced",
        "reproduction_source_ids": ["PAPER1"],
        "independent_replication_status": "not_found",
        "independent_replication_source_ids": [],
    })
    result = _run(_workspace(tmp_path, [record]))
    assert result.returncode != 0
    assert "single-laboratory evidence cannot support base_technical_parameter" in result.stdout + result.stderr


def test_same_lab_mirror_cannot_become_replication_by_renaming_cluster(tmp_path: Path) -> None:
    workspace = _workspace(tmp_path, [_base_record()])
    source_path = workspace / "source_manifest.json"
    payload = json.loads(source_path.read_text(encoding="utf-8"))
    primary, mirror = payload["sources"][0], payload["sources"][1]
    primary.update({
        "publisher": "Lab A",
        "authors": ["Same Team"],
        "root_original_source_id": "PAPER1",
        "derived_from_source_id": None,
        "common_origin": False,
        "measurement_method_id": "same-device-experiment",
    })
    mirror.update({
        "publisher": "Lab A",
        "authors": ["Same Team"],
        "root_original_source_id": "PAPER1",
        "derived_from_source_id": "PAPER1",
        "common_origin": True,
        "independence_cluster": "renamed-lab-a-mirror",
        "measurement_method_id": "same-device-experiment",
    })
    source_path.write_text(json.dumps(payload), encoding="utf-8")
    map_path = workspace / "source_independence_map.csv"
    with map_path.open(encoding="utf-8-sig", newline="") as handle:
        map_rows = list(csv.DictReader(handle))
        map_header = list(map_rows[0])
    map_rows[0].update({
        "publisher": "Lab A", "authors": "Same Team",
        "measurement_method_id": "same-device-experiment",
    })
    map_rows[1].update({
        "publisher": "Lab A", "authors": "Same Team",
        "root_original_source_id": "PAPER1", "derived_from_source_id": "PAPER1",
        "relationship": "mirror", "common_origin": "true",
        "cluster_id": "renamed-lab-a-mirror",
        "measurement_method_id": "same-device-experiment",
    })
    with map_path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=map_header)
        writer.writeheader()
        writer.writerows(map_rows)

    result = _run(workspace)

    assert result.returncode != 0
    output = (result.stdout + result.stderr).lower()
    assert "root" in output or "team" in output or "common origin" in output


def test_orthogonal_engineering_evidence_can_replace_replication_for_base(tmp_path: Path) -> None:
    record = _base_record()
    record.update({
        "computational_reproducibility": "not_attempted",
        "reproduction_source_ids": [],
        "independent_replication_status": "not_found",
        "independent_replication_source_ids": [],
        "orthogonal_engineering_evidence": "A customer qualification run measured the same yield boundary.",
        "orthogonal_engineering_evidence_source_ids": ["ENG1"],
    })
    result = _run(_workspace(tmp_path, [record]))
    assert result.returncode == 0, result.stdout + result.stderr


def test_narrative_production_transfer_bridge_cannot_support_base(tmp_path: Path) -> None:
    record = _base_record()
    record["production_transfer_bridge"] = (
        "Trust the analyst: laboratory value becomes the production value."
    )

    result = _run(_workspace(tmp_path, [record]))

    assert result.returncode != 0
    assert "production_transfer_bridge" in (result.stdout + result.stderr)


def test_production_transfer_bridge_arithmetic_is_recomputed(tmp_path: Path) -> None:
    record = _base_record()
    record["production_transfer_bridge"] = {
        "operation": "additive",
        "source_value": 0.92,
        "source_unit": "ratio",
        "source_source_ids": ["PAPER1"],
        "adjustments": [{
            "adjustment_id": "temperature_delta",
            "operation": "subtract",
            "value": 0.10,
            "source_ids": ["ENG1"],
        }],
        "bridged_value": 0.90,
        "target_value": 0.82,
        "target_unit": "ratio",
        "target_source_ids": ["ENG1"],
        "residual_value": 0.08,
        "residual_unit": "absolute",
    }

    result = _run(_workspace(tmp_path, [record]))

    assert result.returncode != 0
    assert "bridged_value" in (result.stdout + result.stderr)


def test_rejected_production_measurement_cannot_anchor_transfer_bridge(tmp_path: Path) -> None:
    workspace = _workspace(tmp_path, [_base_record()])
    source_path = workspace / "source_manifest.json"
    payload = json.loads(source_path.read_text(encoding="utf-8"))
    payload["sources"][2]["decision_status"] = "rejected"
    source_path.write_text(json.dumps(payload), encoding="utf-8")

    result = _run(workspace)

    assert result.returncode != 0
    assert "production_transfer_bridge" in (result.stdout + result.stderr)
    assert "rejected" in (result.stdout + result.stderr).lower()


def test_unreplicated_paper_remains_usable_as_scenario_only(tmp_path: Path) -> None:
    record = _base_record()
    record.update({
        "allowed_use": "scenario_only",
        "driver_node_ids": ["tech_yield"],
        "scenario_ids": ["bear"],
        "production_transfer_status": "mismatch_scenario_only",
        "production_transfer_bridge": None,
        "independent_replication_status": "not_found",
        "independent_replication_source_ids": [],
        "orthogonal_engineering_evidence_source_ids": [],
    })
    result = _run(_workspace(tmp_path, [record]))
    assert result.returncode == 0, result.stdout + result.stderr


def test_retracted_paper_cannot_drive_a_model_parameter(tmp_path: Path) -> None:
    record = _base_record()
    record["scholarly_record_status"] = "retracted"
    result = _run(_workspace(tmp_path, [record]))
    assert result.returncode != 0
    assert "retracted scholarly record is limited to rejected/background history" in result.stdout + result.stderr


def test_every_material_paper_source_gets_a_matching_record(tmp_path: Path) -> None:
    record = _base_record()
    record["technology_or_product"] = "Different program"
    result = _run(_workspace(tmp_path, [record]))
    assert result.returncode != 0
    assert "missing technical evidence record for Core accelerator / PAPER1" in result.stdout + result.stderr


def test_required_quality_and_model_binding_fields_are_not_prose_optional(tmp_path: Path) -> None:
    required_fields = [
        "version", "scholarly_record_status", "evidence_design", "exact_claim",
        "experimental_conditions", "sample_applicability", "sample_description",
        "benchmark_applicability", "benchmark_version", "uncertainty", "data_availability",
        "code_availability", "computational_reproducibility", "funding",
        "conflicts_of_interest", "competing_technologies", "negative_results",
        "production_transfer_differences", "technical_boundary", "driver_node_ids",
        "commercialization_permission",
    ]
    for field in required_fields:
        record = _base_record()
        record[field] = [] if field == "driver_node_ids" else ""
        with tempfile.TemporaryDirectory() as td:
            result = _run(_workspace(Path(td), [record]))
        assert result.returncode != 0, field
        assert field in result.stdout + result.stderr, field


def test_doi_may_be_replaced_only_by_stable_identifier_and_reason(tmp_path: Path) -> None:
    record = _base_record()
    record.update({
        "doi": "",
        "doi_unavailable_reason": "Preprint has no DOI at this version.",
        "stable_identifier": "arXiv:2601.01234v2",
        "version": "arXiv v2, 2026-02-05",
    })
    result = _run(_workspace(tmp_path, [record]))
    assert result.returncode == 0, result.stdout + result.stderr


def test_paper_never_grants_commercialization_permission(tmp_path: Path) -> None:
    record = _base_record()
    record["commercialization_permission"] = "revenue"
    result = _run(_workspace(tmp_path, [record]))
    assert result.returncode != 0
    assert "commercialization_permission must be none" in result.stdout + result.stderr


def test_company_with_no_material_paper_link_does_not_invent_a_record(tmp_path: Path) -> None:
    workspace = _workspace(tmp_path, [])
    _write_technology_register(
        workspace / "technology_commercialization_register.csv",
        "background",
    )
    rows = list(csv.DictReader(
        (workspace / "technology_commercialization_register.csv").open(
            encoding="utf-8-sig", newline=""
        )
    ))
    rows[0]["paper_source_ids"] = ""
    with (workspace / "technology_commercialization_register.csv").open(
        "w", encoding="utf-8-sig", newline=""
    ) as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    result = _run(workspace)
    assert result.returncode == 0, result.stdout + result.stderr
