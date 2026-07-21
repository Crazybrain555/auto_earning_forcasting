"""One authored scenario catalog governs every generated scenario view."""
from __future__ import annotations

import csv
import importlib.util
import json
import subprocess
import sys
from pathlib import Path


SKILL = Path(__file__).resolve().parents[1]
MODULE_PATH = SKILL / "scripts" / "scenario_contract.py"
VALIDATOR = SKILL / "scripts" / "validate_delivery.py"
SCHEMAS = SKILL / "assets" / "schemas"
sys.path.insert(0, str(SKILL / "scripts"))
from package_self_test import delivery_smoke_test


def _load_module():
    assert MODULE_PATH.exists(), "missing shared scenario_contract.py"
    spec = importlib.util.spec_from_file_location("scenario_contract_test", MODULE_PATH)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _scenario_payload() -> dict:
    return {
        "schema_version": "2.0",
        "scenarios": [
            {
                "id": "demand_contraction",
                "role": "alternative",
                "probability": 0.25,
                "shocks": [{"node_id": "demand"}],
            },
            {
                "id": "central_operating_path",
                "role": "reference",
                "probability": 0.75,
                "shocks": [],
            },
        ],
    }


def _valid_workspace(tmp_path: Path) -> Path:
    # The package smoke test constructs the canonical integration fixture.  A
    # different contract under concurrent development may make the aggregate
    # delivery fail; these regressions assert the named scenario checks rather
    # than treating an unrelated aggregate exit code as evidence.
    try:
        delivery_smoke_test(SKILL, "trainer", tmp_path)
    except SystemExit:
        pass
    workspace = tmp_path / "delivery"
    baseline = _run_delivery(workspace)
    for check_name in (
        "scenarios:catalog",
        "assumptions:scenario-bindings",
        "snapshot:scenario-probabilities",
        "snapshot:valuation-summary",
    ):
        check = _check(baseline, check_name)
        assert check["passed"] is True, check
    return workspace


def _run_delivery(workspace: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(VALIDATOR), "--workspace", str(workspace), "--strict"],
        capture_output=True,
        text=True,
    )


def _check(result: subprocess.CompletedProcess[str], name: str) -> dict:
    payload = json.loads(result.stdout)
    matches = [row for row in payload.get("checks", []) if row.get("check") == name]
    assert len(matches) == 1, (name, result.stdout + result.stderr)
    return matches[0]


def test_catalog_uses_free_ids_one_reference_and_bounded_probabilities():
    module = _load_module()
    catalog, problems = module.parse_scenario_catalog(_scenario_payload())
    assert problems == []
    assert catalog is not None
    assert catalog.reference_id == "central_operating_path"
    assert catalog.ids == frozenset({"demand_contraction", "central_operating_path"})

    for value in (-0.1, 1.1, True, "0.75", float("nan"), float("inf")):
        payload = _scenario_payload()
        payload["scenarios"][1]["probability"] = value
        _, problems = module.parse_scenario_catalog(payload)
        assert any("probability" in problem for problem in problems), (value, problems)

    payload = _scenario_payload()
    payload["scenarios"][0]["role"] = "reference"
    _, problems = module.parse_scenario_catalog(payload)
    assert any("exactly one reference" in problem for problem in problems), problems


def test_snapshot_probability_view_is_an_exact_typed_catalog_projection():
    module = _load_module()
    catalog, problems = module.parse_scenario_catalog(_scenario_payload())
    assert problems == [] and catalog is not None
    valid = dict(catalog.probabilities)
    assert module.validate_probability_view(valid, catalog) == []

    for value in (-0.1, 1.1, True, "0.75", float("nan"), float("inf")):
        view = dict(valid)
        view["central_operating_path"] = value
        problems = module.validate_probability_view(view, catalog)
        assert any("probability" in problem for problem in problems), (value, problems)

    for view in (
        {"central_operating_path": 1.0},
        {**valid, "ghost_scenario": 0.0},
        {"demand_contraction": 0.30, "central_operating_path": 0.70},
    ):
        assert module.validate_probability_view(view, catalog), view


