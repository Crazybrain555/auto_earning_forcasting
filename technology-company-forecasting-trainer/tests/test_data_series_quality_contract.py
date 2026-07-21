"""Material numeric series need lineage; claimed cross-checks must be genuine."""
import csv
import json
import subprocess
import sys
from pathlib import Path


SKILL = Path(__file__).resolve().parents[1]
VALIDATOR = SKILL / "scripts/validate_historical_data_series.py"
TEMPLATE = SKILL / "assets/templates/data_series_register_template.csv"
FACT_TEMPLATE = SKILL / "assets/templates/financial_fact_ledger_template.csv"
COMPARABILITY_FIELDS = (
    "metric_construct_id", "unit", "currency", "entity_scope", "product_scope",
    "geography_scope", "period_start", "period_end", "frequency",
)


def _write_csv(path: Path, rows: list[dict[str, str]]) -> None:
    with TEMPLATE.open(encoding="utf-8-sig", newline="") as handle:
        header = next(csv.reader(handle))
    # Keep the desired API expressible during the RED phase, before the
    # canonical template has learned these columns.
    for field in ("metric_construct_id", "cross_check_bridge_json"):
        if field not in header:
            header.append(field)
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=header)
        writer.writeheader()
        writer.writerows(rows)


def _write_fact_csv(path: Path, rows: list[dict[str, str]]) -> None:
    with FACT_TEMPLATE.open(encoding="utf-8-sig", newline="") as handle:
        header = next(csv.reader(handle))
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=header)
        writer.writeheader()
        writer.writerows(rows)


