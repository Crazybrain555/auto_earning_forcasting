"""Forward Base signals inherit proposition permissions; labels grant none."""

from __future__ import annotations

import csv
import hashlib
import importlib.util
import json
import sys
from pathlib import Path


SKILL = Path(__file__).resolve().parents[1]
SCRIPTS = SKILL / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))
SPEC = importlib.util.spec_from_file_location(
    "forward_evidence_authority_contract",
    SCRIPTS / "validate_forward_evidence_workspace.py",
)
FORWARD = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
SPEC.loader.exec_module(FORWARD)
from validate_delivery import external_observation_review_binding


def _source(
    source_id: str,
    *,
    role: str = "operating_measurement",
    source_type: str = "measurement",
    directness: str = "direct",
    epistemic_class: str = "independent_external_observation",
    authority: str = "third_party",
    independence: str = "independent",
) -> dict:
    if epistemic_class == "independent_external_observation":
        origin_record_kind = "original_measurement_observation"
    elif epistemic_class == "management_statement_or_plan":
        origin_record_kind = "entity_primary_disclosure"
    else:
        origin_record_kind = "expert_or_analyst_interpretation"
    return {
        "source_id": source_id,
        "root_original_source_id": source_id,
        "derived_from_source_id": None,
        "common_origin": False,
        "measurement_method_id": f"method-{source_id}",
        "independence_cluster": f"cluster-{source_id}",
        "publisher": f"Publisher {source_id}",
        "authors": [f"Team {source_id}"],
        "content_hash": "sha256:" + "b" * 64,
        "location": f"https://example.test/{source_id.lower()}",
        "role": role,
        "source_type": source_type,
        "origin_record_kind": origin_record_kind,
        "epistemic_class": epistemic_class,
        "authority": authority,
        "independence": independence,
        "directness": directness,
    }


def _claim(
    claim_id: str,
    source_id: str,
    *,
    claim_type: str = "reported_fact",
    proposition_scope: str = "current_observed_state",
    allowed_use: str = "base_parameter",
    driver: str = "demand",
) -> dict:
    observation_ids = [f"OBS-{source_id}"] if source_id not in {"EXP", "MGT"} else []
    return {
        "claim_id": claim_id,
        "claim_type": claim_type,
        "proposition_scope": proposition_scope,
        "source_ids": [source_id],
        "evidence_links": [{
            "source_id": source_id,
            "relation": "support",
            "evidence_function": "direct_anchor",
            "authority_scope": "The observation measures the named operating construct.",
            "measurement_or_construct_basis": "Accepted units in the named period and perimeter.",
            "incentive_conflict": "No issuer incentive identified.",
            "reconciliation_status": "not_applicable",
            "permission_rationale": "The source and driver definitions match.",
            "observation_ids": observation_ids,
        }],
        "allowed_use": allowed_use,
        "driver_node_ids": [driver],
        "status": "accepted",
    }


def _observation(source_id: str = "OBS", driver: str = "demand") -> dict:
    return {
        "series_id": f"OBS-{source_id}",
        "metric_construct_id": "accepted_customer_units",
        "observation_value": "100",
        "observation_type": "flow",
        "available_at": "2026-07-15T00:00:00Z",
        "vintage_id": f"OBS-{source_id}-v1",
        "source_id": source_id,
        "original_source_id": source_id,
        "measurement_method_id": f"method-{source_id}",
        "period_start": "2026-04-01",
        "period_end": "2026-06-30",
        "frequency": "quarterly",
        "unit": "units",
        "currency": "N/A",
        "entity_scope": "market",
        "product_scope": "named product",
        "geography_scope": "global",
        "population_coverage": "named population",
        "allowed_model_use": "base_parameter",
        "driver_node_ids": driver,
        "status": "accepted",
    }


def _signal(
    *,
    source_id: str = "OBS",
    claim_ids: str = "C-OBS",
    source_family: str = "unseen-proprietary-construct-name",
    driver: str = "demand",
) -> dict[str, str]:
    return {
        "signal_id": "F-OBS",
        "source_id": source_id,
        "claim_ids": claim_ids,
        "source_family": source_family,
        "evidence_role": "fact_anchor",
        "model_driver": driver,
    }


def _review(claim: dict) -> dict:
    classes = {
        "OBS": "independent_external_observation",
        "EXP": "expert_or_analyst_opinion",
    }
    origins = {
        "OBS": "original_measurement_observation",
        "EXP": "expert_or_analyst_interpretation",
    }
    observation_bindings = {}
    if "OBS" in claim["source_ids"]:
        observation_bindings["OBS-OBS"] = {
            **external_observation_review_binding(_observation(), _source("OBS")),
            "classification_rationale": "Reviewed the original measurement and bound locator.",
        }
    return {
        "claim_id": claim["claim_id"],
        "authority_sufficiency": "adequate",
        "permitted_use": claim["allowed_use"],
        "reviewed_source_ids": claim["source_ids"],
        "reviewed_source_epistemic_classes": {
            source_id: classes[source_id] for source_id in claim["source_ids"]
        },
        "reviewed_source_origin_record_kinds": {
            source_id: origins[source_id] for source_id in claim["source_ids"]
        },
        "reviewed_observation_bindings": observation_bindings,
        "rationale": "Independent review accepts this bounded proposition and use.",
    }