def test_schemas_express_local_scenario_and_valuation_summary_types():
    scenario_schema = json.loads(
        (SCHEMAS / "scenario_set.schema.json").read_text(encoding="utf-8")
    )
    scenario_array = scenario_schema["properties"]["scenarios"]
    assert scenario_array["minContains"] == 1
    assert scenario_array["maxContains"] == 1
    assert scenario_array["contains"]["properties"]["role"]["const"] == "reference"
    assert scenario_array["items"]["properties"]["probability"] == {
        "type": "number", "minimum": 0, "maximum": 1,
    }

    snapshot_schema = json.loads(
        (SCHEMAS / "forecast_snapshot.schema.json").read_text(encoding="utf-8")
    )
    assert "valuation_summary" in snapshot_schema["required"]
    summary = snapshot_schema["properties"]["valuation_summary"]
    assert summary["additionalProperties"] is False
    assert {
        "reference_scenario_id", "fair_value_by_scenario_id",
        "not_valued_scenario_ids", "valuation_completeness",
    } <= set(
        summary["required"]
    )
    assert summary["properties"]["fair_value_by_scenario_id"][
        "additionalProperties"
    ] == {"type": "number"}


def test_strict_delivery_rejects_undeclared_assumption_scenario(tmp_path: Path):
    workspace = _valid_workspace(tmp_path)
    path = workspace / "assumption_register.csv"
    with path.open(encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))
    assert rows
    for row in rows:
        row["scenario"] = "Base_LITERAL_NOT_DECLARED"
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)

    result = _run_delivery(workspace)
    check = _check(result, "assumptions:scenario-bindings")
    assert check["passed"] is False, check
    assert "unknown scenario" in check["detail"]


def test_strict_delivery_rejects_out_of_domain_probability_views(tmp_path: Path):
    workspace = _valid_workspace(tmp_path)
    scenario_path = workspace / "scenario_set.json"
    snapshot_path = workspace / "forecast_snapshot.json"
    scenario_set = json.loads(scenario_path.read_text(encoding="utf-8"))
    snapshot = json.loads(snapshot_path.read_text(encoding="utf-8"))
    ids = [row["id"] for row in scenario_set["scenarios"]]
    probabilities = {ids[0]: -0.2, ids[1]: 1.2, **{scenario_id: 0.0 for scenario_id in ids[2:]}}
    for row in scenario_set["scenarios"]:
        row["probability"] = probabilities[row["id"]]
    snapshot["scenario_probabilities"] = probabilities
    scenario_path.write_text(json.dumps(scenario_set, indent=2), encoding="utf-8")
    snapshot_path.write_text(json.dumps(snapshot, indent=2), encoding="utf-8")

    result = _run_delivery(workspace)
    catalog_check = _check(result, "scenarios:catalog")
    probability_check = _check(result, "snapshot:scenario-probabilities")
    assert catalog_check["passed"] is False, catalog_check
    assert probability_check["passed"] is False, probability_check
    assert "probability" in catalog_check["detail"] + probability_check["detail"]


def test_valuation_summary_cannot_publish_unexecuted_or_ghost_scenario_values(tmp_path: Path):
    workspace = _valid_workspace(tmp_path)
    snapshot_path = workspace / "forecast_snapshot.json"
    snapshot = json.loads(snapshot_path.read_text(encoding="utf-8"))
    snapshot["valuation_summary"] = {
        **snapshot["valuation_summary"],
        "reference_scenario_id": "literal_base_not_declared",
        "fair_value_by_scenario_id": {"ghost_scenario": 999999.0},
    }
    snapshot_path.write_text(json.dumps(snapshot, indent=2), encoding="utf-8")

    result = _run_delivery(workspace)
    check = _check(result, "snapshot:valuation-summary")
    assert check["passed"] is False, check
    assert "valuation_summary" in check["detail"]