def _fixture(
    tmp_path: Path,
    *,
    same_cluster: bool = False,
    omit_vintage: bool = False,
    published_after_cutoff: bool = False,
    vintage_after_cutoff: bool = False,
    revision_after_cutoff: bool = False,
    fact_cutoff_after_run: bool = False,
    fact_filed_after_run: bool = False,
    same_measurement_method: bool = False,
    unknown_original_source: bool = False,
    source_published_after_cutoff: bool = False,
    source_version_after_cutoff: bool = False,
    run_mode: str = "historical_train",
):
    run_manifest = {
        "as_of": "2026-07-20T23:59:59Z",
        "run_mode": run_mode,
        "time_boundary_enforced": run_mode == "historical_train",
    }
    source_manifest = {
        "as_of": "2026-07-20T23:59:59Z",
        "sources": [
            {
                "source_id": "S1", "publisher": "Regulator A",
                "source_type": "regulatory_measurement",
                "origin_record_kind": "original_measurement_observation",
                "epistemic_class": "independent_external_observation",
                "authority": "regulator", "independence": "independent",
                "directness": "direct", "role": "leading_indicator",
                "authors": ["Regulator A Filing Team"],
                "root_original_source_id": "S1", "derived_from_source_id": None,
                "common_origin": False, "independence_cluster": "C1",
                "measurement_method_id": "manufacturer_acceptance_census",
                "published_at": "2026-07-21T00:00:00Z" if source_published_after_cutoff else "2026-07-01T00:00:00Z",
                "version_at": "2026-07-21T00:00:00Z" if source_version_after_cutoff else "2026-07-01T00:00:00Z",
            },
            {
                "source_id": "S2", "publisher": "Industry Body B",
                "source_type": "industry_measurement",
                "origin_record_kind": "original_measurement_observation",
                "epistemic_class": "independent_external_observation",
                "authority": "third_party", "independence": "independent",
                "directness": "direct", "role": "leading_indicator",
                "authors": ["Industry Body B Panel Team"],
                "root_original_source_id": "S2", "derived_from_source_id": None,
                "common_origin": False, "independence_cluster": "C2",
                "measurement_method_id": "independent_sell_through_panel",
                "published_at": "2026-07-05T00:00:00Z", "version_at": "2026-07-05T00:00:00Z",
            },
        ]
    }
    graph = {
        "nodes": [
            {"id": "end_demand", "kind": "observable", "unit": "unit", "data_series_ids": ["D1", "D2"]},
            {"id": "irrelevant_metric", "kind": "input", "unit": "unit", "data_series_ids": []},
            {"id": "revenue", "kind": "output", "unit": "USD"},
        ],
        "equations": [
            {"id": "eq_revenue", "output": "revenue", "operation": "identity", "inputs": ["end_demand"]}
        ],
        "main_line": {
            "carrier_node_ids": ["end_demand"],
            "target_node_ids": ["revenue"],
            "falsification_ids": [],
            "competitor_response_node_ids": [],
        },
    }
    rows = [
        {
            "series_id": "D1", "metric_name": "end demand", "source_id": "S1",
            "observation_value": "100", "observation_type": "flow",
            "available_at": "2026-07-15T00:00:00Z", "vintage_id": "D1-v1",
            "revision_of_series_id": "none", "classification_version": "2026Q2-v1",
            "input_series_ids": "none",
            "original_source_id": "S1", "independence_cluster": "C1",
            "measurement_method_id": "manufacturer_acceptance_census",
            "published_at": "2026-07-21T00:00:00Z" if published_after_cutoff else "2026-07-01T00:00:00Z",
            "retrieved_at": "2026-07-20T00:00:00Z",
            "vintage_at": "" if omit_vintage else (
                "2026-07-21T00:00:00Z" if vintage_after_cutoff else "2026-07-01T00:00:00Z"
            ),
            "revision_at": "2026-07-21T00:00:00Z" if revision_after_cutoff else "2026-07-01T00:00:00Z",
            "period_start": "2026-04-01", "period_end": "2026-06-30", "frequency": "quarterly",
            "unit": "unit", "currency": "N/A", "metric_definition": "shipments accepted by end customers",
            "metric_construct_id": "accepted_end_customer_shipments_flow",
            "entity_scope": "market", "product_scope": "product family", "geography_scope": "global",
            "population_coverage": "named panel; 80% of disclosed market", "transformation": "none",
            "revision_policy": "replace only with a new recorded vintage", "lag_days": "15",
            "known_bias": "panel excludes small vendors", "cross_check_series_ids": "D2",
            "cross_check_result": "within 3%; definition difference reconciled", "allowed_model_use": "base_parameter",
            "cross_check_bridge_json": "",
            "driver_node_ids": "end_demand", "conclusion_critical": "true", "status": "accepted", "notes": "",
        },
        {
            "series_id": "D2", "metric_name": "end demand cross-check", "source_id": "S2",
            "observation_value": "103", "observation_type": "flow",
            "available_at": "2026-07-20T00:00:00Z", "vintage_id": "D2-v1",
            "revision_of_series_id": "none", "classification_version": "2026Q2-v1",
            "input_series_ids": "none",
            "original_source_id": "MISSING" if unknown_original_source else "S2",
            "independence_cluster": "C1" if same_cluster else "C2",
            "measurement_method_id": (
                "manufacturer_acceptance_census" if same_measurement_method
                else "independent_sell_through_panel"
            ),
            "published_at": "2026-07-05T00:00:00Z", "retrieved_at": "2026-07-20T00:00:00Z",
            "vintage_at": "2026-07-05T00:00:00Z", "period_start": "2026-04-01",
            "revision_at": "2026-07-05T00:00:00Z",
            "period_end": "2026-06-30", "frequency": "quarterly", "unit": "unit", "currency": "N/A",
            "metric_definition": "manufacturer sell-through adjusted for channel stock",
            "metric_construct_id": "accepted_end_customer_shipments_flow",
            "entity_scope": "market", "product_scope": "product family", "geography_scope": "global",
            "population_coverage": "member survey; coverage disclosed", "transformation": "calendar-quarter alignment",
            "revision_policy": "retain preliminary and final vintages", "lag_days": "20",
            "known_bias": "survey non-response", "cross_check_series_ids": "D1",
            "cross_check_result": "within 3%; definition difference reconciled", "allowed_model_use": "cross_check",
            "cross_check_bridge_json": "",
            "driver_node_ids": "end_demand", "conclusion_critical": "true", "status": "accepted", "notes": "",
        },
    ]
    register = tmp_path / "data_series_register.csv"
    sources = tmp_path / "source_manifest.json"
    model_graph = tmp_path / "model_graph.json"
    manifest = tmp_path / "run_manifest.json"
    facts = tmp_path / "financial_fact_ledger.csv"
    independence_map = tmp_path / "source_independence_map.csv"
    _write_csv(register, rows)
    sources.write_text(json.dumps(source_manifest), encoding="utf-8")
    model_graph.write_text(json.dumps(graph), encoding="utf-8")
    manifest.write_text(json.dumps(run_manifest), encoding="utf-8")
    with independence_map.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow([
            "source_id", "cluster_id", "root_original_source_id",
            "derived_from_source_id", "relationship", "common_origin", "publisher",
            "authors", "measurement_method_id", "independence_basis", "notes",
        ])
        writer.writerows([
            ["S1", "C1", "S1", "", "original", "false", "Regulator A",
             "Regulator A Filing Team", "manufacturer_acceptance_census",
             "direct regulator measurement", ""],
            ["S2", "C2", "S2", "", "original", "false", "Industry Body B",
             "Industry Body B Panel Team", "independent_sell_through_panel",
             "independent panel measurement", ""],
        ])
    _write_fact_csv(facts, [{
        "fact_id": "F1", "entity_id": "TEST", "source_id": "S1",
        "accession_or_filing_id": "TEST-2025-10K",
        "filed_at": "2026-07-21T00:00:00Z" if fact_filed_after_run else "2026-03-01T00:00:00Z",
        "retrieved_at": "2026-07-20T00:00:00Z",
        "as_of_cutoff": "2026-07-21T00:00:00Z" if (
            fact_cutoff_after_run or fact_filed_after_run
        ) else "2026-07-20T23:59:59Z",
        "form": "10-K", "fiscal_year": "2025", "fiscal_period": "FY",
        "period_start": "2025-01-01", "period_end": "2025-12-31", "fact_name": "Revenue",
        "taxonomy": "us-gaap", "tag": "RevenueFromContractWithCustomerExcludingAssessedTax",
        "dimensions": "consolidated", "unit": "USD", "decimals": "-6", "scale": "1000000",
        "sign": "positive", "reported_value": "100", "normalized_value": "100", "currency": "USD",
        "statement_or_note_anchor": "income statement revenue", "extraction_method": "rendered filing checked",
        "amendment_or_restatement": "original", "predecessor_fact_id": "",
        "comparability_adjustment": "none", "status": "accepted", "conflict_note": "none",
    }])
    return register, sources, model_graph, manifest, facts


