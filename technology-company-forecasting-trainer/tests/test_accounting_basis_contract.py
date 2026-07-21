"""Accounting framework/version choices must be explicit and comparable."""
from __future__ import annotations

import csv
import importlib.util
import json
from pathlib import Path


SKILL = Path(__file__).resolve().parents[1]


def _load_delivery_module():
    path = SKILL / "scripts/validate_delivery.py"
    spec = importlib.util.spec_from_file_location("delivery_accounting_contract", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _basis_record(basis_id: str = "ACCT-US-2026") -> dict:
    return {
        "basis_id": basis_id,
        "framework": "US_GAAP",
        "jurisdiction": "US",
        "version": "FASB ASC effective for fiscal years beginning 2026-01-01",
        "effective_at": "2026-01-01T00:00:00Z",
        "presentation_currency": "USD",
        "major_policy_choices": [
            {
                "policy_id": "revenue-recognition",
                "policy_area": "revenue_recognition",
                "choice": "ASC 606 contract-specific point-in-time or over-time recognition",
                "source_ids": ["S1"],
            }
        ],
    }


def _manifest() -> dict:
    return {
        "as_of": "2026-07-20T23:59:59Z",
        "currency": "USD",
        "accounting_basis": {
            "forecast_basis_id": "ACCT-US-2026",
            "historical_basis_ids": ["ACCT-US-2026"],
            "bases": [_basis_record()],
            "comparability_bridges": [],
        },
    }


def _snapshot(basis_id: str = "ACCT-US-2026") -> dict:
    return {"accounting_basis_id": basis_id}


def _facts(basis_id: str = "ACCT-US-2026") -> list[dict[str, str]]:
    return [{"fact_id": "F1", "accounting_basis_id": basis_id}]


def _problems(manifest, *, snapshot=None, facts=None, sources=None):
    module = _load_delivery_module()
    return module.validate_accounting_basis_contract(
        manifest,
        snapshot=_snapshot() if snapshot is None else snapshot,
        financial_fact_rows=_facts() if facts is None else facts,
        source_ids={"S1"} if sources is None else sources,
    )


def test_typed_accounting_basis_passes_when_history_and_forecast_match():
    assert _problems(_manifest()) == []


def test_bare_gaap_string_is_rejected():
    manifest = _manifest()
    manifest["accounting_basis"] = "GAAP"
    problems = _problems(manifest)
    assert any("typed object" in item for item in problems), problems


def test_framework_and_effective_date_syntax_are_machine_checked():
    manifest = _manifest()
    basis = manifest["accounting_basis"]["bases"][0]
    basis["framework"] = "GAAP"
    basis["effective_at"] = "not-a-date"
    problems = _problems(manifest)
    assert any("framework" in item and "US_GAAP" in item for item in problems), problems
    assert any("effective_at" in item and "ISO" in item for item in problems), problems


def test_presentation_currency_and_major_policy_choices_are_required():
    manifest = _manifest()
    basis = manifest["accounting_basis"]["bases"][0]
    basis["presentation_currency"] = "CNY"
    basis["major_policy_choices"] = []
    problems = _problems(manifest)
    assert any("presentation_currency" in item and "manifest currency" in item for item in problems), problems
    assert any("major_policy_choices" in item for item in problems), problems


def test_accounting_policy_cannot_be_encoded_as_a_company_driver_parameter():
    manifest = _manifest()
    policy = manifest["accounting_basis"]["bases"][0]["major_policy_choices"][0]
    policy["driver_node_id"] = "revenue_growth"
    policy["parameter_value"] = 0.2
    problems = _problems(manifest)
    assert any("company driver parameter" in item for item in problems), problems


def test_snapshot_and_historical_facts_must_use_declared_basis_ids():
    problems = _problems(
        _manifest(),
        snapshot=_snapshot("ACCT-IFRS-2026"),
        facts=_facts("ACCT-PRC-2025"),
    )
    assert any("snapshot.accounting_basis_id" in item for item in problems), problems
    assert any("financial fact F1" in item and "historical_basis_ids" in item for item in problems), problems


def test_cross_basis_history_requires_quantified_comparability_bridge():
    manifest = _manifest()
    manifest["accounting_basis"]["historical_basis_ids"] = ["ACCT-IFRS-2025"]
    manifest["accounting_basis"]["bases"].append(
        {
            **_basis_record("ACCT-IFRS-2025"),
            "framework": "IFRS",
            "jurisdiction": "GB",
            "version": "IFRS Accounting Standards issued at 2025-12-31",
            "effective_at": "2025-01-01T00:00:00Z",
        }
    )
    problems = _problems(manifest, facts=_facts("ACCT-IFRS-2025"))
    assert any("comparability bridge" in item for item in problems), problems


def test_comparability_bridge_must_be_quantified_sourced_and_target_forecast_basis():
    manifest = _manifest()
    accounting = manifest["accounting_basis"]
    accounting["historical_basis_ids"] = ["ACCT-IFRS-2025"]
    accounting["bases"].append(
        {
            **_basis_record("ACCT-IFRS-2025"),
            "framework": "IFRS",
            "jurisdiction": "GB",
            "version": "IFRS Accounting Standards issued at 2025-12-31",
            "effective_at": "2025-01-01T00:00:00Z",
        }
    )
    accounting["comparability_bridges"] = [
        {
            "bridge_id": "BR-IFRS-US",
            "from_basis_id": "ACCT-IFRS-2025",
            "to_basis_id": "ACCT-US-2026",
            "period": "FY2025",
            "source_ids": ["S1"],
            "adjustments": [
                {
                    "adjustment_id": "ADJ-RD",
                    "line_item": "operating_expenses",
                    "amount": 5.0,
                    "currency": "USD",
                    "explanation": "Reverse IFRS development capitalization to the forecast basis.",
                }
            ],
        }
    ]
    assert _problems(manifest, facts=_facts("ACCT-IFRS-2025")) == []

    accounting["comparability_bridges"][0]["adjustments"][0]["amount"] = "qualitative"
    accounting["comparability_bridges"][0]["source_ids"] = []
    problems = _problems(manifest, facts=_facts("ACCT-IFRS-2025"))
    assert any("finite amount" in item for item in problems), problems
    assert any("source_ids" in item for item in problems), problems


def test_cross_basis_bridge_must_cover_each_historical_fact_period():
    """One convenient bridge row must not silently authorize every vintage."""

    manifest = _manifest()
    accounting = manifest["accounting_basis"]
    accounting["historical_basis_ids"] = ["ACCT-IFRS-2025"]
    accounting["bases"].append(
        {
            **_basis_record("ACCT-IFRS-2025"),
            "framework": "IFRS",
            "jurisdiction": "GB",
            "version": "IFRS Accounting Standards issued at 2025-12-31",
            "effective_at": "2025-01-01T00:00:00Z",
        }
    )
    accounting["comparability_bridges"] = [
        {
            "bridge_id": "BR-IFRS-US-FY2025",
            "from_basis_id": "ACCT-IFRS-2025",
            "to_basis_id": "ACCT-US-2026",
            "period": "FY2025",
            "source_ids": ["S1"],
            "adjustments": [
                {
                    "adjustment_id": "ADJ-RD",
                    "line_item": "operating_expenses",
                    "amount": 5.0,
                    "currency": "USD",
                    "explanation": "Reverse development capitalization for FY2025.",
                }
            ],
        }
    ]
    facts = [
        {
            "fact_id": "F-2024",
            "accounting_basis_id": "ACCT-IFRS-2025",
            "fiscal_year": "2024",
            "fiscal_period": "FY",
        },
        {
            "fact_id": "F-2025",
            "accounting_basis_id": "ACCT-IFRS-2025",
            "fiscal_year": "2025",
            "fiscal_period": "FY",
        },
    ]

    problems = _problems(manifest, facts=facts)

    assert any("FY2024" in item and "comparability bridge" in item for item in problems), problems
    assert not any("FY2025" in item and "comparability bridge" in item for item in problems), problems


def test_templates_and_schemas_expose_the_typed_contract():
    manifest = json.loads(
        (SKILL / "assets/templates/run_manifest_template.json").read_text(encoding="utf-8")
    )
    schema = json.loads(
        (SKILL / "assets/schemas/run_manifest.schema.json").read_text(encoding="utf-8")
    )
    snapshot = json.loads(
        (SKILL / "assets/templates/forecast_snapshot_template.json").read_text(encoding="utf-8")
    )
    snapshot_schema = json.loads(
        (SKILL / "assets/schemas/forecast_snapshot.schema.json").read_text(encoding="utf-8")
    )
    assert isinstance(manifest["accounting_basis"], dict)
    assert {"forecast_basis_id", "historical_basis_ids", "bases", "comparability_bridges"} <= set(
        manifest["accounting_basis"]
    )
    accounting_schema = schema["properties"]["accounting_basis"]
    assert accounting_schema["type"] == "object"
    assert set(accounting_schema["required"]) == {
        "forecast_basis_id", "historical_basis_ids", "bases", "comparability_bridges"
    }
    assert "accounting_basis_id" in snapshot
    assert "accounting_basis_id" in snapshot_schema["required"]

    with (SKILL / "assets/templates/financial_fact_ledger_template.csv").open(
        encoding="utf-8-sig", newline=""
    ) as handle:
        assert "accounting_basis_id" in next(csv.reader(handle))


def test_delivery_wires_the_accounting_contract_and_method_documents_boundaries():
    validator = (SKILL / "scripts/validate_delivery.py").read_text(encoding="utf-8")
    assert "validate_accounting_basis_contract(" in validator
    assert '"manifest:accounting-basis"' in validator

    doctrine = (SKILL / "references/model-mechanical-integrity.md").read_text(
        encoding="utf-8"
    ).lower()
    for concept in (
        "us_gaap",
        "ifrs",
        "prc_gaap",
        "effective_at",
        "presentation_currency",
        "major_policy_choices",
        "comparability bridge",
        "company driver parameter",
    ):
        assert concept in doctrine, concept
