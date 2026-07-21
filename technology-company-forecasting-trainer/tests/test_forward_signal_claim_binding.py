"""Every model-changing SignalCard has proposition-level permission lineage."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest


SKILL = Path(__file__).resolve().parents[1]
SCRIPTS = SKILL / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))
SPEC = importlib.util.spec_from_file_location(
    "forward_signal_claim_binding", SCRIPTS / "validate_forward_evidence_workspace.py"
)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def _source(source_id: str, *, semantic_role: str) -> dict:
    if semantic_role == "technical":
        return {
            "source_id": source_id,
            "source_type": "peer_reviewed_paper",
            "origin_record_kind": "scholarly_or_engineering_record",
            "epistemic_class": "technical_evidence",
            "authority": "peer_reviewed",
            "independence": "independent",
            "role": "technical_boundary",
            "directness": "direct",
        }
    if semantic_role == "expert":
        return {
            "source_id": source_id,
            "source_type": "expert_interview",
            "origin_record_kind": "expert_or_analyst_interpretation",
            "epistemic_class": "expert_or_analyst_opinion",
            "authority": "third_party",
            "independence": "independent",
            "role": "assumption_support",
            "directness": "inferred",
        }
    return {
        "source_id": source_id,
        "source_type": "filing",
        "origin_record_kind": "entity_primary_disclosure",
        "epistemic_class": "official_reported_fact",
        "authority": "audited_filing",
        "independence": "first_party",
        "role": "historical_fact",
        "directness": "direct",
    }


def _link(source_id: str) -> dict:
    return {
        "source_id": source_id,
        "relation": "support",
        "evidence_function": "direct_anchor",
        "observation_ids": [],
    }


def _claim(
    claim_id: str,
    *,
    claim_type: str,
    allowed_use: str,
    source_id: str,
    driver: str = "driver",
) -> dict:
    return {
        "claim_id": claim_id,
        "claim_type": claim_type,
        "proposition_scope": (
            "technical_boundary"
            if claim_type == "technical_boundary"
            else "analyst_inference" if claim_type == "analyst_assumption"
            else "reported_history"
        ),
        "source_ids": [source_id],
        "evidence_links": [_link(source_id)],
        "allowed_use": allowed_use,
        "driver_node_ids": [driver],
        "status": "accepted",
    }


def _row(allowed_use: str, *, source_id: str = "FILING", claim_ids: str = "") -> dict:
    return {
        "signal_id": f"SIG-{allowed_use}",
        "source_id": source_id,
        "claim_ids": claim_ids,
        "allowed_use": allowed_use,
        "model_driver": "driver",
        "evidence_role": "state_signal",
    }


def _validate(
    rows: list[dict],
    *,
    claims: dict[str, dict] | None = None,
    reviews: dict[str, dict] | None = None,
) -> list[str]:
    validator = getattr(MODULE, "validate_model_changing_signal_permissions", None)
    assert callable(validator), (
        "forward validator must expose one permission gate for every "
        "model-changing SignalCard use"
    )
    return validator(
        rows,
        {
            "FILING": _source("FILING", semantic_role="fact"),
            "PAPER": _source("PAPER", semantic_role="technical"),
            "EXP": _source("EXP", semantic_role="expert"),
        },
        claims or {},
        reviews or {},
    )


@pytest.mark.parametrize(
    "allowed_use",
    ("base_driver", "base_parameter", "historical_anchor", "technical_bound", "scenario_only"),
)
def test_each_model_changing_use_requires_an_accepted_bound_claim(allowed_use: str):
    problems = _validate([_row(allowed_use)])
    assert any("requires claim_ids" in item for item in problems), problems


def test_binding_requires_same_source_support_driver_and_compatible_use():
    claim = _claim(
        "C1",
        claim_type="reported_fact",
        allowed_use="historical_anchor",
        source_id="FILING",
        driver="different_driver",
    )
    problems = _validate(
        [_row("technical_bound", source_id="PAPER", claim_ids="C1")],
        claims={"C1": claim},
    )
    assert any("does not permit technical_bound" in item for item in problems), problems
    assert any("does not name source_id PAPER" in item for item in problems), problems
    assert any("no source-specific support" in item for item in problems), problems
    assert any("does not bind model_driver driver" in item for item in problems), problems


def test_subjective_scenario_signal_requires_matching_frozen_permission():
    claim = _claim(
        "C1",
        claim_type="analyst_assumption",
        allowed_use="scenario_only",
        source_id="EXP",
    )
    row = _row("scenario_only", source_id="EXP", claim_ids="C1")
    problems = _validate([row], claims={"C1": claim})
    assert any("frozen independent authority judgment" in item for item in problems), problems

    review = {
        "claim_id": "C1",
        "authority_sufficiency": "adequate",
        "permitted_use": "scenario_only",
        "reviewed_source_ids": ["EXP"],
        "reviewed_source_epistemic_classes": {
            "EXP": "expert_or_analyst_opinion"
        },
        "reviewed_source_origin_record_kinds": {
            "EXP": "expert_or_analyst_interpretation"
        },
        "reviewed_observation_bindings": {},
        "rationale": "Independent reviewer accepted this bounded rival-state input.",
    }
    assert _validate([row], claims={"C1": claim}, reviews={"C1": review}) == []


def test_monitor_signal_is_a_non_model_use_and_needs_no_claim_binding():
    assert _validate([_row("monitor", source_id="EXP")]) == []