def _run(files):
    register, sources, graph, manifest, facts = files
    independence_map = register.parent / "source_independence_map.csv"
    return subprocess.run(
        [sys.executable, str(VALIDATOR), "--register", str(register), "--sources", str(sources),
         "--graph", str(graph), "--manifest", str(manifest), "--facts", str(facts),
         "--independence-map", str(independence_map), "--strict"],
        capture_output=True, text=True,
    )


def test_data_series_template_has_no_quality_score_or_weight():
    assert TEMPLATE.is_file()
    with TEMPLATE.open(encoding="utf-8-sig", newline="") as handle:
        header = next(csv.reader(handle))
    required = {
        "series_id", "source_id", "original_source_id", "independence_cluster",
        "observation_value", "observation_type", "available_at", "vintage_id",
        "revision_of_series_id", "classification_version", "input_series_ids",
        "measurement_method_id", "vintage_at", "revision_at", "period_start", "period_end",
        "frequency", "unit", "currency",
        "metric_definition", "metric_construct_id", "entity_scope", "product_scope", "geography_scope",
        "population_coverage", "transformation", "revision_policy", "lag_days", "known_bias",
        "cross_check_series_ids", "cross_check_result", "cross_check_bridge_json",
        "allowed_model_use", "driver_node_ids",
        "conclusion_critical", "status",
    }
    assert required <= set(header), required - set(header)
    assert not any("score" in name or "weight" in name for name in header)


def test_method_explains_cutoff_and_non_circular_triangulation_contract():
    text = (SKILL / "references/data-quality-and-triangulation.md").read_text(encoding="utf-8").lower()
    for concept in (
        "publication",
        "vintage",
        "revision",
        "original_source_id",
        "measurement_method_id",
        "circular corroboration",
        "metric construct",
        "quantified basis bridge",
        "target_basis",
    ):
        assert concept in text, concept
    trainer_overlay = (SKILL / "references/historical-training-loop.md").read_text(
        encoding="utf-8"
    ).lower()
    assert "post-cutoff" in trainer_overlay