def test_template_exposes_claim_binding_without_a_source_family_vocabulary() -> None:
    with (SKILL / "assets/templates/forward_signal_card_template.csv").open(
        encoding="utf-8-sig", newline=""
    ) as handle:
        header = next(csv.reader(handle))
    assert "claim_ids" in header
    assert "source_family" in header


def test_signal_allowed_use_is_a_small_type_contract_not_a_score() -> None:
    for allowed_use in (
        "base_driver",
        "monitor",
        "scenario_only",
        "scenario_probability",
        "technical_bound",
        "actual_only",
    ):
        assert FORWARD.validate_signal_allowed_use("F1", allowed_use) == []
    problems = FORWARD.validate_signal_allowed_use("F1", "optimistic_if_convenient")
    assert any("unknown allowed_use" in item for item in problems), problems


def test_forward_authority_loader_rejects_a_mutated_observation_register(
    tmp_path: Path,
) -> None:
    claim_path = tmp_path / "claim_ledger.jsonl"
    source_path = tmp_path / "source_manifest.json"
    observation_path = tmp_path / "data_series_register.csv"
    claim_path.write_text("{}\n", encoding="utf-8")
    source_path.write_text('{"sources": []}\n', encoding="utf-8")
    observation_path.write_text(
        "series_id,known_bias\nOBS-1,Known coverage limitation\n",
        encoding="utf-8",
    )

    frozen = {
        path.name: "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()
        for path in (claim_path, source_path, observation_path)
    }
    (tmp_path / "research_quality_review.json").write_text(
        json.dumps({
            "builder_id": "builder:case",
            "reviewer_id": "reviewer:independent",
            "independent_of_builder": True,
            "frozen_artifacts": frozen,
            "claim_authority_judgments": [],
        }),
        encoding="utf-8",
    )

    _judgments, initial_problems = (
        FORWARD.load_frozen_claim_authority_judgments(tmp_path, claim_path)
    )
    assert initial_problems == []

    observation_path.write_text(
        "series_id,known_bias\nOBS-1,Newly discovered material undercoverage\n",
        encoding="utf-8",
    )
    _judgments, changed_problems = (
        FORWARD.load_frozen_claim_authority_judgments(tmp_path, claim_path)
    )

    assert any(
        "data_series_register.csv hash mismatch" in problem
        for problem in changed_problems
    ), changed_problems


def test_free_source_family_and_valid_observed_claim_binding_pass() -> None:
    claim = _claim("C-OBS", "OBS")
    assert FORWARD.validate_base_anchor_permissions(
        [_signal()],
        {"OBS": _source("OBS")},
        {"C-OBS": claim},
        {"C-OBS": _review(claim)},
        {"OBS-OBS": _observation()},
    ) == []


def test_management_or_expert_directness_alone_is_not_external_authority() -> None:
    reported = _claim("C-MGT", "MGT")
    problems = FORWARD.validate_base_anchor_permissions(
        [_signal(source_id="MGT", claim_ids="C-MGT")],
        {"MGT": _source(
            "MGT",
            role="management_claim",
            epistemic_class="management_statement_or_plan",
            authority="company",
            independence="first_party",
        )},
        {"C-MGT": reported},
        {},
    )
    assert any("directness cannot become" in item for item in problems), problems

    expert = _claim(
        "C-EXP",
        "EXP",
        claim_type="analyst_assumption",
        proposition_scope="analyst_inference",
    )
    problems = FORWARD.validate_base_anchor_permissions(
        [_signal(source_id="EXP", claim_ids="C-EXP")],
        {"EXP": _source(
            "EXP",
            role="expert_opinion",
            source_type="expert_interview",
            epistemic_class="expert_or_analyst_opinion",
        )},
        {"C-EXP": expert},
        {},
    )
    assert any("frozen independent authority judgment" in item for item in problems), problems


def test_signal_claim_source_or_driver_mismatch_fails() -> None:
    claim = _claim("C-OTHER", "OTHER")
    problems = FORWARD.validate_base_anchor_permissions(
        [_signal(source_id="OBS", claim_ids="C-OTHER")],
        {"OBS": _source("OBS"), "OTHER": _source("OTHER")},
        {"C-OTHER": claim},
        {},
    )
    assert any("does not name source_id OBS" in item for item in problems), problems
    assert any("no source-specific support evidence link" in item for item in problems), problems

    claim = _claim("C-OBS", "OBS", driver="price")
    problems = FORWARD.validate_base_anchor_permissions(
        [_signal()],
        {"OBS": _source("OBS")},
        {"C-OBS": claim},
        {},
    )
    assert any("does not bind model_driver demand" in item for item in problems), problems


def test_reviewed_expert_claim_may_inform_base_but_is_not_the_hard_anchor() -> None:
    observed = _claim("C-OBS", "OBS")
    expert = _claim(
        "C-EXP",
        "EXP",
        claim_type="analyst_assumption",
        proposition_scope="analyst_inference",
    )
    assert FORWARD.validate_base_anchor_permissions(
        [
            _signal(),
            _signal(source_id="EXP", claim_ids="C-EXP"),
        ],
        {
            "OBS": _source("OBS"),
            "EXP": _source(
                "EXP",
                role="expert_opinion",
                source_type="expert_interview",
                epistemic_class="expert_or_analyst_opinion",
            ),
        },
        {"C-OBS": observed, "C-EXP": expert},
        {"C-OBS": _review(observed), "C-EXP": _review(expert)},
        {"OBS-OBS": _observation()},
    ) == []
