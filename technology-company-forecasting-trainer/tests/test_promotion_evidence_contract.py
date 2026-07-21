"""A production release must carry anti-drift evidence, not only compile."""
from __future__ import annotations

import json
import hashlib
import importlib.util
import shutil
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path


SKILL = Path(__file__).resolve().parents[1]
BUILDER = SKILL / "scripts/build_live_release.py"
VALIDATOR = SKILL / "scripts/validate_promotion_evidence.py"
PROMOTION_SPEC = importlib.util.spec_from_file_location("promotion_contract", VALIDATOR)
assert PROMOTION_SPEC and PROMOTION_SPEC.loader
PROMOTION = importlib.util.module_from_spec(PROMOTION_SPEC)
PROMOTION_SPEC.loader.exec_module(PROMOTION)


def _sha256(path: Path) -> str:
    return "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()


def _tree_sha256(root: Path) -> str:
    digest = hashlib.sha256()
    for path in sorted(item for item in root.rglob("*") if item.is_file()):
        rel = path.relative_to(root)
        if "__pycache__" in rel.parts or path.suffix in {".pyc", ".pyo"}:
            continue
        digest.update(rel.as_posix().encode("utf-8"))
        digest.update(b"\0")
        digest.update(hashlib.sha256(path.read_bytes()).digest())
    return "sha256:" + digest.hexdigest()


def _write_json(path: Path, value: object) -> None:
    path.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")