def test_financial_fact_ledger_preserves_filing_and_restatement_lineage():
    assert FACT_TEMPLATE.is_file()
    with FACT_TEMPLATE.open(encoding="utf-8-sig", newline="") as handle:
        header = set(next(csv.reader(handle)))
    required = {
        "fact_id", "entity_id", "source_id", "accession_or_filing_id", "filed_at",
        "retrieved_at", "as_of_cutoff", "form", "fiscal_year", "fiscal_period",
        "period_start", "period_end", "fact_name", "taxonomy", "tag", "dimensions",
        "unit", "decimals", "scale", "sign", "reported_value", "normalized_value",
        "currency", "statement_or_note_anchor", "extraction_method",
        "amendment_or_restatement", "predecessor_fact_id", "comparability_adjustment",
        "status", "conflict_note",
    }
    assert required <= header, required - header


def test_complete_independent_series_pass(tmp_path):
    result = _run(_fixture(tmp_path))
    assert result.returncode == 0, result.stdout + result.stderr


def test_observation_value_availability_and_vintage_identity_are_not_optional(tmp_path):
    files = _fixture(tmp_path)
    register = files[0]
    with register.open(encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))
    rows[0]["observation_value"] = ""
    rows[0]["available_at"] = ""
    rows[0]["vintage_id"] = ""
    _write_csv(register, rows)
    result = _run(files)
    output = result.stdout + result.stderr
    assert result.returncode != 0
    assert "observation_value" in output
    assert "available_at" in output
    assert "vintage_id" in output


def test_real_availability_not_period_or_publication_date_owns_the_cutoff(tmp_path):
    files = _fixture(tmp_path)
    register = files[0]
    with register.open(encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))
    rows[0]["available_at"] = "2026-07-21T00:00:00Z"
    rows[0]["lag_days"] = "21"
    _write_csv(register, rows)
    result = _run(files)
    assert result.returncode != 0
    assert "available_at is after run_manifest.as_of" in (result.stdout + result.stderr)


def test_live_current_research_is_not_rejected_by_scaffold_snapshot_time(tmp_path):
    files = _fixture(
        tmp_path,
        run_mode="live_forecast",
        published_after_cutoff=True,
        vintage_after_cutoff=True,
        revision_after_cutoff=True,
        source_published_after_cutoff=True,
        source_version_after_cutoff=True,
        fact_cutoff_after_run=True,
        fact_filed_after_run=True,
    )
    register = files[0]
    with register.open(encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))
    rows[0]["available_at"] = "2026-07-21T00:00:00Z"
    rows[0]["lag_days"] = "21"
    _write_csv(register, rows)
    facts = files[-1]
    with facts.open(encoding="utf-8-sig", newline="") as handle:
        fact_reader = csv.DictReader(handle)
        fact_header = [field for field in (fact_reader.fieldnames or []) if field != "as_of_cutoff"]
        fact_rows = list(fact_reader)
    for row in fact_rows:
        row.pop("as_of_cutoff", None)
    with facts.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fact_header)
        writer.writeheader()
        writer.writerows(fact_rows)
    result = _run(files)
    assert result.returncode == 0, result.stdout + result.stderr


def test_historical_run_mode_cannot_bypass_cutoff_with_manifest_boolean(tmp_path):
    files = _fixture(tmp_path, published_after_cutoff=True)
    manifest_path = files[3]
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["time_boundary_enforced"] = False
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    result = _run(files)
    assert result.returncode != 0
    assert "published_at is after run_manifest.as_of" in (result.stdout + result.stderr)


def test_availability_lag_recomputes_from_observation_period(tmp_path):
    files = _fixture(tmp_path)
    register = files[0]
    with register.open(encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))
    rows[0]["lag_days"] = "99"
    _write_csv(register, rows)
    result = _run(files)
    assert result.returncode != 0
    assert "lag_days" in (result.stdout + result.stderr)


