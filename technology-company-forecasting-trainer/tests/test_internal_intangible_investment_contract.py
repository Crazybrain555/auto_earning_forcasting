from __future__ import annotations

import copy
import importlib.util
import json
import subprocess
import sys
from pathlib import Path


SCRIPT = Path(__file__).resolve().parents[1] / "scripts/validate_internal_intangibles.py"
SPEC = importlib.util.spec_from_file_location("validate_internal_intangibles", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
SPEC.loader.exec_module(MODULE)


def valid_payload() -> dict:
    return {
        "schema_version": "internal-intangible-investment/v1",
        "materiality_threshold_pct_revenue": 1.0,
        "categories": [
            {
                "category_id": "research_and_development",
                "status": "accepted",
                "accounting_basis_id": "basis://issuer/US_GAAP/2026",
                "reported_policy": "Research is expensed under the issuer policy; qualifying software is separately capitalized.",
                "policy_source_ids": ["S1"],
                "economic_life_source_ids": ["S1", "S2"],
                "allowed_use": "analytical_sensitivity_only",
                "product_or_program": "AI accelerator platform",
                "driver_node_ids": ["ai_units"],
                "commercialization_gate_ids": ["customer_qualification"],
                "scenario_ids": ["bear", "base", "bull"],
                "notes": "Shadow capitalization tests accounting comparability and never overwrites reported GAAP.",
                "cohorts": [
                    {
                        "cohort_id": "rnd-FY2027",
                        "vintage_period": "FY2027",
                        "currency": "USDm",
                        "revenue": 100.0,
                        "reported_expense": 10.0,
                        "reported_capitalized": 0.0,
                        "total_internal_investment": 10.0,
                        "materiality_pct_revenue": 10.0,
                        "economic_life_low": 3.0,
                        "economic_life_base": 4.0,
                        "economic_life_high": 5.0,
                        "attrition_or_obsolescence_rate": 0.10,
                        "maintenance_share": 0.30,
                        "growth_share": 0.70,
                        "opening_shadow_asset": 0.0,
                        "new_shadow_investment": 10.0,
                        "shadow_amortization": 2.0,
                        "shadow_writeoff": 0.0,
                        "closing_shadow_asset": 8.0,
                        "after_tax_expense_addback": 7.5,
                        "after_tax_shadow_amortization": 1.5,
                        "reported_nopat": 12.0,
                        "adjusted_nopat": 18.0,
                        "average_reported_invested_capital": 80.0,
                        "average_shadow_asset": 4.0,
                        "average_adjusted_invested_capital": 84.0,
                        "adjusted_roic": 18.0 / 84.0,
                    }
                ],
            }
        ],
    }


def problems(payload: dict, readiness: str = "research-grade") -> list[str]:
    return MODULE.validate_internal_intangible_schedule(
        payload,
        known_source_ids={"S1", "S2"},
        known_node_ids={"ai_units"},
        scenario_ids={"bear", "base", "bull"},
        accounting_basis_id="basis://issuer/US_GAAP/2026",
        readiness=readiness,
        strict=True,
    )


def test_material_internal_investment_cohort_is_machine_recomputable():
    assert problems(valid_payload()) == []


def test_shadow_schedule_cannot_overwrite_reported_gaap_base():
    payload = valid_payload()
    payload["categories"][0]["allowed_use"] = "base_forecast"
    assert any("analytical sensitivity" in item.lower() for item in problems(payload))


def test_shadow_asset_and_adjusted_return_identities_are_recomputed():
    payload = valid_payload()
    payload["categories"][0]["cohorts"][0]["closing_shadow_asset"] = 10.0
    payload["categories"][0]["cohorts"][0]["adjusted_roic"] = 0.99
    result = problems(payload)
    assert any("shadow asset roll" in item.lower() for item in result)
    assert any("adjusted_roic" in item for item in result)


def test_life_and_maintenance_growth_are_company_specific_not_generic_plugs():
    payload = valid_payload()
    category = payload["categories"][0]
    category["economic_life_source_ids"] = []
    cohort = category["cohorts"][0]
    cohort["economic_life_low"] = 6.0
    cohort["economic_life_base"] = 4.0
    cohort["maintenance_share"] = 0.8
    result = problems(payload)
    assert any("economic_life_source_ids" in item for item in result)
    assert any("life" in item.lower() for item in result)
    assert any("maintenance_share + growth_share" in item for item in result)


def test_not_material_exception_is_numeric_and_below_threshold():
    payload = valid_payload()
    payload["categories"] = [
        {
            "category_id": "customer_acquisition",
            "status": "not_material_with_reason",
            "reason": "Issuer disclosures show immaterial direct acquisition spend relative to revenue.",
            "source_ids": ["S1"],
            "materiality_test": {
                "amount": 0.5,
                "revenue": 100.0,
                "pct_revenue": 0.5,
            },
        }
    ]
    assert problems(payload) == []
    payload["categories"][0]["materiality_test"]["amount"] = 5.0
    assert any("below" in item.lower() for item in problems(payload))


def test_unknown_material_economic_life_caps_research_grade_but_does_not_force_precision():
    payload = valid_payload()
    payload["categories"] = [
        {
            "category_id": "research_and_development",
            "status": "human_required",
            "reason": "No supportable economic life or product-attribution evidence is available.",
            "source_ids": ["S1"],
        }
    ]
    assert any("caps readiness" in item.lower() for item in problems(payload))
    assert problems(payload, readiness="screen-grade") == []


def test_material_internal_investment_links_to_selected_paths_without_a_scenario_quota():
    payload = valid_payload()
    payload["categories"][0]["scenario_ids"] = ["base"]
    result = MODULE.validate_internal_intangible_schedule(
        payload,
        known_source_ids={"S1", "S2"},
        known_node_ids={"ai_units"},
        scenario_ids={"base"},
        accounting_basis_id="basis://issuer/US_GAAP/2026",
        readiness="research-grade",
        strict=True,
    )
    assert result == []


def test_full_company_v2_validator_requires_and_invokes_internal_intangible_schedule():
    root = Path(__file__).resolve().parents[1]
    validator_path = root / "scripts/validate_delivery.py"
    validator_spec = importlib.util.spec_from_file_location("validate_delivery_intangible_test", validator_path)
    validator = importlib.util.module_from_spec(validator_spec)
    assert validator_spec and validator_spec.loader
    validator_spec.loader.exec_module(validator)

    registry = json.loads((root / "assets/artifact_registry.json").read_text(encoding="utf-8"))
    artifact = next(
        row for row in registry["artifacts"]
        if row["path"] == "internal_intangible_investment.json"
    )
    assert artifact["requirement"] == "conditional"
    assert artifact["activation"]["route_any"] == ["internal_intangible"]
    validator_text = validator_path.read_text(encoding="utf-8")
    assert "from validate_internal_intangibles import validate_internal_intangible_schedule" in validator_text
    assert validator_text.count("validate_internal_intangible_schedule(") == 1


def test_scaffold_copies_internal_intangible_template(tmp_path: Path):
    root = Path(__file__).resolve().parents[1]
    workspace = tmp_path / "delivery"
    subprocess.run(
        [
            sys.executable,
            str(root / "scripts/scaffold_delivery.py"),
            "--workspace", str(workspace),
            "--entity", "TEST",
            "--security", "TEST",
            "--as-of", "2026-07-18",
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    payload = json.loads((workspace / "internal_intangible_investment.json").read_text(encoding="utf-8"))
    assert payload["schema_version"] == "internal-intangible-investment/v1"

    registry = json.loads((root / "assets/artifact_registry.json").read_text(encoding="utf-8"))
    artifact = next(
        row for row in registry["artifacts"]
        if row["path"] == "internal_intangible_investment.json"
    )
    assert artifact["template"] == "assets/templates/internal_intangible_investment_template.json"
    assert artifact["scaffold"] is True


def test_trainer_and_live_profiles_ship_the_internal_intangible_contract():
    root = Path(__file__).resolve().parents[1]
    profile = json.loads((root / "assets/profile.json").read_text(encoding="utf-8"))
    assert "validate_internal_intangibles.py" in profile["runtime_scripts"]

    self_test_spec = importlib.util.spec_from_file_location(
        "package_self_test_intangible_test", root / "scripts/package_self_test.py"
    )
    package = importlib.util.module_from_spec(self_test_spec)
    assert self_test_spec and self_test_spec.loader
    self_test_spec.loader.exec_module(package)
    required = {
        "assets/templates/internal_intangible_investment_template.json",
        "references/internal-intangible-investment.md",
    }
    assert required <= set(package.TRAINER_REQUIRED)
    assert required <= set(package.LIVE_REQUIRED)

    for skill_path in (root / "SKILL.md", root / "assets/live_release/SKILL.md"):
        text = skill_path.read_text(encoding="utf-8")
        assert "internal_intangible_investment.json" in text
        assert "references/internal-intangible-investment.md" in text