def _actuals_validation_receipt(case_id: str, now_dt: datetime) -> dict:
    entity_id = f"ENTITY-{case_id}"
    source_id = f"{case_id}-OFFICIAL-FILING"
    common = {
        "entity_id": entity_id,
        "period": "FY+1",
        "fiscal_period_start": "2025-01-01",
        "fiscal_period_end": "2025-12-31",
        "currency": "USD",
        "unit": "USD millions",
        "accounting_basis": "US GAAP",
        "accounting_basis_id": "us-gaap",
        "consolidation_perimeter": "Consolidated group including controlled subsidiaries",
        "official_source_ids": [source_id],
    }
    observations = [
        {
            **common,
            "observation_id": f"{case_id}|FY+1|revenue",
            "metric": "revenue",
            "value": 100.0,
            "fact_scope": "consolidated_revenue",
            "sign_convention": "income_positive",
            "source_fact_label": "Revenue",
            "source_fact_anchor": "financial-statements/revenue",
            "source_fact_value_text": "100.0",
            "fact_origin": "direct_official_reported_fact",
            "reported_precision": {"basis": "exact", "rounding_increment_in_reported_unit": 0.0},
        },
        {
            **common,
            "observation_id": f"{case_id}|FY+1|operating-profit",
            "metric": "operating_profit",
            "value": 18.0,
            "fact_scope": "consolidated_operating_profit",
            "sign_convention": "income_positive",
            "source_fact_label": "Income from operations",
            "source_fact_anchor": "financial-statements/operating-profit",
            "source_fact_value_text": "18.0",
            "fact_origin": "direct_official_reported_fact",
            "reported_precision": {"basis": "exact", "rounding_increment_in_reported_unit": 0.0},
        },
        {
            **common,
            "observation_id": f"{case_id}|FY+1|attributable-net-income",
            "metric": "gaap_net_income_attributable",
            "value": 10.0,
            "fact_scope": "attributable_to_parent_shareholders",
            "sign_convention": "income_positive",
            "source_fact_label": "Net income attributable to parent shareholders",
            "source_fact_anchor": "financial-statements/attributable-net-income",
            "source_fact_value_text": "10.0",
            "fact_origin": "direct_official_reported_fact",
            "reported_precision": {"basis": "exact", "rounding_increment_in_reported_unit": 0.0},
            "attribution_method": "direct_official_attributable_fact",
        },
    ]
    core = {
        "contract_version": "training_actuals/3.2",
        "status": "locally_consistent_untrusted",
        "case_id": case_id,
        "entity_id": entity_id,
        "actuals_sha256": "sha256:" + hashlib.sha256(case_id.encode("utf-8")).hexdigest(),
        "sealed_at": (now_dt - timedelta(days=5)).isoformat(),
        "retrieved_at": (now_dt - timedelta(days=2)).isoformat(),
        "information_cutoff_at": (now_dt - timedelta(days=3)).isoformat(),
        "official_source_ids": [source_id],
        "official_sources": [{
            "source_id": source_id,
            "issuer_or_regulator": f"Issuer {case_id}",
            "document_type": "audited annual filing",
            "title": f"{case_id} fiscal-year filing",
            "published_at": (now_dt - timedelta(days=4)).isoformat(),
            "locator": f"https://issuer.example/{case_id}/annual-filing",
            "content_sha256": "sha256:" + hashlib.sha256(
                f"{case_id}:official-filing".encode("utf-8")
            ).hexdigest(),
            "origin_class": "issuer_statutory_filing",
        }],
        "derived_reconciliation_tolerances": {
            "method": "sum_half_reported_rounding_increments",
            "by_period": {},
        },
        "validated_observations": sorted(
            observations,
            key=lambda row: (row["entity_id"], row["period"], row["metric"]),
        ),
    }
    canonical = json.dumps(
        core, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode("utf-8")
    return {**core, "receipt_id": "sha256:" + hashlib.sha256(canonical).hexdigest()}


def _rewrite_artifact(evidence: Path, section: str, value: object) -> None:
    payload = json.loads(evidence.read_text(encoding="utf-8"))
    artifact = Path(payload[section]["artifact"])
    _write_json(artifact, value)
    payload[section]["artifact_sha256"] = _sha256(artifact)
    _write_json(evidence, payload)


def _refresh_judgment_binding(evidence: Path, role: str, artifact: Path) -> None:
    promotion = json.loads(evidence.read_text(encoding="utf-8"))
    judgment_path = Path(promotion["independent_judgment"]["artifact"])
    judgment = json.loads(judgment_path.read_text(encoding="utf-8"))
    ref = next(
        item
        for item in judgment["provenance"]["reviewed_artifacts"]
        if item["role"] == role
    )
    ref["sha256"] = _sha256(artifact)
    _write_json(judgment_path, judgment)
    promotion["independent_judgment"]["artifact_sha256"] = _sha256(judgment_path)
    _write_json(evidence, promotion)


def _mutate_holdout_evaluation(evidence: Path, role: str, index: int, mutate) -> None:
    promotion = json.loads(evidence.read_text(encoding="utf-8"))
    holdout_path = Path(promotion["holdout"]["artifact"])
    holdout = json.loads(holdout_path.read_text(encoding="utf-8"))
    ref = holdout["provenance"][f"{role}_evaluation_artifacts"][index]
    evaluation_path = Path(ref["path"])
    evaluation = json.loads(evaluation_path.read_text(encoding="utf-8"))
    mutate(evaluation)
    _write_json(evaluation_path, evaluation)
    ref["sha256"] = _sha256(evaluation_path)
    _write_json(holdout_path, holdout)
    promotion["holdout"]["artifact_sha256"] = _sha256(holdout_path)
    _write_json(evidence, promotion)
    _refresh_judgment_binding(evidence, "holdout", holdout_path)


def _run(tmp_path: Path, *extra: str, skill_root: Path = SKILL):
    return subprocess.run(
        [
            sys.executable,
            str(BUILDER),
            "--trainer-skill-root",
            str(skill_root),
            "--output-root",
            str(tmp_path / "technology-company-profit-forecasting"),
            *extra,
        ],
        capture_output=True,
        text=True,
    )


def _validate(evidence: Path):
    return subprocess.run(
        [
            sys.executable,
            str(VALIDATOR),
            "--evidence",
            str(evidence),
            "--skill-root",
            str(SKILL),
        ],
        capture_output=True,
        text=True,
    )


def _reflection(path: Path) -> None:
    path.write_text(
        """# Reflection

## Symmetric persistence challenger
- `error_observed`: Candidate method can extend a trend without a symmetric challenger.
- `internal_attribution`: STRUCTURE; the forecast needs an outside-view challenge.
- `external_sources`:
  - `source_id`: S1 | `category`: academic_primary | `independence_cluster`: fama_french | `originality`: original_academic | `location`: https://doi.org/10.1086/209638 | `method_claim`: profitability mean reversion is an outside-view hypothesis | `misuse_boundary`: population speed is not a company coefficient
  - `source_id`: S2 | `category`: original_author_practitioner | `independence_cluster`: mauboussin | `originality`: original_author | `location`: https://www.morganstanley.com/im/publication/insights/articles/article_measuringthemoat.pdf | `method_claim`: competitive response and ROIC duration must be causal | `misuse_boundary`: a checklist does not prove persistence
- `outside_view`: Use a symmetric reference-class challenger and explain company departures.
- `agreement`: refines the internal diagnosis.
- `rule_adopted`: challenger is symmetric and conditional; no universal fade coefficient.
- `support_status`: externally_supported_method; company parameters remain provisional.
- `validation_plan`: three distinct mechanisms, untouched cases, direct revenue/operating-profit/net-income errors and signed bias.
- `challenger_baselines`: trailing organic growth, guidance-bias-adjusted bridge and cycle-normal margin.
- `generative_change`: replace the asymmetric trend extension in the shared forecast stage.
- `assurance_angle`: causal generalization under an untouched symmetric challenger.
- `complexity_delta`: replace one directional rule with one symmetric rule; retire if ablation adds no information.
- `independent_review_plan`: deliver frozen inputs to a separate reviewer session before any builder rebuttal.
""",
        encoding="utf-8",
    )


def _evidence(
    tmp_path: Path,
    *,
    change_type: str = "method_research",
    skill_root: Path = SKILL,
) -> Path:
    reflection = tmp_path / "method_reflection.md"
    _reflection(reflection)

    now_dt = datetime.now(timezone.utc)
    now = now_dt.isoformat()
    orchestration_receipt = {
        "assurance_boundary": "orchestration_receipt_only_not_cryptographic_identity",
        "receipt_id": "orchestration-receipt://promotion-fixture",
        "orchestrator": "pytest-fixture",
        "reviewer_session_id": "session:independent-reviewer",
        "reviewer_task_id": "task:promotion-review",
        "builder_session_id": "session:candidate-builder",
        "frozen_inputs_delivered_at": (now_dt - timedelta(minutes=4)).isoformat(),
        "review_started_at": (now_dt - timedelta(minutes=3)).isoformat(),
        "initial_conclusion_at": (now_dt - timedelta(minutes=2)).isoformat(),
        "review_completed_at": now,
        "receipt_issued_at": now,
        "builder_rebuttal": {
            "status": "not_provided",
            "provided_at": None,
        },
    }
    candidate_identity = {
        "trainer_tree_sha256": _tree_sha256(skill_root),
        "method_version": "working-tree-fixture",
    }
    test_command_argv = PROMOTION.promotion_test_argv(sys.executable)
    test_command = " ".join(test_command_argv)
    test_report = tmp_path / "test-run.json"
    _write_json(
        test_report,
        {
            "schema_version": "1.0",
            "artifact_type": "test_run",
            "run_id": "test-run-fixture",
            "started_at": now,
            "finished_at": now,
            "tested_tree_sha256": _tree_sha256(skill_root),
            "provenance": {
                "runner": "pytest",
                "command_argv": test_command_argv,
                "cwd": str(skill_root),
                "source_revision": candidate_identity["method_version"],
            },
            "summary": {
                "exit_code": 0,
                "collected": 12,
                "passed": 12,
                "failed": 0,
                "errors": 0,
                "skipped": 0,
            },
        },
    )

    blind_candidate = tmp_path / "blind-candidate.json"
    blind_challenger = tmp_path / "blind-challenger.json"
    _write_json(
        blind_candidate,
        {
            "case_id": "BLIND-1",
            "result": "candidate",
            "candidate_identity": dict(candidate_identity),
        },
    )
    _write_json(blind_challenger, {"case_id": "BLIND-1", "result": "challenger"})
    assertion_spec = tmp_path / "blind-assertions.json"
    _write_json(
        assertion_spec,
        {
            "case_id": "BLIND-1",
            "assertions": [
                {"index": 1, "text": "Separates facts from assumptions", "critical": True},
                {"index": 2, "text": "Reconciles the profit bridge", "critical": True},
            ],
        },
    )
    candidate_grading = tmp_path / "blind-candidate-grading.json"
    challenger_grading = tmp_path / "blind-challenger-grading.json"
    _write_json(
        candidate_grading,
        {
            "case_id": "BLIND-1",
            "role": "candidate",
            "grader_id": "independent-fixture-evaluator",
            "graded_at": now,
            "candidate_identity": dict(candidate_identity),
            "assertion_results": [
                {"index": 1, "text": "Separates facts from assumptions", "passed": True, "reason": "met"},
                {"index": 2, "text": "Reconciles the profit bridge", "passed": True, "reason": "met"},
            ],
        },
    )
    _write_json(
        challenger_grading,
        {
            "case_id": "BLIND-1",
            "role": "challenger",
            "grader_id": "independent-fixture-evaluator",
            "graded_at": now,
            "assertion_results": [
                {"index": 1, "text": "Separates facts from assumptions", "passed": True, "reason": "met"},
                {"index": 2, "text": "Reconciles the profit bridge", "passed": False, "reason": "missing bridge"},
            ],
        },
    )
    blind_report = tmp_path / "blind-eval-report.json"
    _write_json(
        blind_report,
        {
            "schema_version": "1.0",
            "artifact_type": "blind_evaluation",
            "evaluation_id": "blind-eval-fixture",
            "generated_at": now,
            "provenance": {
                "evaluator_id": "independent-fixture-evaluator",
                "evaluation_method": "locked contract comparison",
                "candidate_id": "candidate-v2",
                "challenger_id": "challenger-v1",
                "candidate_identity": dict(candidate_identity),
                "case_ids": ["BLIND-1"],
                "input_artifacts": [
                    {"role": "candidate", "path": str(blind_candidate), "sha256": _sha256(blind_candidate)},
                    {"role": "challenger", "path": str(blind_challenger), "sha256": _sha256(blind_challenger)},
                ],
                "assertion_specs": [
                    {"case_id": "BLIND-1", "path": str(assertion_spec), "sha256": _sha256(assertion_spec)}
                ],
                "grading_artifacts": [
                    {
                        "role": "candidate",
                        "case_id": "BLIND-1",
                        "path": str(candidate_grading),
                        "sha256": _sha256(candidate_grading),
                    },
                    {
                        "role": "challenger",
                        "case_id": "BLIND-1",
                        "path": str(challenger_grading),
                        "sha256": _sha256(challenger_grading),
                    },
                ],
            },
            "summary": {"status": "pass", "critical_failures": 0, "candidate_not_worse": True},
        },
    )
    evidence = {
        "schema_version": "1.0",
        "change_type": change_type,
        "candidate_identity": dict(candidate_identity),
        "method_reflection": str(reflection),
        "test_suite": {
            "suite_id": PROMOTION.PROMOTION_TEST_SUITE_ID,
            "command": test_command,
            "passed": True,
            "failed": 0,
            "artifact": str(test_report),
            "artifact_sha256": _sha256(test_report),
        },
        "profit_accuracy_claim": "not_established" if change_type == "method_research" else "validated_on_holdout",
        "blind_evaluation": {
            "status": "pass",
            "critical_failures": 0,
            "candidate_not_worse": True,
            "artifact": str(blind_report),
            "artifact_sha256": _sha256(blind_report),
        },
    }
    holdout_report: Path | None = None
    if change_type == "historical_training":
        case_ids = ["HOLDOUT-A", "HOLDOUT-B"]
        candidate_artifacts = []
        challenger_artifacts = []
        for case_id in case_ids:
            for role, error, bias, interval, target in (
                ("candidate", 0.08, 0.01, 0.12, candidate_artifacts),
                ("challenger", 0.09, 0.02, 0.13, challenger_artifacts),
            ):
                evaluation = tmp_path / f"{case_id}-{role}-evaluation.json"
                metrics = {
                    "revenue_mape": error,
                    "operating_profit_scaled_mae": error,
                    "net_income_scaled_mae": error,
                    "revenue_signed_bias": bias,
                    "operating_profit_signed_bias": bias,
                    "net_income_signed_bias": bias,
                    "revenue_interval_score": interval,
                    "operating_profit_interval_score": interval,
                    "net_income_interval_score": interval,
                }
                _write_json(
                    evaluation,
                    {
                        "case_id": case_id,
                        "seal_hash": "sha256:" + ("a" if role == "candidate" else "b") * 64,
                        "hash_verified": True,
                        "forecast_seal_receipt_status": "verified",
                        "seal_reverified_after_scoring": True,
                        "actuals_retrieved_after_seal": True,
                        "scored_at": now,
                        "actuals_validation_receipt": _actuals_validation_receipt(case_id, now_dt),
                        **(
                            {"candidate_identity": dict(candidate_identity)}
                            if role == "candidate"
                            else {}
                        ),
                        "metrics": metrics,
                        "metric_observation_counts": {name: 3 for name in metrics},
                    },
                )
                target.append({"case_id": case_id, "path": str(evaluation), "sha256": _sha256(evaluation)})
        metrics = {
            name: {
                "candidate_error": 0.08,
                "challenger_error": 0.09,
                "candidate_not_worse": True,
                "signed_bias": 0.01,
                "interval_score": 0.12,
            }
            for name in ("revenue", "operating_profit", "net_income")
        }
        holdout_report = tmp_path / "holdout-comparison.json"
        _write_json(
            holdout_report,
            {
                "schema_version": "1.0",
                "artifact_type": "holdout_comparison",
                "evaluation_id": "holdout-comparison-fixture",
                "generated_at": now,
                "provenance": {
                    "candidate_id": "candidate-v2",
                    "challenger_id": "challenger-v1",
                    "candidate_identity": dict(candidate_identity),
                    "case_ids": case_ids,
                    "evaluation_units": [
                        {
                            "case_id": "HOLDOUT-A",
                            "entity_cluster_id": "ENTITY-HOLDOUT-A",
                            "as_of": "2024-12-31T00:00:00Z",
                            "target_period_start": "2025-01-01",
                            "target_period_end": "2025-12-31",
                            "horizon_id": "FY+1",
                            "horizon_period_ids": ["FY+1"],
                            "mechanism": "unit-volume-price-cost",
                            "cycle_or_lifecycle_regime": "balanced",
                        },
                        {
                            "case_id": "HOLDOUT-B",
                            "entity_cluster_id": "ENTITY-HOLDOUT-B",
                            "as_of": "2024-12-31T00:00:00Z",
                            "target_period_start": "2025-01-01",
                            "target_period_end": "2025-12-31",
                            "horizon_id": "FY+1",
                            "horizon_period_ids": ["FY+1"],
                            "mechanism": "recurring-contract",
                            "cycle_or_lifecycle_regime": "mature-growth",
                        },
                    ],
                    "candidate_evaluation_artifacts": candidate_artifacts,
                    "challenger_evaluation_artifacts": challenger_artifacts,
                },
                "summary": {
                    "status": "pass",
                    "right_reason_ok": True,
                    "new_systematic_bias": False,
                    "entity_cluster_count": 2,
                    "case_count": 2,
                    "leave_one_entity_out": {
                        name: {
                            "all_candidate_not_worse": True,
                            "max_candidate_minus_challenger_error": -0.01,
                        }
                        for name in ("revenue", "operating_profit", "net_income")
                    },
                    "metrics": metrics,
                },
            },
        )
        evidence["holdout"] = {
            "status": "pass",
            "right_reason_ok": True,
            "new_systematic_bias": False,
            "metrics": metrics,
            "artifact": str(holdout_report),
            "artifact_sha256": _sha256(holdout_report),
        }
    reviewed_artifacts = [
        {"role": "method_reflection", "path": str(reflection), "sha256": _sha256(reflection)},
        {"role": "test_suite", "path": str(test_report), "sha256": _sha256(test_report)},
        {"role": "blind_evaluation", "path": str(blind_report), "sha256": _sha256(blind_report)},
    ]
    if holdout_report is not None:
        reviewed_artifacts.append(
            {"role": "holdout", "path": str(holdout_report), "sha256": _sha256(holdout_report)}
        )
    judgment_report = tmp_path / "promotion-independent-judgment.json"
    _write_json(
        judgment_report,
        {
            "schema_version": "1.0",
            "artifact_type": "promotion_judgment",
            "judgment_id": "promotion-judgment-fixture",
            "generated_at": now,
            "provenance": {
                "reviewer_id": "independent-promotion-reviewer",
                "builder_id": "candidate-builder",
                "independent_of_builder": True,
                "candidate_identity": dict(candidate_identity),
                "orchestration_receipt": orchestration_receipt,
                "reviewed_artifacts": reviewed_artifacts,
            },
            "hard_failure_findings": {
                "leakage": [],
                "accounting_or_definition_error": [],
                "unauthorized_evidence": [],
                "outcome_fitting": [],
                "critical_failure": [],
            },
            "judgments": {
                "causal_quality": {
                    "conclusion": "supports",
                    "reasoning": "The change addresses the diagnosed causal failure rather than an outcome value.",
                    "evidence_refs": ["method_reflection", "blind_evaluation"],
                },
                "generalization": {
                    "conclusion": "supports" if change_type == "historical_training" else "not_established",
                    "reasoning": "Holdout regimes support transfer." if change_type == "historical_training" else "Accuracy remains explicitly unestablished.",
                    "evidence_refs": ["holdout"] if change_type == "historical_training" else ["blind_evaluation"],
                },
                "complexity": {
                    "conclusion": "proportionate",
                    "reasoning": "The shared method change replaces an overlapping rule and adds no score target.",
                    "evidence_refs": ["method_reflection", "test_suite"],
                },
                "disagreements": {
                    "conclusion": "bounded",
                    "reasoning": "Remaining disagreements are named and do not hide a hard failure.",
                    "evidence_refs": ["blind_evaluation"],
                },
            },
            "numeric_diagnostics_assessment": {
                "conclusion": "supports" if change_type == "historical_training" else "not_applicable",
                "worse_metrics": [],
                "worse_leave_one_out": [],
                "reasoning": "Metrics are read jointly by target and regime; no scalar objective is used.",
                "decision_effect": "No hard failure is inferred from the diagnostic panel.",
            },
            "overall": {
                "decision": "approve",
                "rationale": "Causal quality, bounded complexity and honest uncertainty support promotion.",
                "profit_accuracy_claim": evidence["profit_accuracy_claim"],
            },
        },
    )
    evidence["independent_judgment"] = {
        "status": "approve",
        "artifact": str(judgment_report),
        "artifact_sha256": _sha256(judgment_report),
    }
    path = tmp_path / "promotion_evidence.json"
    path.write_text(json.dumps(evidence), encoding="utf-8")
    return path


def _runtime_skill(tmp_path: Path, test_body: str) -> Path:
    runtime_skill = tmp_path / "trainer-runtime"
    shutil.copytree(
        SKILL,
        runtime_skill,
        ignore=shutil.ignore_patterns("__pycache__", "*.pyc", ".pytest_cache"),
    )
    shutil.rmtree(runtime_skill / "tests")
    (runtime_skill / "tests").mkdir()
    (runtime_skill / "tests" / "test_promotion_runtime.py").write_text(
        test_body,
        encoding="utf-8",
    )
    return runtime_skill


def test_plain_build_is_candidate_not_release(tmp_path):
    result = _run(tmp_path)
    assert result.returncode == 0, result.stdout + result.stderr
    payload = json.loads(result.stdout)
    assert payload["release_eligible"] is False
    assert payload["release_is_git_commit"] is False


def test_promote_requires_evidence(tmp_path):
    result = _run(tmp_path, "--self-test", "--promote")
    assert result.returncode != 0
    assert "promotion" in (result.stdout + result.stderr).lower()


def test_promote_requires_self_test_even_with_valid_evidence(tmp_path):
    evidence = _evidence(tmp_path)
    result = _run(tmp_path, "--promote", "--promotion-evidence", str(evidence))
    assert result.returncode != 0
    assert "self-test" in (result.stdout + result.stderr).lower()


def test_release_rejects_self_reported_test_result_without_artifact(tmp_path):
    evidence = _evidence(tmp_path)
    obj = json.loads(evidence.read_text(encoding="utf-8"))
    del obj["test_suite"]["artifact"]
    del obj["test_suite"]["artifact_sha256"]
    _write_json(evidence, obj)
    result = _validate(evidence)
    assert result.returncode != 0
    assert "test_suite.artifact" in (result.stdout + result.stderr)


def test_release_rejects_test_artifact_for_a_different_tree(tmp_path):
    evidence = _evidence(tmp_path)
    obj = json.loads(evidence.read_text(encoding="utf-8"))
    artifact = Path(obj["test_suite"]["artifact"])
    report = json.loads(artifact.read_text(encoding="utf-8"))
    report["tested_tree_sha256"] = "sha256:" + "0" * 64
    _write_json(artifact, report)
    obj["test_suite"]["artifact_sha256"] = _sha256(artifact)
    _write_json(evidence, obj)
    result = _validate(evidence)
    assert result.returncode != 0
    assert "tested_tree_sha256" in (result.stdout + result.stderr)


def test_release_rejects_promotion_identity_replayed_on_a_different_tree(tmp_path):
    evidence = _evidence(tmp_path)
    promotion = json.loads(evidence.read_text(encoding="utf-8"))
    promotion["candidate_identity"]["trainer_tree_sha256"] = "sha256:" + "0" * 64
    _write_json(evidence, promotion)

    result = _validate(evidence)

    assert result.returncode != 0
    assert "candidate_identity.trainer_tree_sha256" in (result.stdout + result.stderr)


def test_release_rejects_nonempty_test_shell_without_command_result(tmp_path):
    evidence = _evidence(tmp_path)
    _rewrite_artifact(evidence, "test_suite", {"status": "pass"})
    result = _validate(evidence)
    assert result.returncode != 0
    assert "test_suite.artifact" in (result.stdout + result.stderr)


def test_release_rejects_test_command_not_bound_to_artifact(tmp_path):
    evidence = _evidence(tmp_path)
    obj = json.loads(evidence.read_text(encoding="utf-8"))
    obj["test_suite"]["command"] = "echo forged-pass"
    _write_json(evidence, obj)
    result = _validate(evidence)
    assert result.returncode != 0
    assert "test_suite.command" in (result.stdout + result.stderr)


def test_promote_rejects_forged_pass_when_allowlisted_suite_actually_fails(tmp_path):
    runtime_skill = _runtime_skill(
        tmp_path,
        "def test_actual_failure():\n    assert False, 'real allowlisted test failed'\n",
    )
    evidence = _evidence(tmp_path, skill_root=runtime_skill)
    result = _run(
        tmp_path,
        "--self-test",
        "--promote",
        "--promotion-evidence",
        str(evidence),
        skill_root=runtime_skill,
    )
    assert result.returncode != 0
    assert "allowlisted promotion test suite failed" in (result.stdout + result.stderr).lower()


def test_promote_executes_allowlisted_real_suite(tmp_path):
    marker = tmp_path / "allowlisted-suite-ran"
    runtime_skill = _runtime_skill(
        tmp_path,
        "from pathlib import Path\n\n"
        "def test_actual_pass():\n"
        f"    Path({str(marker)!r}).write_text('ran', encoding='utf-8')\n"
        "    assert True\n",
    )
    evidence = _evidence(tmp_path, skill_root=runtime_skill)
    result = _run(
        tmp_path,
        "--self-test",
        "--promote",
        "--promotion-evidence",
        str(evidence),
        skill_root=runtime_skill,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert marker.read_text(encoding="utf-8") == "ran"
    payload = json.loads(result.stdout)
    assert payload["promotion_test_run"]["suite_id"] == PROMOTION.PROMOTION_TEST_SUITE_ID
    assert payload["promotion_test_run"]["exit_code"] == 0


def test_promote_rejects_non_allowlisted_command_without_executing_it(tmp_path):
    marker = tmp_path / "arbitrary-command-ran"
    runtime_skill = _runtime_skill(tmp_path, "def test_actual_pass():\n    assert True\n")
    evidence = _evidence(tmp_path, skill_root=runtime_skill)
    payload = json.loads(evidence.read_text(encoding="utf-8"))
    payload["test_suite"]["suite_id"] = "shell"
    payload["test_suite"]["command"] = f"touch {marker}"
    _write_json(evidence, payload)
    result = _run(
        tmp_path,
        "--self-test",
        "--promote",
        "--promotion-evidence",
        str(evidence),
        skill_root=runtime_skill,
    )
    assert result.returncode != 0
    assert "allowlisted" in (result.stdout + result.stderr).lower()
    assert not marker.exists()


def test_release_rejects_nonempty_blind_shell_without_provenance(tmp_path):
    evidence = _evidence(tmp_path)
    _rewrite_artifact(evidence, "blind_evaluation", {"status": "pass"})
    result = _validate(evidence)
    assert result.returncode != 0
    assert "blind_evaluation.artifact" in (result.stdout + result.stderr)


def test_release_rejects_blind_input_digest_mismatch(tmp_path):
    evidence = _evidence(tmp_path)
    obj = json.loads(evidence.read_text(encoding="utf-8"))
    artifact = Path(obj["blind_evaluation"]["artifact"])
    report = json.loads(artifact.read_text(encoding="utf-8"))
    report["provenance"]["input_artifacts"][0]["sha256"] = "sha256:" + "0" * 64
    _write_json(artifact, report)
    obj["blind_evaluation"]["artifact_sha256"] = _sha256(artifact)
    _write_json(evidence, obj)
    result = _validate(evidence)
    assert result.returncode != 0
    assert "blind_evaluation.artifact provenance" in (result.stdout + result.stderr)


def test_release_rejects_blind_candidate_input_replayed_from_another_method(tmp_path):
    evidence = _evidence(tmp_path)
    promotion = json.loads(evidence.read_text(encoding="utf-8"))
    report_path = Path(promotion["blind_evaluation"]["artifact"])
    report = json.loads(report_path.read_text(encoding="utf-8"))
    candidate_ref = next(
        ref for ref in report["provenance"]["input_artifacts"] if ref["role"] == "candidate"
    )
    candidate_path = Path(candidate_ref["path"])
    candidate = json.loads(candidate_path.read_text(encoding="utf-8"))
    candidate["candidate_identity"]["method_version"] = "replayed-old-method"
    _write_json(candidate_path, candidate)
    candidate_ref["sha256"] = _sha256(candidate_path)
    _write_json(report_path, report)
    promotion["blind_evaluation"]["artifact_sha256"] = _sha256(report_path)
    _write_json(evidence, promotion)
    _refresh_judgment_binding(evidence, "blind_evaluation", report_path)

    result = _validate(evidence)

    assert result.returncode != 0
    assert "blind_evaluation candidate input" in (result.stdout + result.stderr)


def test_release_accepts_original_eval_metrics_as_blind_inputs(tmp_path):
    """Promotion can bind immutable raw eval outputs instead of rewritten wrappers."""

    evidence = _evidence(tmp_path)
    promotion = json.loads(evidence.read_text(encoding="utf-8"))
    report_path = Path(promotion["blind_evaluation"]["artifact"])
    report = json.loads(report_path.read_text(encoding="utf-8"))
    for ref in report["provenance"]["input_artifacts"]:
        path = Path(ref["path"])
        payload = json.loads(path.read_text(encoding="utf-8"))
        payload["eval_name"] = payload.pop("case_id")
        _write_json(path, payload)
        ref["sha256"] = _sha256(path)
    _write_json(report_path, report)
    promotion["blind_evaluation"]["artifact_sha256"] = _sha256(report_path)
    _write_json(evidence, promotion)
    _refresh_judgment_binding(evidence, "blind_evaluation", report_path)

    result = _validate(evidence)
    assert result.returncode == 0, result.stdout + result.stderr


def test_release_rejects_blind_summary_forged_over_failed_raw_assertion(tmp_path):
    evidence = _evidence(tmp_path)
    promotion = json.loads(evidence.read_text(encoding="utf-8"))
    report_path = Path(promotion["blind_evaluation"]["artifact"])
    report = json.loads(report_path.read_text(encoding="utf-8"))
    candidate_ref = next(
        ref for ref in report["provenance"]["grading_artifacts"] if ref["role"] == "candidate"
    )
    grading_path = Path(candidate_ref["path"])
    grading = json.loads(grading_path.read_text(encoding="utf-8"))
    grading["assertion_results"][1]["passed"] = False
    grading["assertion_results"][1]["reason"] = "candidate actually missed the bridge"
    _write_json(grading_path, grading)
    candidate_ref["sha256"] = _sha256(grading_path)
    _write_json(report_path, report)
    promotion["blind_evaluation"]["artifact_sha256"] = _sha256(report_path)
    _write_json(evidence, promotion)

    result = _validate(evidence)
    assert result.returncode != 0
    assert "derived from fixed assertion results" in (result.stdout + result.stderr).lower()


def test_release_rejects_blind_grading_that_changes_fixed_assertion_text(tmp_path):
    evidence = _evidence(tmp_path)
    promotion = json.loads(evidence.read_text(encoding="utf-8"))
    report_path = Path(promotion["blind_evaluation"]["artifact"])
    report = json.loads(report_path.read_text(encoding="utf-8"))
    candidate_ref = next(
        ref for ref in report["provenance"]["grading_artifacts"] if ref["role"] == "candidate"
    )
    grading_path = Path(candidate_ref["path"])
    grading = json.loads(grading_path.read_text(encoding="utf-8"))
    grading["assertion_results"][0]["text"] = "An easier substituted assertion"
    _write_json(grading_path, grading)
    candidate_ref["sha256"] = _sha256(grading_path)
    _write_json(report_path, report)
    promotion["blind_evaluation"]["artifact_sha256"] = _sha256(report_path)
    _write_json(evidence, promotion)

    result = _validate(evidence)
    assert result.returncode != 0
    assert "fixed assertion" in (result.stdout + result.stderr).lower()


def test_release_requires_bound_blind_assertion_specs(tmp_path):
    evidence = _evidence(tmp_path)
    promotion = json.loads(evidence.read_text(encoding="utf-8"))
    report_path = Path(promotion["blind_evaluation"]["artifact"])
    report = json.loads(report_path.read_text(encoding="utf-8"))
    del report["provenance"]["assertion_specs"]
    _write_json(report_path, report)
    promotion["blind_evaluation"]["artifact_sha256"] = _sha256(report_path)
    _write_json(evidence, promotion)

    result = _validate(evidence)
    assert result.returncode != 0
    assert "assertion_specs" in (result.stdout + result.stderr)


def test_release_accepts_bound_original_eval_metadata_and_grading_artifacts(tmp_path):
    evidence = _evidence(tmp_path)
    promotion = json.loads(evidence.read_text(encoding="utf-8"))
    report_path = Path(promotion["blind_evaluation"]["artifact"])
    report = json.loads(report_path.read_text(encoding="utf-8"))

    spec_ref = report["provenance"]["assertion_specs"][0]
    spec_path = Path(spec_ref["path"])
    fixed_text = ["Separates facts from assumptions", "Reconciles the profit bridge"]
    _write_json(
        spec_path,
        {"eval_id": 1, "eval_name": "BLIND-1", "assertions": fixed_text},
    )
    spec_ref["sha256"] = _sha256(spec_path)

    for ref in report["provenance"]["grading_artifacts"]:
        grading_path = Path(ref["path"])
        passed = [True, True] if ref["role"] == "candidate" else [True, False]
        original_grading = {
                "expectations": [
                    {"text": text, "passed": status, "evidence": "anchored grading evidence"}
                    for text, status in zip(fixed_text, passed)
                ],
                "summary": {
                    "passed": sum(passed),
                    "failed": len(passed) - sum(passed),
                    "total": len(passed),
                    "pass_rate": sum(passed) / len(passed),
                },
                "timing": {
                    "executor_start": "2026-07-20T14:00:00Z",
                    "executor_end": "2026-07-20T14:01:00Z",
                    "executor_duration_seconds": 60.0,
                },
            }
        if ref["role"] == "candidate":
            original_grading["candidate_identity"] = dict(
                promotion["candidate_identity"]
            )
        _write_json(grading_path, original_grading)
        ref["sha256"] = _sha256(grading_path)

    _write_json(report_path, report)
    promotion["blind_evaluation"]["artifact_sha256"] = _sha256(report_path)
    _write_json(evidence, promotion)
    _refresh_judgment_binding(evidence, "blind_evaluation", report_path)
    result = _validate(evidence)
    assert result.returncode == 0, result.stdout + result.stderr


def test_historical_release_rejects_nonempty_holdout_shell_without_provenance(tmp_path):
    evidence = _evidence(tmp_path, change_type="historical_training")
    _rewrite_artifact(evidence, "holdout", {"status": "pass"})
    result = _validate(evidence)
    assert result.returncode != 0
    assert "holdout.artifact" in (result.stdout + result.stderr)


def test_historical_release_requires_typed_economically_independent_evaluation_units(tmp_path):
    evidence = _evidence(tmp_path, change_type="historical_training")
    promotion = json.loads(evidence.read_text(encoding="utf-8"))
    artifact = Path(promotion["holdout"]["artifact"])
    report = json.loads(artifact.read_text(encoding="utf-8"))
    del report["provenance"]["evaluation_units"]
    _write_json(artifact, report)
    promotion["holdout"]["artifact_sha256"] = _sha256(artifact)
    _write_json(evidence, promotion)

    result = _validate(evidence)
    assert result.returncode != 0
    assert "evaluation_units" in (result.stdout + result.stderr)


def test_historical_release_does_not_count_two_cutoffs_of_one_entity_as_two_holdouts(tmp_path):
    evidence = _evidence(tmp_path, change_type="historical_training")
    promotion = json.loads(evidence.read_text(encoding="utf-8"))
    artifact = Path(promotion["holdout"]["artifact"])
    report = json.loads(artifact.read_text(encoding="utf-8"))
    report["provenance"]["evaluation_units"][1]["entity_cluster_id"] = "ENTITY-HOLDOUT-A"
    _write_json(artifact, report)
    promotion["holdout"]["artifact_sha256"] = _sha256(artifact)
    _write_json(evidence, promotion)

    result = _validate(evidence)
    assert result.returncode != 0
    assert "two distinct entity clusters" in (result.stdout + result.stderr).lower()


def test_holdout_unit_entity_and_fiscal_dates_are_bound_to_actuals_receipt(tmp_path):
    evidence = _evidence(tmp_path, change_type="historical_training")
    promotion = json.loads(evidence.read_text(encoding="utf-8"))
    artifact = Path(promotion["holdout"]["artifact"])
    report = json.loads(artifact.read_text(encoding="utf-8"))
    unit = report["provenance"]["evaluation_units"][0]
    unit["entity_cluster_id"] = "GHOST-ENTITY"
    unit["target_period_end"] = "2099-12-31"
    unit["horizon_period_ids"] = ["FY+99"]
    _write_json(artifact, report)
    promotion["holdout"]["artifact_sha256"] = _sha256(artifact)
    _write_json(evidence, promotion)

    result = _validate(evidence)
    output = result.stdout + result.stderr
    assert result.returncode != 0
    assert "does not match the actuals receipt entity_id" in output
    assert "target_period_end does not match" in output
    assert "horizon_period_ids do not match" in output


def test_historical_release_rejects_holdout_evaluation_digest_mismatch(tmp_path):
    evidence = _evidence(tmp_path, change_type="historical_training")
    obj = json.loads(evidence.read_text(encoding="utf-8"))
    artifact = Path(obj["holdout"]["artifact"])
    report = json.loads(artifact.read_text(encoding="utf-8"))
    report["provenance"]["candidate_evaluation_artifacts"][0]["sha256"] = "sha256:" + "0" * 64
    _write_json(artifact, report)
    obj["holdout"]["artifact_sha256"] = _sha256(artifact)
    _write_json(evidence, obj)
    result = _validate(evidence)
    assert result.returncode != 0
    assert "holdout.artifact provenance" in (result.stdout + result.stderr)


def test_historical_release_rejects_candidate_evaluation_replayed_from_another_tree(tmp_path):
    evidence = _evidence(tmp_path, change_type="historical_training")
    promotion = json.loads(evidence.read_text(encoding="utf-8"))
    holdout_path = Path(promotion["holdout"]["artifact"])
    holdout = json.loads(holdout_path.read_text(encoding="utf-8"))
    candidate_ref = holdout["provenance"]["candidate_evaluation_artifacts"][0]
    evaluation_path = Path(candidate_ref["path"])
    evaluation = json.loads(evaluation_path.read_text(encoding="utf-8"))
    evaluation["candidate_identity"]["trainer_tree_sha256"] = "sha256:" + "0" * 64
    _write_json(evaluation_path, evaluation)
    candidate_ref["sha256"] = _sha256(evaluation_path)
    _write_json(holdout_path, holdout)
    promotion["holdout"]["artifact_sha256"] = _sha256(holdout_path)
    _write_json(evidence, promotion)
    _refresh_judgment_binding(evidence, "holdout", holdout_path)

    result = _validate(evidence)

    assert result.returncode != 0
    assert "holdout candidate evaluation" in (result.stdout + result.stderr)


def test_historical_release_rejects_summary_not_derived_from_artifact(tmp_path):
    evidence = _evidence(tmp_path, change_type="historical_training")
    obj = json.loads(evidence.read_text(encoding="utf-8"))
    obj["holdout"]["metrics"]["revenue"]["candidate_error"] = 0.001
    _write_json(evidence, obj)
    result = _validate(evidence)
    assert result.returncode != 0
    assert "holdout.metrics" in (result.stdout + result.stderr)


def test_historical_diagnostics_accept_one_noisy_metric_but_release_waits_for_trusted_actuals(tmp_path):
    """A noisy slice is not a veto, but local Actuals still cannot prove truth."""

    evidence = _evidence(tmp_path, change_type="historical_training")
    promotion = json.loads(evidence.read_text(encoding="utf-8"))
    holdout_path = Path(promotion["holdout"]["artifact"])
    holdout = json.loads(holdout_path.read_text(encoding="utf-8"))

    for ref in holdout["provenance"]["candidate_evaluation_artifacts"]:
        evaluation_path = Path(ref["path"])
        evaluation = json.loads(evaluation_path.read_text(encoding="utf-8"))
        evaluation["metrics"]["operating_profit_scaled_mae"] = 0.10
        _write_json(evaluation_path, evaluation)
        ref["sha256"] = _sha256(evaluation_path)

    noisy_metric = {
        "candidate_error": 0.10,
        "challenger_error": 0.09,
        "candidate_not_worse": False,
        "signed_bias": 0.01,
        "interval_score": 0.12,
    }
    holdout["summary"]["metrics"]["operating_profit"] = noisy_metric
    holdout["summary"]["leave_one_entity_out"]["operating_profit"] = {
        "all_candidate_not_worse": False,
        "max_candidate_minus_challenger_error": 0.01,
    }
    _write_json(holdout_path, holdout)
    promotion["holdout"]["metrics"]["operating_profit"] = noisy_metric
    promotion["holdout"]["artifact_sha256"] = _sha256(holdout_path)
    _write_json(evidence, promotion)
    _refresh_judgment_binding(evidence, "holdout", holdout_path)

    promotion = json.loads(evidence.read_text(encoding="utf-8"))
    judgment_path = Path(promotion["independent_judgment"]["artifact"])
    judgment = json.loads(judgment_path.read_text(encoding="utf-8"))
    judgment["numeric_diagnostics_assessment"].update({
        "conclusion": "mixed_but_acceptable",
        "worse_metrics": ["operating_profit.error"],
        "worse_leave_one_out": ["operating_profit:ENTITY-A", "operating_profit:ENTITY-B"],
        "reasoning": (
            "Operating-profit error is 1pp worse in a small noisy panel, while revenue, "
            "attributable net income, causal direction and calibration remain coherent."
        ),
        "decision_effect": "Retain as a monitored disagreement; it is not a hard failure.",
    })
    _write_json(judgment_path, judgment)
    promotion["independent_judgment"]["artifact_sha256"] = _sha256(judgment_path)
    _write_json(evidence, promotion)

    result = _validate(evidence)

    output = result.stdout + result.stderr
    assert result.returncode != 0
    assert "trusted external actuals registry" in output
    assert "numeric_diagnostics_assessment" not in output


def test_promotion_requires_frozen_independent_judgment(tmp_path):
    evidence = _evidence(tmp_path)
    promotion = json.loads(evidence.read_text(encoding="utf-8"))
    del promotion["independent_judgment"]
    _write_json(evidence, promotion)

    result = _validate(evidence)

    assert result.returncode != 0
    assert "independent_judgment" in (result.stdout + result.stderr)


def test_role_labels_and_boolean_do_not_replace_reviewer_orchestration_receipt(tmp_path):
    evidence = _evidence(tmp_path)
    promotion = json.loads(evidence.read_text(encoding="utf-8"))
    judgment_path = Path(promotion["independent_judgment"]["artifact"])
    judgment = json.loads(judgment_path.read_text(encoding="utf-8"))
    del judgment["provenance"]["orchestration_receipt"]
    _write_json(judgment_path, judgment)
    promotion["independent_judgment"]["artifact_sha256"] = _sha256(judgment_path)
    _write_json(evidence, promotion)

    result = _validate(evidence)

    assert result.returncode != 0
    assert "orchestration_receipt" in (result.stdout + result.stderr)


def test_different_role_labels_cannot_share_the_same_orchestrated_session(tmp_path):
    evidence = _evidence(tmp_path)
    promotion = json.loads(evidence.read_text(encoding="utf-8"))
    judgment_path = Path(promotion["independent_judgment"]["artifact"])
    judgment = json.loads(judgment_path.read_text(encoding="utf-8"))
    receipt = judgment["provenance"]["orchestration_receipt"]
    receipt["reviewer_session_id"] = receipt["builder_session_id"]
    _write_json(judgment_path, judgment)
    promotion["independent_judgment"]["artifact_sha256"] = _sha256(judgment_path)
    _write_json(evidence, promotion)

    result = _validate(evidence)

    assert result.returncode != 0
    assert "reviewer_session_id" in (result.stdout + result.stderr)


def test_builder_rebuttal_cannot_predate_reviewers_initial_conclusion(tmp_path):
    evidence = _evidence(tmp_path)
    promotion = json.loads(evidence.read_text(encoding="utf-8"))
    judgment_path = Path(promotion["independent_judgment"]["artifact"])
    judgment = json.loads(judgment_path.read_text(encoding="utf-8"))
    receipt = judgment["provenance"]["orchestration_receipt"]
    receipt["builder_rebuttal"] = {
        "status": "provided",
        "provided_at": receipt["review_started_at"],
    }
    _write_json(judgment_path, judgment)
    promotion["independent_judgment"]["artifact_sha256"] = _sha256(judgment_path)
    _write_json(evidence, promotion)

    result = _validate(evidence)

    assert result.returncode != 0
    assert "builder rebuttal" in (result.stdout + result.stderr).lower()


def test_release_rejects_independent_judgment_replayed_from_another_tree(tmp_path):
    evidence = _evidence(tmp_path)
    promotion = json.loads(evidence.read_text(encoding="utf-8"))
    judgment_path = Path(promotion["independent_judgment"]["artifact"])
    judgment = json.loads(judgment_path.read_text(encoding="utf-8"))
    judgment["provenance"]["candidate_identity"]["trainer_tree_sha256"] = (
        "sha256:" + "0" * 64
    )
    _write_json(judgment_path, judgment)
    promotion["independent_judgment"]["artifact_sha256"] = _sha256(judgment_path)
    _write_json(evidence, promotion)

    result = _validate(evidence)

    assert result.returncode != 0
    assert "independent_judgment candidate_identity" in (result.stdout + result.stderr)


def test_independent_hard_failure_cannot_be_compensated_by_positive_judgments(tmp_path):
    evidence = _evidence(tmp_path)
    promotion = json.loads(evidence.read_text(encoding="utf-8"))
    judgment_path = Path(promotion["independent_judgment"]["artifact"])
    judgment = json.loads(judgment_path.read_text(encoding="utf-8"))
    judgment["hard_failure_findings"]["unauthorized_evidence"] = [
        {
            "finding_id": "HF-EVIDENCE-1",
            "reasoning": "A scenario-only source was used as a Base parameter.",
            "affected_artifact_roles": ["blind_evaluation"],
        }
    ]
    _write_json(judgment_path, judgment)
    promotion["independent_judgment"]["artifact_sha256"] = _sha256(judgment_path)
    _write_json(evidence, promotion)

    result = _validate(evidence)

    assert result.returncode != 0
    assert "unauthorized_evidence" in (result.stdout + result.stderr)


def test_blind_critical_failure_blocks_even_if_overall_judgment_says_approve(tmp_path):
    evidence = _evidence(tmp_path)
    promotion = json.loads(evidence.read_text(encoding="utf-8"))
    blind_path = Path(promotion["blind_evaluation"]["artifact"])
    blind = json.loads(blind_path.read_text(encoding="utf-8"))
    candidate_ref = next(
        ref for ref in blind["provenance"]["grading_artifacts"] if ref["role"] == "candidate"
    )
    grading_path = Path(candidate_ref["path"])
    grading = json.loads(grading_path.read_text(encoding="utf-8"))
    grading["assertion_results"][1].update({
        "passed": False,
        "reason": "The candidate fails the critical reported-profit reconciliation.",
    })
    _write_json(grading_path, grading)
    candidate_ref["sha256"] = _sha256(grading_path)
    blind["summary"].update({
        "status": "fail",
        "critical_failures": 1,
        "candidate_not_worse": True,
    })
    _write_json(blind_path, blind)
    promotion["blind_evaluation"].update({
        "status": "fail",
        "critical_failures": 1,
        "candidate_not_worse": True,
        "artifact_sha256": _sha256(blind_path),
    })
    _write_json(evidence, promotion)
    _refresh_judgment_binding(evidence, "blind_evaluation", blind_path)

    result = _validate(evidence)

    assert result.returncode != 0
    assert "critical" in (result.stdout + result.stderr).lower()


def test_fixed_release_assertion_cannot_be_downgraded_inside_evidence(tmp_path):
    evidence = _evidence(tmp_path)
    promotion = json.loads(evidence.read_text(encoding="utf-8"))
    blind_path = Path(promotion["blind_evaluation"]["artifact"])
    blind = json.loads(blind_path.read_text(encoding="utf-8"))
    spec_ref = blind["provenance"]["assertion_specs"][0]
    spec_path = Path(spec_ref["path"])
    spec = json.loads(spec_path.read_text(encoding="utf-8"))
    spec["assertions"][1]["critical"] = False
    _write_json(spec_path, spec)
    spec_ref["sha256"] = _sha256(spec_path)

    candidate_ref = next(
        ref for ref in blind["provenance"]["grading_artifacts"]
        if ref["role"] == "candidate"
    )
    grading_path = Path(candidate_ref["path"])
    grading = json.loads(grading_path.read_text(encoding="utf-8"))
    grading["assertion_results"][1].update({
        "passed": False,
        "reason": "Profit bridge does not reconcile.",
    })
    _write_json(grading_path, grading)
    candidate_ref["sha256"] = _sha256(grading_path)
    blind["summary"].update({"status": "pass", "critical_failures": 0})
    _write_json(blind_path, blind)
    promotion["blind_evaluation"].update({
        "status": "pass",
        "critical_failures": 0,
        "artifact_sha256": _sha256(blind_path),
    })
    _write_json(evidence, promotion)
    _refresh_judgment_binding(evidence, "blind_evaluation", blind_path)

    result = _validate(evidence)

    assert result.returncode != 0
    assert "cannot be downgraded" in (result.stdout + result.stderr)


def test_method_research_release_is_honest_about_accuracy(tmp_path):
    evidence = _evidence(tmp_path)
    result = _validate(evidence)
    assert result.returncode == 0, result.stdout + result.stderr
    payload = json.loads(result.stdout)
    assert payload["status"] == "PASS"
    assert payload["profit_accuracy_claim"] == "not_established"
    assert payload["independent_review_assurance"] == (
        "orchestration_receipt_only_not_cryptographic_identity"
    )


def test_historical_accuracy_promotion_fails_closed_without_external_actuals_registry(tmp_path):
    evidence = _evidence(tmp_path, change_type="historical_training")

    result = _validate(evidence)

    assert result.returncode != 0
    assert "trusted external actuals registry" in (result.stdout + result.stderr)


def test_historical_release_requires_direct_profit_metrics(tmp_path):
    evidence = _evidence(tmp_path, change_type="historical_training")
    obj = json.loads(evidence.read_text(encoding="utf-8"))
    del obj["holdout"]["metrics"]["operating_profit"]
    evidence.write_text(json.dumps(obj), encoding="utf-8")
    result = _validate(evidence)
    assert result.returncode != 0
    assert "operating_profit" in (result.stdout + result.stderr)


def test_complete_historical_metrics_still_wait_for_trusted_actuals_registry(tmp_path):
    evidence = _evidence(tmp_path, change_type="historical_training")
    result = _validate(evidence)
    assert result.returncode != 0
    assert "trusted external actuals registry" in (result.stdout + result.stderr)


def test_historical_accuracy_claim_requires_local_actuals_receipt_not_metric_counts(tmp_path):
    evidence = _evidence(tmp_path, change_type="historical_training")
    _mutate_holdout_evaluation(
        evidence,
        "candidate",
        0,
        lambda evaluation: evaluation.pop("actuals_validation_receipt"),
    )

    result = _validate(evidence)

    assert result.returncode != 0
    assert "actuals_validation_receipt is required" in (result.stdout + result.stderr)


def test_historical_evaluation_rejects_ambiguous_legacy_receipt_state(tmp_path):
    evidence = _evidence(tmp_path, change_type="historical_training")

    def mutate(evaluation):
        evaluation.pop("forecast_seal_receipt_status")
        evaluation["receipt_verified"] = True

    _mutate_holdout_evaluation(evidence, "candidate", 0, mutate)
    result = _validate(evidence)

    assert result.returncode != 0
    assert "requires forecast_seal_receipt_status=verified" in (
        result.stdout + result.stderr
    )


def test_historical_evaluation_rejects_false_actuals_trust_statuses(tmp_path):
    for false_status in ("validated", "externally_verified"):
        case_root = tmp_path / false_status
        case_root.mkdir()
        evidence = _evidence(case_root, change_type="historical_training")

        def mutate(evaluation):
            receipt = evaluation["actuals_validation_receipt"]
            receipt["status"] = false_status
            core = {key: value for key, value in receipt.items() if key != "receipt_id"}
            canonical = json.dumps(
                core, sort_keys=True, separators=(",", ":"), ensure_ascii=False
            ).encode("utf-8")
            receipt["receipt_id"] = "sha256:" + hashlib.sha256(canonical).hexdigest()

        _mutate_holdout_evaluation(evidence, "candidate", 0, mutate)
        result = _validate(evidence)

        assert result.returncode != 0, false_status
        assert (
            "must be a locally_consistent_untrusted training_actuals/3.2 receipt"
            in result.stdout + result.stderr
        ), false_status


def test_historical_accuracy_claim_rejects_tampered_actuals_receipt(tmp_path):
    evidence = _evidence(tmp_path, change_type="historical_training")

    def mutate(evaluation):
        evaluation["actuals_validation_receipt"]["validated_observations"][0]["value"] += 1

    _mutate_holdout_evaluation(evidence, "candidate", 0, mutate)
    result = _validate(evidence)

    assert result.returncode != 0
    assert "receipt_id is not derived" in (result.stdout + result.stderr)


def test_rehashed_receipt_cannot_override_source_bound_fact_semantics(tmp_path):
    adversarial_changes = (
        (
            "basis label laundering",
            lambda row: row.update(accounting_basis="non-GAAP adjusted management measure"),
            "canonical statutory basis label",
        ),
        (
            "numeric literal disagrees with value",
            lambda row: row.update(source_fact_value_text="999.0"),
            "does not equal value",
        ),
        (
            "analyst-selected precision",
            lambda row: row.update(
                reported_precision={
                    "basis": "rounded",
                    "rounding_increment_in_reported_unit": 1e12,
                }
            ),
            "displayed numeric increment",
        ),
    )
    for label, change, expected in adversarial_changes:
        case_root = tmp_path / label.replace(" ", "-")
        case_root.mkdir()
        evidence = _evidence(case_root, change_type="historical_training")

        def mutate(evaluation):
            receipt = evaluation["actuals_validation_receipt"]
            change(receipt["validated_observations"][0])
            core = {key: value for key, value in receipt.items() if key != "receipt_id"}
            canonical = json.dumps(
                core, sort_keys=True, separators=(",", ":"), ensure_ascii=False
            ).encode("utf-8")
            receipt["receipt_id"] = "sha256:" + hashlib.sha256(canonical).hexdigest()

        _mutate_holdout_evaluation(evidence, "candidate", 0, mutate)
        result = _validate(evidence)

        assert result.returncode != 0, label
        assert expected in (result.stdout + result.stderr), label


def test_candidate_and_challenger_must_use_identical_locally_consistent_actuals(tmp_path):
    evidence = _evidence(tmp_path, change_type="historical_training")

    def mutate(evaluation):
        receipt = evaluation["actuals_validation_receipt"]
        receipt["actuals_sha256"] = "sha256:" + "f" * 64
        core = {key: value for key, value in receipt.items() if key != "receipt_id"}
        canonical = json.dumps(
            core, sort_keys=True, separators=(",", ":"), ensure_ascii=False
        ).encode("utf-8")
        receipt["receipt_id"] = "sha256:" + hashlib.sha256(canonical).hexdigest()

    _mutate_holdout_evaluation(evidence, "challenger", 0, mutate)
    result = _validate(evidence)

    assert result.returncode != 0
    assert "not scored against identical actuals" in (result.stdout + result.stderr)


def test_receipt_cannot_use_consolidated_net_income_as_attributable_metric(tmp_path):
    evidence = _evidence(tmp_path, change_type="historical_training")

    def mutate(evaluation):
        receipt = evaluation["actuals_validation_receipt"]
        target = next(
            row for row in receipt["validated_observations"]
            if row["metric"] == "gaap_net_income_attributable"
        )
        target["metric"] = "net_income"
        core = {key: value for key, value in receipt.items() if key != "receipt_id"}
        canonical = json.dumps(
            core, sort_keys=True, separators=(",", ":"), ensure_ascii=False
        ).encode("utf-8")
        receipt["receipt_id"] = "sha256:" + hashlib.sha256(canonical).hexdigest()

    _mutate_holdout_evaluation(evidence, "candidate", 0, mutate)
    result = _validate(evidence)

    assert result.returncode != 0
    assert "canonical metric identity" in (result.stdout + result.stderr)


def test_structural_promotion_suite_uses_source_local_diagnostic_markers():
    argv = PROMOTION.promotion_test_argv(sys.executable)
    assert "tests" in argv
    assert "-m" in argv
    assert "not diagnostic_benchmark" in argv
    assert not any(item.startswith("--ignore=tests/") for item in argv)


def test_trainer_documents_trusted_promotion_execution_contract():
    contract = "\n".join(
        [
            (SKILL / "SKILL.md").read_text(encoding="utf-8"),
            (SKILL / "references" / "historical-training-loop.md").read_text(encoding="utf-8"),
            (SKILL / "references" / "companion-live-skill-contract.md").read_text(encoding="utf-8"),
        ]
    )
    for required in (
        "trainer_structural_contracts",
        "evidence-supplied command",
        "assertion_specs",
        "grading_artifacts",
        "recomputed",
    ):
        assert required in contract