def test_revision_link_must_resolve_to_a_prior_observation(tmp_path):
    files = _fixture(tmp_path)
    register = files[0]
    with register.open(encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))
    rows[0]["revision_of_series_id"] = "MISSING"
    _write_csv(register, rows)
    result = _run(files)
    assert result.returncode != 0
    assert "revision_of_series_id" in (result.stdout + result.stderr)


def test_single_direct_anchor_can_pass_without_claiming_corroboration(tmp_path):
    """Criticality triggers review, not an automatic second-source quota."""
    files = _fixture(tmp_path)
    register, _sources, graph_path, _manifest, _facts = files
    with register.open(encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))
    anchor = rows[0]
    anchor["cross_check_series_ids"] = ""
    anchor["cross_check_result"] = ""
    anchor["cross_check_bridge_json"] = ""
    _write_csv(register, [anchor])

    graph = json.loads(graph_path.read_text(encoding="utf-8"))
    graph["nodes"][0]["data_series_ids"] = ["D1"]
    graph_path.write_text(json.dumps(graph), encoding="utf-8")

    result = _run(files)

    assert result.returncode == 0, result.stdout + result.stderr


def test_partial_cross_check_claim_is_rejected(tmp_path):
    """A result narrative cannot claim corroboration without a bound series."""
    files = _fixture(tmp_path)
    register = files[0]
    with register.open(encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))
    rows[0]["cross_check_series_ids"] = ""
    rows[0]["cross_check_result"] = "independent measurement agrees"
    rows[1]["cross_check_series_ids"] = ""
    rows[1]["cross_check_result"] = ""
    _write_csv(register, rows)

    result = _run(files)

    assert result.returncode != 0
    assert "cross-check claim" in (result.stdout + result.stderr).lower()


def test_strict_series_must_support_a_main_line_carrier(tmp_path):
    files = _fixture(tmp_path)
    register = files[0]
    with register.open(encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))
    for row in rows:
        row["driver_node_ids"] = "irrelevant_metric"
        row["conclusion_critical"] = "false"
    _write_csv(register, rows)

    result = _run(files)

    assert result.returncode != 0
    assert "main-line carrier" in (result.stdout + result.stderr).lower()


def test_missing_vintage_fails(tmp_path):
    result = _run(_fixture(tmp_path, omit_vintage=True))
    assert result.returncode != 0
    assert "vintage" in (result.stdout + result.stderr).lower()


def test_same_origin_does_not_count_as_cross_check(tmp_path):
    result = _run(_fixture(tmp_path, same_cluster=True))
    assert result.returncode != 0
    assert "independ" in (result.stdout + result.stderr).lower()


def test_unknown_original_source_id_fails(tmp_path):
    result = _run(_fixture(tmp_path, unknown_original_source=True))
    assert result.returncode != 0
    assert "original_source_id" in (result.stdout + result.stderr)


def test_same_measurement_method_does_not_count_as_cross_check(tmp_path):
    result = _run(_fixture(tmp_path, same_measurement_method=True))
    assert result.returncode != 0
    assert "measurement_method_id" in (result.stdout + result.stderr)


def test_derived_common_origin_cannot_be_hidden_by_changing_cluster_strings(tmp_path):
    files = _fixture(tmp_path)
    register, sources_path, *_rest = files
    payload = json.loads(sources_path.read_text(encoding="utf-8"))
    payload["sources"][0].update({
        "root_original_source_id": "S1",
        "derived_from_source_id": None,
        "common_origin": False,
        "independence_cluster": "root-panel",
        "authors": ["Shared Measurement Team"],
        "measurement_method_id": "manufacturer_acceptance_census",
    })
    payload["sources"][1].update({
        "publisher": "Regulator A",
        "root_original_source_id": "S1",
        "derived_from_source_id": "S1",
        "common_origin": True,
        # These self-declared strings previously made the transformed copy
        # look independent even though its root and team are identical.
        "independence_cluster": "renamed-copy",
        "authors": ["Shared Measurement Team"],
        "measurement_method_id": "renamed_method",
    })
    sources_path.write_text(json.dumps(payload), encoding="utf-8")
    with register.open(encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))
    rows[0]["independence_cluster"] = "root-panel"
    rows[1].update({
        "original_source_id": "S1",
        "independence_cluster": "renamed-copy",
        "measurement_method_id": "renamed_method",
    })
    rows[1]["notes"] = "Transformed republication of D1; no new observation."
    _write_csv(register, rows)
    map_path = register.parent / "source_independence_map.csv"
    with map_path.open(encoding="utf-8-sig", newline="") as handle:
        map_rows = list(csv.DictReader(handle))
        map_header = list(map_rows[0])
    map_rows[0].update({
        "cluster_id": "root-panel", "authors": "Shared Measurement Team",
        "measurement_method_id": "manufacturer_acceptance_census",
    })
    map_rows[1].update({
        "cluster_id": "renamed-copy", "root_original_source_id": "S1",
        "derived_from_source_id": "S1", "relationship": "transformation",
        "common_origin": "true", "publisher": "Regulator A",
        "authors": "Shared Measurement Team", "measurement_method_id": "renamed_method",
    })
    with map_path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=map_header)
        writer.writeheader()
        writer.writerows(map_rows)

    result = _run(files)

    assert result.returncode != 0
    output = (result.stdout + result.stderr).lower()
    assert "root" in output or "common origin" in output or "derived" in output


