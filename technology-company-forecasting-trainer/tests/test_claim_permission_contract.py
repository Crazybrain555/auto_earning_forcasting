"""Claim permissions attach each source to one bounded proposition."""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path


SKILL = Path(__file__).resolve().parents[1]
SCRIPTS = SKILL / "scripts"


def _load_delivery_module():
    if str(SCRIPTS) not in sys.path:
        sys.path.insert(0, str(SCRIPTS))
    path = SCRIPTS / "validate_delivery.py"
    spec = importlib.util.spec_from_file_location("claim_permission_delivery", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _load_research_module():
    if str(SCRIPTS) not in sys.path:
        sys.path.insert(0, str(SCRIPTS))
    path = SCRIPTS / "validate_research_completeness.py"
    spec = importlib.util.spec_from_file_location("claim_permission_research", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _source(source_id: str, *, semantic_role: str) -> dict:
    shared = {
        "source_id": source_id,
        "root_original_source_id": source_id,
        "derived_from_source_id": None,
        "common_origin": False,
        "measurement_method_id": f"method-{source_id}",
        "independence_cluster": f"cluster-{source_id}",
        "directness": "direct",
        "publisher": f"Publisher {source_id}",
        "authors": [f"Team {source_id}"],
        "content_hash": "sha256:" + "a" * 64,
        "location": f"https://example.test/{source_id.lower()}",
    }
    if semantic_role == "management":
        return {
            **shared,
            "source_type": "management_guidance",
            "origin_record_kind": "entity_primary_disclosure",
            "epistemic_class": "management_statement_or_plan",
            "authority": "company",
            "independence": "first_party",
            "role": "management_claim",
        }
    if semantic_role == "expert":
        return {
            **shared,
            "source_type": "expert_interview",
            "origin_record_kind": "expert_or_analyst_interpretation",
            "epistemic_class": "expert_or_analyst_opinion",
            "authority": "third_party",
            "independence": "independent",
            "role": "assumption_support",
        }
    if semantic_role == "analyst":
        return {
            **shared,
            "source_type": "analyst_report",
            "origin_record_kind": "expert_or_analyst_interpretation",
            "epistemic_class": "expert_or_analyst_opinion",
            "authority": "third_party",
            "independence": "independent",
            "role": "assumption_support",
        }
    if semantic_role == "audited_first_party":
        return {
            **shared,
            "source_type": "regulatory_filing",
            "origin_record_kind": "entity_primary_disclosure",
            "epistemic_class": "official_reported_fact",
            "authority": "audited_filing",
            "independence": "first_party",
            "role": "historical_fact",
        }
    if semantic_role == "unrecognized_expert_variant":
        return {
            **shared,
            "source_type": "expert_interview_transcript",
            "origin_record_kind": "expert_or_analyst_interpretation",
            "epistemic_class": "expert_or_analyst_opinion",
            "authority": "third_party",
            "independence": "independent",
            "role": "leading_indicator",
        }
    return {
        **shared,
        "source_type": "independent_measurement",
        "origin_record_kind": "original_measurement_observation",
        "epistemic_class": "independent_external_observation",
        "authority": "third_party",
        "independence": "independent",
        "role": "leading_indicator",
    }


def _link(
    source_id: str,
    *,
    relation: str = "support",
    reconciliation_status: str = "not_applicable",
    evidence_function: str = "direct_anchor",
    observation_ids: list[str] | None = None,
) -> dict:
    if observation_ids is None:
        observation_ids = ["OBS-IND"] if source_id == "IND" else []
    return {
        "source_id": source_id,
        "relation": relation,
        "evidence_function": evidence_function,
        "authority_scope": "The source directly observes the stated construct within its boundary.",
        "measurement_or_construct_basis": "Named operating measure, period, unit, and perimeter.",
        "incentive_conflict": "Issuer incentive disclosed" if source_id == "MGT" else "No issuer incentive identified",
        "reconciliation_status": reconciliation_status,
        "permission_rationale": "The bounded proposition matches the source scope and model use.",
        "observation_ids": observation_ids,
    }


def _observation(
    observation_id: str = "OBS-IND",
    *,
    source_id: str = "IND",
    allowed_model_use: str = "base_parameter",
    driver_node_ids: str = "driver",
) -> dict:
    return {
        "series_id": observation_id,
        "metric_name": "accepted demand",
        "metric_construct_id": "accepted_customer_units",
        "observation_value": "100",
        "observation_type": "flow",
        "available_at": "2026-07-15T00:00:00Z",
        "vintage_id": f"{observation_id}-v1",
        "revision_of_series_id": "none",
        "classification_version": "v1",
        "input_series_ids": "none",
        "source_id": source_id,
        "original_source_id": source_id,
        "independence_cluster": f"cluster-{source_id}",
        "measurement_method_id": f"method-{source_id}",
        "published_at": "2026-07-10T00:00:00Z",
        "retrieved_at": "2026-07-20T00:00:00Z",
        "vintage_at": "2026-07-15T00:00:00Z",
        "revision_at": "2026-07-15T00:00:00Z",
        "period_start": "2026-04-01",
        "period_end": "2026-06-30",
        "frequency": "quarterly",
        "unit": "units",
        "currency": "N/A",
        "metric_definition": "Customer-accepted units in the named period.",
        "entity_scope": "market",
        "product_scope": "named product",
        "geography_scope": "global",
        "population_coverage": "Named measurement population.",
        "transformation": "none",
        "revision_policy": "new vintage",
        "lag_days": "15",
        "known_bias": "Coverage limitation disclosed.",
        "cross_check_series_ids": "",
        "cross_check_result": "",
        "cross_check_bridge_json": "",
        "allowed_model_use": allowed_model_use,
        "driver_node_ids": driver_node_ids,
        "conclusion_critical": "true",
        "status": "accepted",
        "notes": "",
    }


def _claim(
    *,
    claim_type: str = "reported_fact",
    source_ids: list[str] | None = None,
    links: list[dict] | None = None,
    status: str = "accepted",
    proposition_scope: str | None = None,
    forecast_calibration: dict | None = None,
    allowed_use: str = "base_parameter",
) -> dict:
    source_ids = source_ids if source_ids is not None else ["IND"]
    links = links if links is not None else [_link(source_id) for source_id in source_ids]
    if proposition_scope is None:
        proposition_scope = (
            "management_view_or_plan"
            if claim_type == "management_claim"
            else "analyst_inference" if claim_type == "analyst_assumption"
            else "reported_history"
        )
    claim = {
        "claim_id": "C1",
        "text": "Named customer acceptance supports the modeled operating parameter.",
        "claim_type": claim_type,
        "proposition_scope": proposition_scope,
        "source_ids": source_ids,
        "evidence_links": links,
        "allowed_use": allowed_use,
        "driver_node_ids": ["driver"],
        "as_of": "2026-07-20T00:00:00Z",
        "status": status,
    }
    if forecast_calibration is not None:
        claim["forecast_calibration"] = forecast_calibration
    return claim


def _calibration() -> dict:
    return {
        "historical_bias_or_range": "Prior guidance was within -3% to +5% of realized outcomes.",
        "calibration_basis": "Comparable guidance vintages were matched to first-reported actuals.",
        "application_boundary": "Used as management's plan, not proof of customer demand or execution.",
    }


def _review(
    *,
    source_ids: list[str],
    sufficiency: str = "adequate",
    permitted_use: str = "base_parameter",
) -> dict:
    epistemic_classes = {
        "MGT": "management_statement_or_plan",
        "IND": "independent_external_observation",
        "EXP": "expert_or_analyst_opinion",
        "ANL": "expert_or_analyst_opinion",
        "AFIL": "official_reported_fact",
        "EXPX": "expert_or_analyst_opinion",
    }
    origins = {
        "MGT": "entity_primary_disclosure",
        "IND": "original_measurement_observation",
        "EXP": "expert_or_analyst_interpretation",
        "ANL": "expert_or_analyst_interpretation",
        "AFIL": "entity_primary_disclosure",
        "EXPX": "expert_or_analyst_interpretation",
    }
    module = _load_delivery_module()
    observation_bindings = {}
    if "IND" in source_ids:
        observation_bindings["OBS-IND"] = {
            **module.external_observation_review_binding(
                _observation(), _source("IND", semantic_role="measurement")
            ),
            "classification_rationale": (
                "The reviewer inspected the bound original measurement record and its "
                "construct, period, method, locator and source hash."
            ),
        }
    return {
        "claim_id": "C1",
        "authority_sufficiency": sufficiency,
        "permitted_use": permitted_use,
        "reviewed_source_ids": source_ids,
        "reviewed_source_epistemic_classes": {
            source_id: epistemic_classes.get(source_id, "discovery_only")
            for source_id in source_ids
        },
        "reviewed_source_origin_record_kinds": {
            source_id: origins[source_id] for source_id in source_ids
        },
        "reviewed_observation_bindings": observation_bindings,
        "rationale": "Independent reviewer accepted this bounded assumption for Base.",
    }


def _validate(claim: dict, *, review: dict | None = None) -> list[str]:
    module = _load_delivery_module()
    return module.validate_claim_records(
        [claim],
        source_records={
            "MGT": _source("MGT", semantic_role="management"),
            "IND": _source("IND", semantic_role="measurement"),
            "EXP": _source("EXP", semantic_role="expert"),
            "ANL": _source("ANL", semantic_role="analyst"),
            "AFIL": _source("AFIL", semantic_role="audited_first_party"),
            "EXPX": _source("EXPX", semantic_role="unrecognized_expert_variant"),
        },
        graph_node_ids={"driver"},
        main_line_carriers={"driver"},
        authority_judgments={"C1": review} if review else {},
        observation_records={"OBS-IND": _observation()},
    )


def test_claim_schema_and_template_require_proposition_scoped_evidence_links():
    schema = json.loads(
        (SKILL / "assets/schemas/claim_record.schema.json").read_text(encoding="utf-8")
    )
    template = json.loads(
        (SKILL / "assets/templates/claim_ledger_template.jsonl").read_text(encoding="utf-8")
    )

    assert "evidence_links" in schema["required"]
    assert "proposition_scope" in schema["required"]
    link_schema = schema["properties"]["evidence_links"]["items"]
    assert set(link_schema["required"]) >= {
        "source_id",
        "relation",
        "evidence_function",
        "authority_scope",
        "measurement_or_construct_basis",
        "incentive_conflict",
        "reconciliation_status",
        "permission_rationale",
        "observation_ids",
    }
    assert link_schema["properties"]["relation"]["enum"] == [
        "support",
        "contradict",
        "context",
    ]
    assert "evidence_links" in template


def test_source_schema_template_and_review_contract_require_epistemic_class():
    schema = json.loads(
        (SKILL / "assets/schemas/source_record.schema.json").read_text(encoding="utf-8")
    )
    source_template = json.loads(
        (SKILL / "assets/templates/source_manifest_template.json").read_text(
            encoding="utf-8"
        )
    )
    review_template = json.loads(
        (SKILL / "assets/templates/research_quality_review_template.json").read_text(
            encoding="utf-8"
        )
    )

    assert source_template["schema_version"] == "3.0"
    assert "epistemic_class" in schema["required"]
    assert "origin_record_kind" in schema["required"]
    assert schema["properties"]["epistemic_class"]["enum"] == [
        "official_reported_fact",
        "independent_external_observation",
        "management_statement_or_plan",
        "expert_or_analyst_opinion",
        "technical_evidence",
        "discovery_only",
    ]
    assert (
        source_template["sources"][0]["epistemic_class"]
        == "official_reported_fact"
    )
    assert "reviewed_source_epistemic_classes" in review_template[
        "claim_authority_judgment_contract"
    ]["required_fields"]
    assert "reviewed_source_origin_record_kinds" in review_template[
        "claim_authority_judgment_contract"
    ]["required_fields"]
    assert "reviewed_observation_bindings" in review_template[
        "claim_authority_judgment_contract"
    ]["required_fields"]


def test_source_ids_and_evidence_links_must_match_and_resolve():
    claim = _claim(source_ids=["IND"], links=[_link("MGT")])
    problems = _validate(claim)
    assert any("source_ids and evidence_links must match" in item for item in problems), problems

    claim = _claim(source_ids=["UNKNOWN"], links=[_link("UNKNOWN")])
    problems = _validate(claim)
    assert any("unknown evidence-link source ids" in item for item in problems), problems


def test_unresolved_contradiction_cannot_masquerade_as_accepted():
    claim = _claim(
        source_ids=["IND", "MGT"],
        links=[_link("IND"), _link("MGT", relation="contradict", reconciliation_status="unresolved")],
    )
    problems = _validate(claim)
    assert any("unresolved contradiction cannot be accepted" in item for item in problems), problems

    claim["evidence_links"][1]["reconciliation_status"] = "reconciled"
    assert _validate(claim, review=_review(source_ids=["IND", "MGT"])) == []


def test_management_plan_is_direct_anchor_not_an_independent_source_quota():
    claim = _claim(claim_type="management_claim", source_ids=["MGT"])
    problems = _validate(claim, review=_review(source_ids=["MGT"]))
    assert any("management forecast calibration" in item for item in problems), problems

    claim = _claim(
        claim_type="management_claim",
        source_ids=["MGT"],
        forecast_calibration=_calibration(),
    )
    assert _validate(claim, review=_review(source_ids=["MGT"])) == []


def test_management_claim_crossing_into_execution_needs_a_named_test_not_a_source_count():
    claim = _claim(
        claim_type="management_claim",
        source_ids=["MGT"],
        proposition_scope="future_execution",
        forecast_calibration=_calibration(),
    )
    problems = _validate(claim, review=_review(source_ids=["MGT"]))
    assert any("future execution or external state" in item for item in problems), problems

    claim = _claim(
        claim_type="management_claim",
        source_ids=["MGT", "IND"],
        links=[_link("MGT"), _link("IND", evidence_function="context_only")],
        proposition_scope="future_execution",
        forecast_calibration=_calibration(),
    )
    problems = _validate(claim, review=_review(source_ids=["MGT", "IND"]))
    assert any("future execution or external state" in item for item in problems), problems

    claim = _claim(
        claim_type="management_claim",
        source_ids=["MGT", "IND"],
        links=[_link("MGT"), _link("IND", evidence_function="causal_test")],
        proposition_scope="future_execution",
        forecast_calibration=_calibration(),
    )
    assert _validate(claim, review=_review(source_ids=["MGT", "IND"])) == []


def test_subjective_external_views_cannot_directly_prove_future_execution_or_external_state():
    for source_id in ("EXP", "ANL"):
        for proposition_scope in ("future_execution", "external_state"):
            claim = _claim(
                claim_type="analyst_assumption",
                source_ids=[source_id],
                proposition_scope=proposition_scope,
                allowed_use="base_parameter",
            )
            problems = _validate(
                claim,
                review=_review(source_ids=[source_id]),
            )
            assert any(
                "independent external factual source" in item for item in problems
            ), (source_id, proposition_scope, problems)

            claim["source_ids"] = [source_id, "IND"]
            claim["evidence_links"] = [
                _link(source_id),
                _link("IND", evidence_function="context_only"),
            ]
            problems = _validate(
                claim,
                review=_review(source_ids=[source_id, "IND"]),
            )
            assert any(
                "independent external factual source" in item for item in problems
            ), (source_id, proposition_scope, problems)

            claim["evidence_links"][1] = _link(
                "IND", evidence_function="external_test"
            )
            assert _validate(
                claim,
                review=_review(source_ids=[source_id, "IND"]),
            ) == []


def test_reported_fact_is_incompatible_with_a_future_or_external_proposition():
    for proposition_scope in ("future_execution", "external_state"):
        claim = _claim(
            claim_type="reported_fact",
            source_ids=["AFIL"],
            proposition_scope=proposition_scope,
            allowed_use="base_parameter",
        )
        problems = _validate(claim)
        assert any(
            "reported_fact" in item and "incompatible" in item
            for item in problems
        ), (proposition_scope, problems)

    historical = _claim(
        claim_type="reported_fact",
        source_ids=["AFIL"],
        proposition_scope="reported_history",
        allowed_use="base_parameter",
    )
    assert _validate(historical) == []


def test_every_model_changing_future_proposition_needs_an_external_factual_test():
    for proposition_scope in ("future_execution", "external_state"):
        claim = _claim(
            claim_type="derived_fact",
            source_ids=["EXPX"],
            proposition_scope=proposition_scope,
            allowed_use="base_parameter",
        )
        problems = _validate(claim)
        assert any(
            "independent external factual source" in item for item in problems
        ), (proposition_scope, problems)

        claim["source_ids"] = ["EXPX", "IND"]
        claim["evidence_links"] = [
            _link("EXPX", relation="context", evidence_function="context_only"),
            _link("IND", evidence_function="context_only"),
        ]
        problems = _validate(claim)
        assert any(
            "independent external factual source" in item for item in problems
        ), (proposition_scope, problems)

        claim["evidence_links"][1] = _link(
            "IND", evidence_function="causal_test"
        )
        assert _validate(claim, review=_review(source_ids=["EXPX", "IND"])) == []


def test_source_type_variant_cannot_turn_opinion_into_an_external_factual_test():
    claim = _claim(
        claim_type="derived_fact",
        source_ids=["EXPX"],
        links=[_link("EXPX", evidence_function="causal_test")],
        proposition_scope="future_execution",
        allowed_use="base_parameter",
    )

    problems = _validate(claim, review=_review(source_ids=["EXPX"]))

    assert any(
        "independent_external_observation" in item for item in problems
    ), problems


def test_self_declared_epistemic_class_cannot_override_the_origin_record_kind():
    module = _load_delivery_module()
    source = _source("EXPX", semantic_role="unrecognized_expert_variant")
    source.update({
        "epistemic_class": "independent_external_observation",
        "authority": "third_party",
        "independence": "independent",
        "directness": "direct",
    })
    claim = _claim(
        claim_type="derived_fact",
        source_ids=["EXPX"],
        links=[_link("EXPX", evidence_function="causal_test")],
        proposition_scope="future_execution",
    )

    problems = module.validate_claim_records(
        [claim],
        source_records={"EXPX": source},
        graph_node_ids={"driver"},
        main_line_carriers={"driver"},
        authority_judgments={},
        observation_records={},
    )

    assert any("origin_record_kind" in item for item in problems), problems


def test_external_test_needs_a_separate_bound_observation_record():
    module = _load_delivery_module()
    source = _source("EXPX", semantic_role="unrecognized_expert_variant")
    source.update({
        "origin_record_kind": "original_measurement_observation",
        "epistemic_class": "independent_external_observation",
        "authority": "third_party",
        "independence": "independent",
        "directness": "direct",
    })
    claim = _claim(
        claim_type="derived_fact",
        source_ids=["EXPX"],
        links=[_link("EXPX", evidence_function="external_test")],
        proposition_scope="external_state",
    )

    problems = module.validate_claim_records(
        [claim],
        source_records={"EXPX": source},
        graph_node_ids={"driver"},
        main_line_carriers={"driver"},
        authority_judgments={},
        observation_records={},
    )

    assert any("observation_ids" in item for item in problems), problems


def test_predictive_external_test_requires_a_frozen_review_even_for_a_measurement():
    claim = _claim(
        claim_type="derived_fact",
        source_ids=["IND"],
        links=[_link("IND", evidence_function="external_test")],
        proposition_scope="external_state",
        allowed_use="base_parameter",
    )

    problems = _validate(claim)
    assert any("frozen independent authority judgment" in item for item in problems), problems
    assert _validate(claim, review=_review(source_ids=["IND"])) == []


def test_source_record_must_declare_a_controlled_epistemic_class():
    module = _load_delivery_module()
    source = _source("IND", semantic_role="measurement")
    del source["epistemic_class"]
    problems = module.validate_claim_records(
        [_claim(source_ids=["IND"])],
        source_records={"IND": source},
        graph_node_ids={"driver"},
        main_line_carriers={"driver"},
        authority_judgments={},
    )

    assert any("epistemic_class" in item for item in problems), problems


def test_frozen_review_binds_the_exact_source_epistemic_class():
    claim = _claim(claim_type="analyst_assumption", source_ids=["IND"])
    review = _review(source_ids=["IND"])
    review["reviewed_source_epistemic_classes"]["IND"] = (
        "expert_or_analyst_opinion"
    )

    problems = _validate(claim, review=review)

    assert any("reviewed_source_epistemic_classes" in item for item in problems), problems


def test_frozen_review_binds_source_origin_and_observation_fingerprint():
    claim = _claim(claim_type="analyst_assumption", source_ids=["IND"])
    review = _review(source_ids=["IND"])
    review["reviewed_source_origin_record_kinds"]["IND"] = (
        "expert_or_analyst_interpretation"
    )
    problems = _validate(claim, review=review)
    assert any("reviewed_source_origin_record_kinds" in item for item in problems), problems

    review = _review(source_ids=["IND"])
    review["reviewed_observation_bindings"]["OBS-IND"]["fingerprint"] = (
        "sha256:" + "0" * 64
    )
    problems = _validate(claim, review=review)
    assert any("reviewed_observation_bindings" in item for item in problems), problems


def test_frozen_review_binds_known_bias_as_part_of_the_full_observation_semantics():
    module = _load_delivery_module()
    claim = _claim(claim_type="analyst_assumption", source_ids=["IND"])
    review = _review(source_ids=["IND"])
    changed_observation = _observation()
    changed_observation["known_bias"] = (
        "Coverage excludes a newly identified customer cohort."
    )

    problems = module.validate_claim_records(
        [claim],
        source_records={"IND": _source("IND", semantic_role="measurement")},
        graph_node_ids={"driver"},
        main_line_carriers={"driver"},
        authority_judgments={"C1": review},
        observation_records={"OBS-IND": changed_observation},
    )

    assert any("reviewed_observation_bindings" in item for item in problems), problems


def test_bounded_expert_scenario_and_technical_opinion_do_not_need_an_execution_test():
    for proposition_scope, allowed_use, claim_type in (
        ("scenario_only", "scenario_only", "scenario"),
        ("technical_boundary", "technical_bound", "analyst_assumption"),
    ):
        claim = _claim(
            claim_type=claim_type,
            source_ids=["EXP"],
            proposition_scope=proposition_scope,
            allowed_use=allowed_use,
        )
        assert _validate(
            claim,
            review=_review(source_ids=["EXP"], permitted_use=allowed_use),
        ) == []


def test_analyst_authorship_does_not_turn_a_current_fact_into_future_proof():
    claim = _claim(
        claim_type="analyst_assumption",
        source_ids=["IND"],
        proposition_scope="future_execution",
        allowed_use="base_parameter",
    )
    problems = _validate(claim, review=_review(source_ids=["IND"]))
    assert any("independent external factual source" in item for item in problems), problems

    claim["evidence_links"] = [
        _link("IND", evidence_function="causal_test")
    ]
    assert _validate(claim, review=_review(source_ids=["IND"])) == []


def test_analyst_assumption_enters_base_only_after_claim_specific_independent_review():
    claim = _claim(claim_type="analyst_assumption")
    problems = _validate(claim)
    assert any("frozen independent authority judgment" in item for item in problems), problems

    assert _validate(claim, review=_review(source_ids=["IND"])) == []

    problems = _validate(
        claim,
        review=_review(source_ids=["IND"], sufficiency="limited"),
    )
    assert any("does not permit base_parameter" in item for item in problems), problems


def test_subjective_claims_cannot_evade_review_by_renaming_model_changing_use():
    for allowed_use in (
        "historical_anchor",
        "technical_bound",
        "scenario_only",
    ):
        claim = _claim(
            claim_type="analyst_assumption",
            allowed_use=allowed_use,
        )
        problems = _validate(claim)
        assert any(
            "frozen independent authority judgment" in item for item in problems
        ), (allowed_use, problems)
        assert _validate(
            claim,
            review=_review(source_ids=["IND"], permitted_use=allowed_use),
        ) == []


def test_monitoring_and_discovery_do_not_require_model_permission_review():
    for allowed_use in ("monitoring_only", "discovery_only"):
        claim = _claim(
            claim_type="analyst_assumption",
            allowed_use=allowed_use,
        )
        assert _validate(claim) == []


def test_future_management_execution_needs_a_causal_test_for_any_model_use():
    for allowed_use in ("historical_anchor", "technical_bound", "scenario_only"):
        claim = _claim(
            claim_type="management_claim",
            source_ids=["MGT"],
            proposition_scope="future_execution",
            allowed_use=allowed_use,
        )
        review = _review(source_ids=["MGT"], permitted_use=allowed_use)
        problems = _validate(claim, review=review)
        assert any("model-changing use" in item for item in problems), (
            allowed_use,
            problems,
        )
        claim["evidence_links"] = [
            _link("MGT", evidence_function="causal_test")
        ]
        problems = _validate(claim, review=review)
        assert any("management cannot test its own execution" in item for item in problems), (
            allowed_use,
            problems,
        )

        claim["source_ids"] = ["MGT", "IND"]
        claim["evidence_links"] = [
            _link("MGT"),
            _link("IND", evidence_function="causal_test"),
        ]
        review = _review(
            source_ids=["MGT", "IND"],
            permitted_use=allowed_use,
        )
        assert _validate(claim, review=review) == []


def test_management_calibration_is_bounded_to_quantitative_reference_use():
    claim = _claim(
        claim_type="management_claim",
        source_ids=["MGT"],
        allowed_use="historical_anchor",
    )
    assert _validate(
        claim,
        review=_review(source_ids=["MGT"], permitted_use="historical_anchor"),
    ) == []


def test_reported_fact_label_cannot_launder_expert_subjectivity_into_model_uses():
    for allowed_use in ("historical_anchor", "technical_bound", "scenario_only"):
        claim = _claim(
            claim_type="reported_fact",
            source_ids=["EXP"],
            proposition_scope="reported_history",
            allowed_use=allowed_use,
        )
        problems = _validate(claim)
        assert any("incompatible" in item and "expert" in item for item in problems), (
            allowed_use,
            problems,
        )
        assert any(
            "frozen independent authority judgment" in item for item in problems
        ), (allowed_use, problems)

        reviewed = _validate(
            claim,
            review=_review(source_ids=["EXP"], permitted_use=allowed_use),
        )
        assert any("incompatible" in item and "expert" in item for item in reviewed), (
            allowed_use,
            reviewed,
        )


def test_management_source_cannot_hide_future_execution_behind_reported_fact():
    claim = _claim(
        claim_type="reported_fact",
        source_ids=["MGT"],
        proposition_scope="future_execution",
        allowed_use="scenario_only",
    )
    problems = _validate(
        claim,
        review=_review(source_ids=["MGT"], permitted_use="scenario_only"),
    )
    assert any("incompatible" in item and "management" in item for item in problems), problems
    assert any("independent external" in item for item in problems), problems


def test_research_review_binds_authority_judgment_to_claim_and_sources():
    module = _load_research_module()
    delivery = _load_delivery_module()
    observation_binding = delivery.external_observation_review_binding(
        _observation(), _source("IND", semantic_role="measurement")
    )
    valid = _review(source_ids=["IND"])
    problems, judgments = module.validate_claim_authority_judgments(
        [valid],
        known_claim_ids={"C1"},
        known_source_ids={"IND"},
        known_source_epistemic_classes={
            "IND": "independent_external_observation"
        },
        known_source_origin_record_kinds={
            "IND": "original_measurement_observation"
        },
        known_observation_bindings={"OBS-IND": observation_binding},
        claim_observation_ids={"C1": {"OBS-IND"}},
    )
    assert problems == []
    assert judgments == {"C1": valid}

    invalid = dict(valid)
    invalid["claim_id"] = "UNKNOWN"
    invalid["reviewed_source_ids"] = ["UNKNOWN_SOURCE"]
    problems, _ = module.validate_claim_authority_judgments(
        [invalid],
        known_claim_ids={"C1"},
        known_source_ids={"IND"},
        known_source_epistemic_classes={
            "IND": "independent_external_observation"
        },
        known_source_origin_record_kinds={
            "IND": "original_measurement_observation"
        },
        known_observation_bindings={"OBS-IND": observation_binding},
        claim_observation_ids={"C1": {"OBS-IND"}},
    )
    assert any("unknown claim_id" in item for item in problems), problems
    assert any("unknown reviewed_source_ids" in item for item in problems), problems