def test_valuation_summary_reference_value_must_match_executed_per_share_value(tmp_path: Path):
    workspace = _valid_workspace(tmp_path)
    snapshot_path = workspace / "forecast_snapshot.json"
    snapshot = json.loads(snapshot_path.read_text(encoding="utf-8"))
    snapshot["valuation_summary"]["reference_scenario_id"] = "central_operating_path"
    snapshot["valuation_summary"]["fair_value_by_scenario_id"] = {
        "central_operating_path": snapshot["valuation"]["per_share"]["value_per_share"] + 1.0,
    }
    snapshot_path.write_text(json.dumps(snapshot, indent=2), encoding="utf-8")

    result = _run_delivery(workspace)
    check = _check(result, "snapshot:valuation-summary")
    assert check["passed"] is False, check
    assert "valuation_summary" in check["detail"]


def test_valuation_summary_rejects_declared_but_unexecuted_rival_value(tmp_path: Path):
    workspace = _valid_workspace(tmp_path)
    snapshot_path = workspace / "forecast_snapshot.json"
    snapshot = json.loads(snapshot_path.read_text(encoding="utf-8"))
    executed = snapshot["valuation"]["per_share"]["value_per_share"]
    snapshot["valuation_summary"]["reference_scenario_id"] = "central_operating_path"
    snapshot["valuation_summary"]["fair_value_by_scenario_id"] = {
        "central_operating_path": executed,
        "demand_contraction": executed - 2.0,
    }
    # A free-form nested value is not executable merely because it uses a
    # plausible field name.  Until a per-scenario valuation identity is part of
    # the validated contract, only the validated reference per-share result may
    # be projected into the summary.
    snapshot["valuation"]["by_scenario_id"] = {
        "demand_contraction": {"per_share": {"value_per_share": executed - 2.0}}
    }
    snapshot_path.write_text(json.dumps(snapshot, indent=2), encoding="utf-8")

    result = _run_delivery(workspace)
    check = _check(result, "snapshot:valuation-summary")
    assert check["passed"] is False, check
    assert "no executable valuation result" in check["detail"]


def test_valuation_summary_may_publish_only_reference_when_unvalued_rivals_are_explicit(tmp_path: Path):
    workspace = _valid_workspace(tmp_path)
    snapshot_path = workspace / "forecast_snapshot.json"
    snapshot = json.loads(snapshot_path.read_text(encoding="utf-8"))
    snapshot["valuation_summary"]["reference_scenario_id"] = "central_operating_path"
    snapshot["valuation_summary"]["fair_value_by_scenario_id"] = {
        "central_operating_path": snapshot["valuation"]["per_share"]["value_per_share"],
    }
    snapshot_path.write_text(json.dumps(snapshot, indent=2), encoding="utf-8")

    result = _run_delivery(workspace)
    check = _check(result, "snapshot:valuation-summary")
    assert check["passed"] is True, check


def test_valuation_summary_cannot_silently_omit_unvalued_rivals_or_issue_buy_action(tmp_path: Path):
    workspace = _valid_workspace(tmp_path)
    snapshot_path = workspace / "forecast_snapshot.json"
    snapshot = json.loads(snapshot_path.read_text(encoding="utf-8"))
    snapshot["valuation_summary"]["not_valued_scenario_ids"] = []
    snapshot["valuation_summary"]["action"] = "buy"
    snapshot["valuation_summary"]["recommended_buy_price"] = 7.0
    snapshot_path.write_text(json.dumps(snapshot, indent=2), encoding="utf-8")

    result = _run_delivery(workspace)
    check = _check(result, "snapshot:valuation-summary")
    assert check["passed"] is False, check
    assert "explicitly name every unexecuted scenario" in check["detail"]
    assert "cannot express an investment decision" in check["detail"]