def test_unrelated_mars_employee_series_cannot_cross_check_end_demand(tmp_path):
    """Different origins do not make economically incomparable metrics corroboration."""
    files = _fixture(tmp_path)
    register = files[0]
    with register.open(encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))
    # D1's explicit cross-check claim remains objectively auditable even when
    # D1 itself is not conclusion-critical. D2 is a separate single hard anchor
    # whose need for corroboration belongs to the independent reviewer.
    rows[0]["conclusion_critical"] = "false"
    rows[1]["cross_check_series_ids"] = ""
    rows[1]["cross_check_result"] = ""
    rows[1].update({
        "metric_name": "Mars employee count",
        "metric_definition": "employees located on Mars at period end",
        "metric_construct_id": "period_end_employee_headcount_stock",
        "unit": "employees",
        "entity_scope": "Mars Colony Holdings",
        "product_scope": "workforce",
        "geography_scope": "Mars",
        "frequency": "annual",
        "period_start": "2025-01-01",
        "period_end": "2025-12-31",
        "cross_check_result": "different source agrees with our story",
    })
    _write_csv(register, rows)

    result = _run(files)

    assert result.returncode != 0
    assert "comparab" in (result.stdout + result.stderr).lower()


def _quantified_bridge(target: dict[str, str], check_id: str = "D2") -> dict:
    return {
        "input_series_id": check_id,
        "target_series_id": target["series_id"],
        "mismatch_fields": ["metric_construct_id", "period_start", "frequency"],
        "operation": "additive",
        "source_value": 97.0,
        "source_unit": "unit",
        "source_source_ids": ["S2"],
        "adjustments": [{
            "adjustment_id": "channel_inventory_change",
            "operation": "add",
            "value": 5.0,
            "source_ids": ["S1", "S2"],
        }],
        "bridged_value": 102.0,
        "target_value": 100.0,
        "target_unit": "unit",
        "target_source_ids": ["S1"],
        "residual_value": 2.0,
        "residual_unit": "percent",
        "target_basis": {field: target[field] for field in COMPARABILITY_FIELDS},
    }


def test_quantified_basis_bridge_allows_non_identical_cross_check(tmp_path):
    files = _fixture(tmp_path)
    register = files[0]
    with register.open(encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))
    rows[1].update({
        "metric_construct_id": "monthly_sell_through_flow",
        "period_start": "2026-06-01",
        "frequency": "monthly",
        "cross_check_series_ids": "",
        "cross_check_result": "",
        "conclusion_critical": "false",
    })
    rows[0]["cross_check_bridge_json"] = json.dumps({"D2": _quantified_bridge(rows[0])})
    rows[0]["cross_check_result"] = "102 bridged units versus 100 target units; residual +2.0%"
    _write_csv(register, rows)

    result = _run(files)

    assert result.returncode == 0, result.stdout + result.stderr


def test_quantified_basis_bridge_arithmetic_is_verified(tmp_path):
    files = _fixture(tmp_path)
    register = files[0]
    with register.open(encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))
    rows[1].update({
        "metric_construct_id": "monthly_sell_through_flow",
        "period_start": "2026-06-01",
        "frequency": "monthly",
        "cross_check_series_ids": "",
        "cross_check_result": "",
        "conclusion_critical": "false",
    })
    bridge = _quantified_bridge(rows[0])
    bridge["residual_value"] = 42.0
    rows[0]["cross_check_bridge_json"] = json.dumps({"D2": bridge})
    _write_csv(register, rows)

    result = _run(files)

    assert result.returncode != 0
    assert "bridge residual" in (result.stdout + result.stderr).lower()


def test_quantified_basis_bridge_target_basis_is_verified(tmp_path):
    files = _fixture(tmp_path)
    register = files[0]
    with register.open(encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))
    rows[1].update({
        "metric_construct_id": "monthly_sell_through_flow",
        "period_start": "2026-06-01",
        "frequency": "monthly",
        "cross_check_series_ids": "",
        "cross_check_result": "",
        "conclusion_critical": "false",
    })
    bridge = _quantified_bridge(rows[0])
    bridge["target_basis"]["geography_scope"] = "Mars"
    rows[0]["cross_check_bridge_json"] = json.dumps({"D2": bridge})
    _write_csv(register, rows)

    result = _run(files)

    assert result.returncode != 0
    assert "target_basis" in (result.stdout + result.stderr)


def test_quantified_basis_bridge_units_must_match_endpoint_series(tmp_path):
    files = _fixture(tmp_path)
    register = files[0]
    with register.open(encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))
    rows[1].update({
        "metric_construct_id": "monthly_sell_through_flow",
        "period_start": "2026-06-01",
        "frequency": "monthly",
        "cross_check_series_ids": "",
        "cross_check_result": "",
        "conclusion_critical": "false",
    })
    bridge = _quantified_bridge(rows[0])
    bridge["source_unit"] = "employees"
    rows[0]["cross_check_bridge_json"] = json.dumps({"D2": bridge})
    _write_csv(register, rows)

    result = _run(files)

    assert result.returncode != 0
    assert "source_unit" in (result.stdout + result.stderr)


def test_narrative_basis_bridge_cannot_manufacture_a_bridged_value(tmp_path):
    files = _fixture(tmp_path)
    register = files[0]
    with register.open(encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))
    rows[1].update({
        "metric_construct_id": "monthly_sell_through_flow",
        "period_start": "2026-06-01",
        "frequency": "monthly",
        "cross_check_series_ids": "",
        "cross_check_result": "",
        "conclusion_critical": "false",
    })
    bridge = _quantified_bridge(rows[0])
    bridge.update({
        "formula": "arbitrary narrative transform with no executable operation",
        "source_value": 1.0,
        "bridged_value": 100.0,
        "target_value": 100.0,
        "residual_value": 0.0,
    })
    rows[0]["cross_check_bridge_json"] = json.dumps({"D2": bridge})
    _write_csv(register, rows)

    result = _run(files)

    assert result.returncode != 0
    assert "operation" in (result.stdout + result.stderr).lower()


def test_published_after_run_manifest_cutoff_fails(tmp_path):
    result = _run(_fixture(tmp_path, published_after_cutoff=True))
    assert result.returncode != 0
    assert "published_at" in (result.stdout + result.stderr)


def test_vintage_after_run_manifest_cutoff_fails(tmp_path):
    result = _run(_fixture(tmp_path, vintage_after_cutoff=True))
    assert result.returncode != 0
    assert "vintage_at" in (result.stdout + result.stderr)


def test_revision_after_run_manifest_cutoff_fails(tmp_path):
    result = _run(_fixture(tmp_path, revision_after_cutoff=True))
    assert result.returncode != 0
    assert "revision_at" in (result.stdout + result.stderr)


def test_source_publication_after_run_manifest_cutoff_fails(tmp_path):
    result = _run(_fixture(tmp_path, source_published_after_cutoff=True))
    assert result.returncode != 0
    assert "source S1 published_at" in (result.stdout + result.stderr)


def test_source_version_after_run_manifest_cutoff_fails(tmp_path):
    result = _run(_fixture(tmp_path, source_version_after_cutoff=True))
    assert result.returncode != 0
    assert "source S1 version_at" in (result.stdout + result.stderr)


def test_fact_cutoff_after_run_manifest_cutoff_fails(tmp_path):
    result = _run(_fixture(tmp_path, fact_cutoff_after_run=True))
    assert result.returncode != 0
    assert "as_of_cutoff" in (result.stdout + result.stderr)


def test_fact_filed_after_run_manifest_cutoff_fails(tmp_path):
    result = _run(_fixture(tmp_path, fact_filed_after_run=True))
    assert result.returncode != 0
    assert "filed_at" in (result.stdout + result.stderr)


def test_conclusion_critical_human_required_series_cannot_pass_strict(tmp_path):
    files = _fixture(tmp_path)
    register = files[0]
    with register.open(encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))
    for row in rows:
        row.update({
            "metric_name": "N/A", "independence_cluster": "N/A",
            "measurement_method_id": "N/A", "frequency": "N/A", "unit": "N/A",
            "currency": "N/A", "metric_definition": "N/A", "entity_scope": "N/A",
            "product_scope": "N/A", "geography_scope": "N/A", "population_coverage": "N/A",
            "transformation": "N/A", "revision_policy": "N/A", "lag_days": "N/A",
            "known_bias": "N/A", "cross_check_series_ids": "", "cross_check_result": "",
            "allowed_model_use": "human_required", "conclusion_critical": "true",
            "status": "human_required", "notes": "missing evidence",
        })
    _write_csv(register, rows)
    result = _run(files)
    assert result.returncode != 0
    assert "conclusion-critical" in (result.stdout + result.stderr)


def test_financial_fact_na_shell_cannot_pass_strict(tmp_path):
    files = _fixture(tmp_path)
    facts = files[-1]
    _write_fact_csv(facts, [{
        "fact_id": "F1", "entity_id": "N/A", "source_id": "S1",
        "accession_or_filing_id": "N/A", "filed_at": "N/A", "retrieved_at": "N/A",
        "as_of_cutoff": "N/A", "form": "N/A", "fiscal_year": "N/A", "fiscal_period": "N/A",
        "period_start": "N/A", "period_end": "N/A", "fact_name": "N/A", "taxonomy": "N/A",
        "tag": "N/A", "dimensions": "N/A", "unit": "N/A", "decimals": "N/A", "scale": "N/A",
        "sign": "N/A", "reported_value": "N/A", "normalized_value": "N/A", "currency": "N/A",
        "statement_or_note_anchor": "N/A", "extraction_method": "N/A",
        "amendment_or_restatement": "original", "predecessor_fact_id": "",
        "comparability_adjustment": "N/A", "status": "accepted", "conflict_note": "N/A",
    }])
    result = _run(files)
    assert result.returncode != 0
    assert "financial fact" in (result.stdout + result.stderr).lower()


def test_delivery_scaffolds_and_validates_data_series():
    registry = json.loads((SKILL / "assets/artifact_registry.json").read_text(encoding="utf-8"))
    by_path = {row["path"]: row for row in registry["artifacts"]}
    for path, template in (
        ("data_series_register.csv", "assets/templates/data_series_register_template.csv"),
        ("financial_fact_ledger.csv", "assets/templates/financial_fact_ledger_template.csv"),
    ):
        assert by_path[path]["requirement"] == "core"
        assert by_path[path]["scaffold"] is True
        assert by_path[path]["template"] == template
    live = (SKILL / "assets/live_release/SKILL.md").read_text(encoding="utf-8")
    assert "references/data-quality-and-triangulation.md" in live


def test_run_manifest_declares_new_v10_data_contract():
    method = json.loads((SKILL / "assets/method_system.json").read_text(encoding="utf-8"))
    manifest = json.loads(
        (SKILL / "assets/templates/run_manifest_template.json").read_text(encoding="utf-8")
    )
    assert manifest["method_version"].startswith(method["method_version"])
    assert manifest["baseline_skill_version"] == method["method_version"]
    snapshot = json.loads(
        (SKILL / "assets/templates/forecast_snapshot_template.json").read_text(encoding="utf-8")
    )
    assert snapshot["model_version"].startswith(method["method_version"])
    assert {
        "earnings_power_bridge.csv",
        "data_series_register.csv",
        "financial_fact_ledger.csv",
    } <= set(manifest["required_artifacts"])
