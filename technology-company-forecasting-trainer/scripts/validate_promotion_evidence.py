#!/usr/bin/env python3
"""Validate anti-drift evidence before a candidate build is promoted.

This gate deliberately distinguishes two honest claims:

* ``historical_training`` may claim improved forecast accuracy only after
  untouched holdouts report revenue, operating-profit and GAAP-net-income
  errors against a named challenger, including signed bias and interval score.
* ``method_research`` may promote structural/data-integrity improvements after
  external-method reflection, regression tests and a blind contract audit, but
  must explicitly say that profit-accuracy improvement is not established.

The validator rejects bare self-report. Test, blind-evaluation and holdout
claims must be bound by SHA-256 to structured artifacts. Test artifacts are
also bound to the exact trainer tree; holdout summaries are recomputed from
sealed per-case scoring artifacts rather than trusted from promotion JSON.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import subprocess
import sys
from datetime import datetime
from pathlib import Path


_SCRIPT_DIR = Path(__file__).resolve().parent
if str(_SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPT_DIR))

from _actuals_contract import (
    FORECAST_SEAL_RECEIPT_STATUS_VERIFIED,
    validate_actuals_receipt,
)


CHANGE_TYPES = {"historical_training", "method_research"}
# Local hashes and internally coherent Actuals receipts cannot establish that
# an external official document was copied faithfully when the same builder can
# rewrite every local artifact and recompute each hash. Until the host provides
# a verifier for an append-only/signed Actuals registry outside builder control,
# this release must not certify predictive accuracy. Method-integrity releases
# remain available with profit_accuracy_claim=not_established.
TRUSTED_EXTERNAL_ACTUALS_REGISTRY_AVAILABLE = False
PROFIT_METRICS = {"revenue", "operating_profit", "net_income"}
PROMOTION_TEST_SUITE_ID = "trainer_structural_contracts"
HOLDOUT_METRIC_FIELDS = {
    "revenue": ("revenue_mape", "revenue_signed_bias", "revenue_interval_score"),
    "operating_profit": (
        "operating_profit_scaled_mae",
        "operating_profit_signed_bias",
        "operating_profit_interval_score",
    ),
    "net_income": ("net_income_scaled_mae", "net_income_signed_bias", "net_income_interval_score"),
}
HARD_FAILURE_CATEGORIES = {
    "leakage",
    "accounting_or_definition_error",
    "unauthorized_evidence",
    "outcome_fitting",
    "critical_failure",
}
JUDGMENT_CONCLUSIONS = {
    "causal_quality": {"supports", "rejects", "unresolved"},
    "generalization": {"supports", "not_established", "rejects", "unresolved"},
    "complexity": {"proportionate", "bounded", "excessive", "unresolved"},
    "disagreements": {"resolved", "bounded", "unresolved_material"},
}
ORCHESTRATION_RECEIPT_BOUNDARY = "orchestration_receipt_only_not_cryptographic_identity"


def _path(raw: object, *, base: Path) -> Path | None:
    if not isinstance(raw, str) or not raw.strip():
        return None
    path = Path(raw)
    return path if path.is_absolute() else (base / path).resolve()


def _meaningful(raw: object) -> bool:
    return isinstance(raw, str) and raw.strip().lower() not in {"", "none", "n/a", "tbd", "unknown"}


def _sha256(path: Path) -> str:
    return "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()


def promotion_test_argv(python_executable: str) -> list[str]:
    """Return the sole command promotion is permitted to execute.

    Evidence selects a stable suite identifier; it never supplies executable
    arguments. Disabling bytecode and pytest's cache provider lets the builder
    verify that the tested trainer tree did not change during the run.
    """

    return [
        python_executable,
        "-m",
        "pytest",
        "-q",
        "-p",
        "no:cacheprovider",
        "tests",
        "-m",
        "not diagnostic_benchmark",
    ]


def trainer_tree_sha256(root: Path) -> str:
    digest = hashlib.sha256()
    for path in sorted(item for item in root.rglob("*") if item.is_file()):
        rel = path.relative_to(root)
        if "__pycache__" in rel.parts or path.suffix in {".pyc", ".pyo"}:
            continue
        digest.update(rel.as_posix().encode("utf-8"))
        digest.update(b"\0")
        digest.update(hashlib.sha256(path.read_bytes()).digest())
    return "sha256:" + digest.hexdigest()


def _finite(raw: object) -> bool:
    return isinstance(raw, (int, float)) and not isinstance(raw, bool) and math.isfinite(float(raw))


def _iso_datetime(raw: object) -> bool:
    if not _meaningful(raw):
        return False
    try:
        datetime.fromisoformat(str(raw).replace("Z", "+00:00"))
    except ValueError:
        return False
    return True


def _aware_datetime(raw: object) -> datetime | None:
    if not _meaningful(raw):
        return None
    try:
        parsed = datetime.fromisoformat(str(raw).replace("Z", "+00:00"))
    except ValueError:
        return None
    return parsed if parsed.utcoffset() is not None else None


def _validate_orchestration_receipt(
    raw: object,
    *,
    label: str,
    report_timestamp: object,
    errors: list[str],
) -> None:
    """Validate auditable process separation without claiming strong identity.

    This receipt records what the local orchestrator says happened.  It is not
    a signature, authentication token or proof that the named human/agent owns
    the session.  Hash validation remains separate and binds the reviewed
    artifacts; this function only validates session separation and chronology.
    """

    if not isinstance(raw, dict):
        errors.append(f"{label} is required; role labels and booleans do not prove independence")
        return
    if raw.get("assurance_boundary") != ORCHESTRATION_RECEIPT_BOUNDARY:
        errors.append(
            f"{label}.assurance_boundary must state {ORCHESTRATION_RECEIPT_BOUNDARY}"
        )
    for field in (
        "receipt_id",
        "orchestrator",
        "reviewer_session_id",
        "reviewer_task_id",
        "builder_session_id",
    ):
        if not _meaningful(raw.get(field)):
            errors.append(f"{label}.{field} is required")
    if (
        _meaningful(raw.get("reviewer_session_id"))
        and raw.get("reviewer_session_id") == raw.get("builder_session_id")
    ):
        errors.append(f"{label}.reviewer_session_id must differ from builder_session_id")

    timestamps: dict[str, datetime | None] = {}
    for field in (
        "frozen_inputs_delivered_at",
        "review_started_at",
        "initial_conclusion_at",
        "review_completed_at",
        "receipt_issued_at",
    ):
        timestamps[field] = _aware_datetime(raw.get(field))
        if timestamps[field] is None:
            errors.append(f"{label}.{field} must be a timezone-aware ISO timestamp")
    ordered = (
        "frozen_inputs_delivered_at",
        "review_started_at",
        "initial_conclusion_at",
        "review_completed_at",
        "receipt_issued_at",
    )
    if all(timestamps[field] is not None for field in ordered):
        for earlier, later in zip(ordered, ordered[1:]):
            if timestamps[earlier] > timestamps[later]:
                if earlier == "frozen_inputs_delivered_at":
                    errors.append(f"{label}: frozen inputs must be delivered before review starts")
                else:
                    errors.append(f"{label}: {earlier} must not be after {later}")

    report_time = _aware_datetime(report_timestamp)
    completed = timestamps.get("review_completed_at")
    if report_time is None:
        errors.append(f"{label}: enclosing review timestamp must be timezone-aware")
    elif completed is not None and report_time < completed:
        errors.append(f"{label}: enclosing review report predates review_completed_at")

    rebuttal = raw.get("builder_rebuttal")
    if not isinstance(rebuttal, dict):
        errors.append(f"{label}.builder_rebuttal must explicitly state provided or not_provided")
        return
    status = str(rebuttal.get("status") or "").strip()
    provided_at = rebuttal.get("provided_at")
    if status == "not_provided":
        if provided_at is not None and provided_at != "":
            errors.append(f"{label}: builder rebuttal marked not_provided cannot have provided_at")
    elif status == "provided":
        rebuttal_time = _aware_datetime(provided_at)
        if rebuttal_time is None:
            errors.append(f"{label}: builder rebuttal provided_at must be timezone-aware")
        else:
            initial = timestamps.get("initial_conclusion_at")
            if initial is not None and rebuttal_time < initial:
                errors.append(f"{label}: builder rebuttal cannot predate reviewer initial conclusion")
            if completed is not None and rebuttal_time > completed:
                errors.append(f"{label}: builder rebuttal cannot postdate review completion")
    else:
        errors.append(f"{label}.builder_rebuttal.status must be provided or not_provided")


def _date_value(raw: object):
    if not _meaningful(raw):
        return None
    try:
        return datetime.fromisoformat(str(raw).replace("Z", "+00:00")).date()
    except ValueError:
        return None


def _close(left: object, right: object) -> bool:
    return _finite(left) and _finite(right) and math.isclose(
        float(left), float(right), rel_tol=1e-9, abs_tol=1e-12
    )


def _validate_candidate_identity(
    raw: object,
    *,
    label: str,
    errors: list[str],
    expected: dict[str, str] | None = None,
    current_tree_sha256: str | None = None,
) -> dict[str, str] | None:
    """Bind every promotion view to one immutable method candidate.

    Human review decides whether the candidate is causally adequate.  This
    deterministic identity only prevents a favorable blind/holdout review for
    one method tree from being replayed against another tree.
    """

    if not isinstance(raw, dict):
        errors.append(f"{label} is required")
        return None
    tree_sha256 = raw.get("trainer_tree_sha256")
    method_version = raw.get("method_version")
    if not _meaningful(tree_sha256):
        errors.append(f"{label}.trainer_tree_sha256 is required")
    if not _meaningful(method_version):
        errors.append(f"{label}.method_version is required")
    if current_tree_sha256 is not None and tree_sha256 != current_tree_sha256:
        errors.append(
            f"{label}.trainer_tree_sha256 must equal current trainer tree "
            f"{current_tree_sha256}"
        )
    if expected is not None:
        if tree_sha256 != expected.get("trainer_tree_sha256"):
            errors.append(f"{label}.trainer_tree_sha256 does not match promotion candidate")
        if method_version != expected.get("method_version"):
            errors.append(f"{label}.method_version does not match promotion candidate")
    if not _meaningful(tree_sha256) or not _meaningful(method_version):
        return None
    return {
        "trainer_tree_sha256": str(tree_sha256),
        "method_version": str(method_version),
    }


def _load_bound_json(
    descriptor: dict,
    *,
    base: Path,
    label: str,
    errors: list[str],
) -> tuple[Path | None, dict | None]:
    artifact = _path(descriptor.get("artifact"), base=base)
    if artifact is None or not artifact.is_file() or artifact.stat().st_size == 0:
        errors.append(f"{label}.artifact must point to a non-empty JSON artifact")
        return artifact, None
    expected_hash = descriptor.get("artifact_sha256")
    if not _meaningful(expected_hash):
        errors.append(f"{label}.artifact_sha256 is required")
    else:
        actual_hash = _sha256(artifact)
        if expected_hash != actual_hash:
            errors.append(f"{label}.artifact_sha256 does not match {actual_hash}")
    try:
        payload = json.loads(artifact.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        errors.append(f"{label}.artifact is not valid JSON: {exc}")
        return artifact, None
    if not isinstance(payload, dict):
        errors.append(f"{label}.artifact must contain a JSON object")
        return artifact, None
    return artifact, payload


def _verify_artifact_ref(
    ref: object,
    *,
    base: Path,
    label: str,
    errors: list[str],
) -> tuple[Path | None, dict | None]:
    if not isinstance(ref, dict):
        errors.append(f"{label} must be an artifact reference object")
        return None, None
    path = _path(ref.get("path"), base=base)
    if path is None or not path.is_file() or path.stat().st_size == 0:
        errors.append(f"{label} path must reference a non-empty artifact")
        return path, None
    if ref.get("sha256") != _sha256(path):
        errors.append(f"{label} sha256 mismatch")
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        errors.append(f"{label} is not valid JSON: {exc}")
        return path, None
    if not isinstance(payload, dict):
        errors.append(f"{label} must contain a JSON object")
        return path, None
    return path, payload


def _validate_independent_judgment(
    descriptor: dict,
    *,
    evidence_base: Path,
    expected_artifacts: dict[str, Path | None],
    candidate_identity: dict[str, str] | None,
    change_type: str,
    profit_accuracy_claim: object,
    errors: list[str],
) -> None:
    """Validate a frozen qualitative decision without inventing a score.

    Numeric holdout and blind-comparison results remain a diagnostic panel.
    Promotion authority comes from a distinct reviewer considering causal
    quality, generalization, complexity and unresolved disagreement.  Leakage,
    hard accounting/definition errors, evidence used outside its permission,
    outcome fitting and critical failures remain non-compensatory vetoes.
    """

    artifact, report = _load_bound_json(
        descriptor,
        base=evidence_base,
        label="independent_judgment",
        errors=errors,
    )
    if artifact is None or report is None:
        return
    if report.get("schema_version") != "1.0" or report.get("artifact_type") != "promotion_judgment":
        errors.append(
            "independent_judgment.artifact must be schema 1.0 artifact_type=promotion_judgment"
        )
    if not _meaningful(report.get("judgment_id")) or not _iso_datetime(report.get("generated_at")):
        errors.append("independent_judgment.artifact requires judgment_id and generated_at")
    for forbidden in ("score", "weighted_score", "overall_score", "composite_score"):
        if forbidden in report:
            errors.append(
                f"independent_judgment.artifact {forbidden} is forbidden; preserve orthogonal judgments"
            )

    provenance = report.get("provenance")
    reviewed_roles: set[str] = set()
    if not isinstance(provenance, dict):
        errors.append("independent_judgment.artifact provenance is required")
    else:
        for field in ("reviewer_id", "builder_id"):
            if not _meaningful(provenance.get(field)):
                errors.append(f"independent_judgment.artifact provenance.{field} is required")
        if provenance.get("reviewer_id") == provenance.get("builder_id"):
            errors.append("independent_judgment reviewer_id must differ from builder_id")
        if provenance.get("independent_of_builder") is not True:
            errors.append("independent_judgment independent_of_builder must be true")
        _validate_candidate_identity(
            provenance.get("candidate_identity"),
            label="independent_judgment candidate_identity",
            errors=errors,
            expected=candidate_identity,
        )
        _validate_orchestration_receipt(
            provenance.get("orchestration_receipt"),
            label="independent_judgment orchestration_receipt",
            report_timestamp=report.get("generated_at"),
            errors=errors,
        )
        refs = provenance.get("reviewed_artifacts")
        if not isinstance(refs, list):
            errors.append("independent_judgment provenance.reviewed_artifacts is required")
            refs = []
        for index, ref in enumerate(refs):
            label = f"independent_judgment.artifact provenance.reviewed_artifacts[{index}]"
            if not isinstance(ref, dict):
                errors.append(f"{label} must be an object")
                continue
            role = str(ref.get("role") or "").strip()
            if role not in expected_artifacts:
                errors.append(f"{label}.role is not a declared promotion input")
                continue
            if role in reviewed_roles:
                errors.append(f"{label} duplicates role {role}")
                continue
            reviewed_roles.add(role)
            path = _path(ref.get("path"), base=artifact.parent)
            expected = expected_artifacts.get(role)
            if path is None or not path.is_file() or path.stat().st_size == 0:
                errors.append(f"{label}.path must reference a non-empty frozen artifact")
                continue
            if expected is None or path.resolve() != expected.resolve():
                errors.append(f"{label}.path does not match the promotion input for {role}")
            if ref.get("sha256") != _sha256(path):
                errors.append(f"{label}.sha256 mismatch")
        if reviewed_roles != set(expected_artifacts):
            errors.append(
                "independent_judgment must bind every frozen promotion input exactly once: "
                + ", ".join(sorted(expected_artifacts))
            )

    hard_findings = report.get("hard_failure_findings")
    if not isinstance(hard_findings, dict):
        errors.append("independent_judgment.artifact hard_failure_findings is required")
        hard_findings = {}
    if set(hard_findings) != HARD_FAILURE_CATEGORIES:
        errors.append(
            "independent_judgment hard_failure_findings must contain exactly: "
            + ", ".join(sorted(HARD_FAILURE_CATEGORIES))
        )
    for category in sorted(HARD_FAILURE_CATEGORIES):
        findings = hard_findings.get(category)
        if not isinstance(findings, list):
            errors.append(f"independent_judgment hard_failure_findings.{category} must be an array")
            continue
        for index, finding in enumerate(findings):
            label = f"independent_judgment hard_failure_findings.{category}[{index}]"
            if not isinstance(finding, dict):
                errors.append(f"{label} must be an object")
                continue
            if not _meaningful(finding.get("finding_id")) or not _meaningful(finding.get("reasoning")):
                errors.append(f"{label} requires finding_id and reasoning")
            roles = finding.get("affected_artifact_roles")
            if not isinstance(roles, list) or not roles or not all(
                role in expected_artifacts for role in roles
            ):
                errors.append(f"{label}.affected_artifact_roles must reference frozen inputs")
        if findings:
            errors.append(
                f"independent_judgment reports non-compensatory hard failure {category}"
            )

    judgments = report.get("judgments")
    conclusions: dict[str, str] = {}
    if not isinstance(judgments, dict):
        errors.append("independent_judgment.artifact judgments is required")
        judgments = {}
    for angle, allowed in JUDGMENT_CONCLUSIONS.items():
        row = judgments.get(angle)
        if not isinstance(row, dict):
            errors.append(f"independent_judgment judgments.{angle} is required")
            continue
        conclusion = str(row.get("conclusion") or "").strip()
        conclusions[angle] = conclusion
        if conclusion not in allowed:
            errors.append(
                f"independent_judgment judgments.{angle}.conclusion must be one of "
                + ", ".join(sorted(allowed))
            )
        if not _meaningful(row.get("reasoning")):
            errors.append(f"independent_judgment judgments.{angle}.reasoning is required")
        evidence_refs = row.get("evidence_refs")
        if not isinstance(evidence_refs, list) or not evidence_refs or not all(
            ref in expected_artifacts for ref in evidence_refs
        ):
            errors.append(
                f"independent_judgment judgments.{angle}.evidence_refs must reference frozen inputs"
            )

    diagnostics = report.get("numeric_diagnostics_assessment")
    diagnostic_conclusion = ""
    if not isinstance(diagnostics, dict):
        errors.append("independent_judgment.artifact numeric_diagnostics_assessment is required")
    else:
        diagnostic_conclusion = str(diagnostics.get("conclusion") or "").strip()
        if diagnostic_conclusion not in {
            "supports", "mixed_but_acceptable", "does_not_support", "not_applicable",
        }:
            errors.append("independent_judgment numeric_diagnostics_assessment.conclusion is invalid")
        for field in ("worse_metrics", "worse_leave_one_out"):
            if not isinstance(diagnostics.get(field), list):
                errors.append(f"independent_judgment numeric_diagnostics_assessment.{field} must be an array")
        for field in ("reasoning", "decision_effect"):
            if not _meaningful(diagnostics.get(field)):
                errors.append(
                    f"independent_judgment numeric_diagnostics_assessment.{field} is required"
                )
        if change_type == "historical_training" and diagnostic_conclusion == "not_applicable":
            errors.append("historical_training requires an independent assessment of numeric diagnostics")

    overall = report.get("overall")
    decision = ""
    if not isinstance(overall, dict):
        errors.append("independent_judgment.artifact overall is required")
    else:
        decision = str(overall.get("decision") or "").strip()
        if decision not in {"approve", "reject"}:
            errors.append("independent_judgment overall.decision must be approve or reject")
        if descriptor.get("status") != decision:
            errors.append("independent_judgment.status must match artifact overall.decision")
        if not _meaningful(overall.get("rationale")):
            errors.append("independent_judgment overall.rationale is required")
        if overall.get("profit_accuracy_claim") != profit_accuracy_claim:
            errors.append(
                "independent_judgment overall.profit_accuracy_claim must match promotion evidence"
            )

    if decision != "approve":
        errors.append("independent_judgment must approve promotion")
    if conclusions.get("causal_quality") != "supports":
        errors.append("independent_judgment causal_quality does not support promotion")
    if change_type == "historical_training" and conclusions.get("generalization") != "supports":
        errors.append("historical_training independent judgment must support generalization")
    if change_type == "method_research" and conclusions.get("generalization") not in {
        "supports", "not_established",
    }:
        errors.append("method_research independent judgment must bound generalization honestly")
    if conclusions.get("complexity") not in {"proportionate", "bounded"}:
        errors.append("independent_judgment complexity does not support promotion")
    if conclusions.get("disagreements") not in {"resolved", "bounded"}:
        errors.append("independent_judgment has unresolved material disagreement")
    if diagnostic_conclusion == "does_not_support":
        errors.append("independent_judgment numeric diagnostics do not support promotion")


def _validate_test_artifact(
    descriptor: dict,
    *,
    evidence_base: Path,
    skill_root: Path,
    candidate_identity: dict[str, str] | None,
    errors: list[str],
) -> None:
    _, report = _load_bound_json(
        descriptor, base=evidence_base, label="test_suite", errors=errors
    )
    if report is None:
        return
    if report.get("schema_version") != "1.0" or report.get("artifact_type") != "test_run":
        errors.append("test_suite.artifact must be schema 1.0 artifact_type=test_run")
    for field in ("run_id",):
        if not _meaningful(report.get(field)):
            errors.append(f"test_suite.artifact missing {field}")
    for field in ("started_at", "finished_at"):
        if not _iso_datetime(report.get(field)):
            errors.append(f"test_suite.artifact has invalid {field}")

    tested_tree = report.get("tested_tree_sha256")
    current_tree = trainer_tree_sha256(skill_root)
    if tested_tree != current_tree:
        errors.append(
            f"test_suite.artifact tested_tree_sha256 does not match current trainer tree {current_tree}"
        )

    provenance = report.get("provenance")
    if not isinstance(provenance, dict):
        errors.append("test_suite.artifact provenance is required")
    else:
        for field in ("runner", "cwd", "source_revision"):
            if not _meaningful(provenance.get(field)):
                errors.append(f"test_suite.artifact provenance.{field} is required")
        argv = provenance.get("command_argv")
        if not isinstance(argv, list) or not argv or not all(_meaningful(item) for item in argv):
            errors.append("test_suite.artifact provenance.command_argv must be a non-empty string array")
        else:
            artifact_command = " ".join(str(item) for item in argv)
            if descriptor.get("command") != artifact_command:
                errors.append("test_suite.command is not bound to artifact provenance.command_argv")
            expected_argv = promotion_test_argv(sys.executable)
            if argv != expected_argv:
                errors.append("test_suite command is not the allowlisted structural-contract suite")
        cwd = _path(provenance.get("cwd"), base=evidence_base)
        if cwd != skill_root.resolve():
            errors.append("test_suite.artifact provenance.cwd must equal the trainer skill root")
        if candidate_identity is not None:
            if tested_tree != candidate_identity["trainer_tree_sha256"]:
                errors.append("test_suite.artifact tested_tree_sha256 does not match promotion candidate")
            if provenance.get("source_revision") != candidate_identity["method_version"]:
                errors.append("test_suite.artifact provenance.source_revision does not match promotion candidate")

    summary = report.get("summary")
    if not isinstance(summary, dict):
        errors.append("test_suite.artifact summary is required")
        return
    for field in ("exit_code", "collected", "passed", "failed", "errors", "skipped"):
        if not isinstance(summary.get(field), int) or isinstance(summary.get(field), bool):
            errors.append(f"test_suite.artifact summary.{field} must be an integer")
    if summary.get("exit_code") != 0 or summary.get("failed") != 0 or summary.get("errors") != 0:
        errors.append("test_suite.artifact command result must have exit_code=0, failed=0 and errors=0")
    if not isinstance(summary.get("collected"), int) or summary.get("collected", 0) <= 0:
        errors.append("test_suite.artifact command result must collect at least one test")
    if not isinstance(summary.get("passed"), int) or summary.get("passed", 0) <= 0:
        errors.append("test_suite.artifact command result must pass at least one test")
    if descriptor.get("passed") is not True or descriptor.get("failed") != 0:
        errors.append("test_suite promotion summary must record passed=true and failed=0")
    if summary.get("failed") != descriptor.get("failed"):
        errors.append("test_suite.failed does not match test_suite.artifact summary")


def _validate_assertion_specs(
    refs: object,
    *,
    artifact_base: Path,
    case_ids: list[str],
    errors: list[str],
) -> dict[str, list[dict[str, object]]]:
    specs: dict[str, list[dict[str, object]]] = {}
    if not isinstance(refs, list) or not refs:
        errors.append("blind_evaluation.artifact provenance.assertion_specs is required")
        return specs
    for index, ref in enumerate(refs):
        label = f"blind_evaluation.artifact provenance.assertion_specs[{index}]"
        _, payload = _verify_artifact_ref(ref, base=artifact_base, label=label, errors=errors)
        case_id = str(ref.get("case_id") or "") if isinstance(ref, dict) else ""
        if not _meaningful(case_id) or (case_ids and case_id not in case_ids):
            errors.append(f"{label} case_id is not declared")
            continue
        if case_id in specs:
            errors.append(f"{label} duplicates case_id {case_id}")
            continue
        if payload is None:
            continue
        payload_case = payload.get("case_id") or payload.get("eval_name")
        if payload_case != case_id:
            errors.append(f"{label} payload case_id does not match {case_id}")
        assertions = payload.get("assertions")
        if not isinstance(assertions, list) or not assertions:
            errors.append(f"{label} requires a non-empty fixed assertions array")
            continue
        parsed: list[dict[str, object]] = []
        for expected_index, assertion in enumerate(assertions, start=1):
            item_label = f"{label}.assertions[{expected_index - 1}]"
            if isinstance(assertion, str):
                assertion = {
                    "index": expected_index,
                    "text": assertion,
                    # The original eval metadata has no severity field; treating
                    # every locked assertion as critical is conservative.
                    "critical": True,
                }
            elif not isinstance(assertion, dict):
                errors.append(f"{item_label} must be an object or string")
                continue
            if assertion.get("index") != expected_index:
                errors.append(f"{item_label} index must be the fixed sequence value {expected_index}")
            if not _meaningful(assertion.get("text")):
                errors.append(f"{item_label} text is required")
            if assertion.get("critical") is not True:
                errors.append(
                    f"{item_label} is a fixed release assertion and cannot be downgraded; "
                    "non-critical observations belong in the independent judgment"
                )
            parsed.append({**assertion, "critical": True})
        if len(parsed) == len(assertions):
            specs[case_id] = parsed
    if case_ids and set(specs) != set(case_ids):
        errors.append(
            "blind_evaluation.artifact provenance.assertion_specs must cover every declared case"
        )
    return specs


def _validate_blind_gradings(
    refs: object,
    *,
    artifact_base: Path,
    case_ids: list[str],
    specs: dict[str, list[dict[str, object]]],
    evaluator_id: object,
    candidate_identity: dict[str, str] | None,
    errors: list[str],
) -> dict[str, dict[str, dict[str, int]]]:
    grades: dict[str, dict[str, dict[str, int]]] = {"candidate": {}, "challenger": {}}
    if not isinstance(refs, list) or not refs:
        errors.append("blind_evaluation.artifact provenance.grading_artifacts is required")
        return grades
    for index, ref in enumerate(refs):
        label = f"blind_evaluation.artifact provenance.grading_artifacts[{index}]"
        _, payload = _verify_artifact_ref(ref, base=artifact_base, label=label, errors=errors)
        role = str(ref.get("role") or "") if isinstance(ref, dict) else ""
        case_id = str(ref.get("case_id") or "") if isinstance(ref, dict) else ""
        if role not in grades:
            errors.append(f"{label} role must be candidate or challenger")
            continue
        if not _meaningful(case_id) or (case_ids and case_id not in case_ids):
            errors.append(f"{label} case_id is not declared")
            continue
        if case_id in grades[role]:
            errors.append(f"{label} duplicates {role} case_id {case_id}")
            continue
        if payload is None:
            continue
        native_results = "assertion_results" in payload
        if native_results:
            if payload.get("case_id") != case_id or payload.get("role") != role:
                errors.append(f"{label} payload role/case_id does not match its bound reference")
            if payload.get("grader_id") != evaluator_id or not _iso_datetime(payload.get("graded_at")):
                errors.append(f"{label} requires the bound evaluator_id and graded_at")
        if role == "candidate":
            _validate_candidate_identity(
                payload.get("candidate_identity"),
                label=f"blind_evaluation candidate grading {case_id}",
                errors=errors,
                expected=candidate_identity,
            )
        fixed = specs.get(case_id)
        results = payload.get("assertion_results") if native_results else payload.get("expectations")
        if fixed is None:
            errors.append(f"{label} has no fixed assertion spec")
            continue
        if not isinstance(results, list) or len(results) != len(fixed):
            errors.append(f"{label} must grade every fixed assertion exactly once")
            continue
        passed = 0
        critical_failures = 0
        structurally_valid = True
        for offset, (result, assertion) in enumerate(zip(results, fixed), start=1):
            item_label = f"{label}.assertion_results[{offset - 1}]"
            if not isinstance(result, dict):
                errors.append(f"{item_label} must be an object")
                structurally_valid = False
                continue
            result_index = result.get("index", offset) if not native_results else result.get("index")
            if result_index != assertion.get("index"):
                errors.append(f"{item_label} index does not match the fixed assertion")
                structurally_valid = False
            if result.get("text") != assertion.get("text"):
                errors.append(f"{item_label} text does not match the fixed assertion")
                structurally_valid = False
            if not isinstance(result.get("passed"), bool):
                errors.append(f"{item_label} passed must be boolean")
                structurally_valid = False
                continue
            reason = result.get("reason") if native_results else result.get("evidence")
            if not _meaningful(reason):
                errors.append(f"{item_label} reason is required")
                structurally_valid = False
            if result["passed"]:
                passed += 1
            elif assertion.get("critical") is True:
                critical_failures += 1
        if not native_results:
            summary = payload.get("summary")
            if not isinstance(summary, dict):
                errors.append(f"{label} original grading artifact requires summary")
                structurally_valid = False
            else:
                expected_summary = {
                    "passed": passed,
                    "failed": len(fixed) - passed,
                    "total": len(fixed),
                }
                for field, expected in expected_summary.items():
                    if summary.get(field) != expected:
                        errors.append(f"{label} summary.{field} is not derived from expectations")
                        structurally_valid = False
                expected_rate = passed / len(fixed)
                if not _close(summary.get("pass_rate"), expected_rate):
                    errors.append(f"{label} summary.pass_rate is not derived from expectations")
                    structurally_valid = False
            timing = payload.get("timing")
            if (
                not isinstance(timing, dict)
                or not _iso_datetime(timing.get("executor_start"))
                or not _iso_datetime(timing.get("executor_end"))
                or not _finite(timing.get("executor_duration_seconds"))
                or float(timing.get("executor_duration_seconds", -1)) < 0
            ):
                errors.append(f"{label} original grading artifact requires valid execution timing")
                structurally_valid = False
        if structurally_valid:
            grades[role][case_id] = {
                "passed": passed,
                "failed": len(fixed) - passed,
                "total": len(fixed),
                "critical_failures": critical_failures,
            }
    for role in grades:
        if case_ids and set(grades[role]) != set(case_ids):
            errors.append(
                f"blind_evaluation.artifact provenance.grading_artifacts must cover every {role} case"
            )
    return grades


def _validate_blind_artifact(
    descriptor: dict,
    *,
    evidence_base: Path,
    candidate_identity: dict[str, str] | None,
    errors: list[str],
) -> None:
    artifact, report = _load_bound_json(
        descriptor, base=evidence_base, label="blind_evaluation", errors=errors
    )
    if artifact is None or report is None:
        return
    if report.get("schema_version") != "1.0" or report.get("artifact_type") != "blind_evaluation":
        errors.append("blind_evaluation.artifact must be schema 1.0 artifact_type=blind_evaluation")
    if not _meaningful(report.get("evaluation_id")) or not _iso_datetime(report.get("generated_at")):
        errors.append("blind_evaluation.artifact requires evaluation_id and generated_at")

    provenance = report.get("provenance")
    case_ids: list[str] = []
    grades: dict[str, dict[str, dict[str, int]]] = {"candidate": {}, "challenger": {}}
    if not isinstance(provenance, dict):
        errors.append("blind_evaluation.artifact provenance is required")
    else:
        for field in ("evaluator_id", "evaluation_method", "candidate_id", "challenger_id"):
            if not _meaningful(provenance.get(field)):
                errors.append(f"blind_evaluation.artifact provenance.{field} is required")
        if provenance.get("candidate_id") == provenance.get("challenger_id"):
            errors.append("blind_evaluation.artifact provenance candidate and challenger must differ")
        _validate_candidate_identity(
            provenance.get("candidate_identity"),
            label="blind_evaluation candidate_identity",
            errors=errors,
            expected=candidate_identity,
        )
        raw_case_ids = provenance.get("case_ids")
        if (
            not isinstance(raw_case_ids, list)
            or not raw_case_ids
            or len(set(raw_case_ids)) != len(raw_case_ids)
            or not all(_meaningful(item) for item in raw_case_ids)
        ):
            errors.append("blind_evaluation.artifact provenance.case_ids must be non-empty")
        else:
            case_ids = [str(item) for item in raw_case_ids]
        refs = provenance.get("input_artifacts")
        if not isinstance(refs, list) or len(refs) < 2:
            errors.append("blind_evaluation.artifact provenance.input_artifacts needs candidate and challenger inputs")
        else:
            roles: set[str] = set()
            paths: set[Path] = set()
            role_cases: set[tuple[str, str]] = set()
            for index, ref in enumerate(refs):
                ref_label = f"blind_evaluation.artifact provenance.input_artifacts[{index}]"
                path, payload = _verify_artifact_ref(ref, base=artifact.parent, label=ref_label, errors=errors)
                if isinstance(ref, dict):
                    role = str(ref.get("role") or "")
                    if role not in {"candidate", "challenger"}:
                        errors.append(f"{ref_label} role must be candidate or challenger")
                    roles.add(role)
                if path is not None:
                    paths.add(path.resolve())
                if payload is not None:
                    payload_case = str(payload.get("case_id") or payload.get("eval_name") or "")
                    if case_ids and payload_case not in case_ids:
                        errors.append(f"{ref_label} case_id is not declared in provenance.case_ids")
                    if (role, payload_case) in role_cases:
                        errors.append(f"{ref_label} duplicates role/case input")
                    role_cases.add((role, payload_case))
                    if role == "candidate":
                        _validate_candidate_identity(
                            payload.get("candidate_identity"),
                            label=f"blind_evaluation candidate input {payload_case}",
                            errors=errors,
                            expected=candidate_identity,
                        )
            if roles != {"candidate", "challenger"}:
                errors.append("blind_evaluation.artifact provenance must bind both candidate and challenger")
            if len(paths) != len(refs):
                errors.append("blind_evaluation.artifact provenance input artifacts must be distinct")
            if case_ids:
                expected_role_cases = {
                    (role, case_id)
                    for role in ("candidate", "challenger")
                    for case_id in case_ids
                }
                if role_cases != expected_role_cases:
                    errors.append(
                        "blind_evaluation.artifact provenance.input_artifacts must cover every role/case"
                    )

        specs = _validate_assertion_specs(
            provenance.get("assertion_specs"),
            artifact_base=artifact.parent,
            case_ids=case_ids,
            errors=errors,
        )
        grades = _validate_blind_gradings(
            provenance.get("grading_artifacts"),
            artifact_base=artifact.parent,
            case_ids=case_ids,
            specs=specs,
            evaluator_id=provenance.get("evaluator_id"),
            candidate_identity=candidate_identity,
            errors=errors,
        )

    summary = report.get("summary")
    if not isinstance(summary, dict):
        errors.append("blind_evaluation.artifact summary is required")
        return
    complete_grades = bool(case_ids) and all(
        set(grades[role]) == set(case_ids) for role in ("candidate", "challenger")
    )
    if complete_grades:
        candidate_rows = [grades["candidate"][case_id] for case_id in case_ids]
        challenger_rows = [grades["challenger"][case_id] for case_id in case_ids]
        candidate_passed = sum(row["passed"] for row in candidate_rows)
        candidate_total = sum(row["total"] for row in candidate_rows)
        challenger_passed = sum(row["passed"] for row in challenger_rows)
        challenger_total = sum(row["total"] for row in challenger_rows)
        critical_failures = sum(row["critical_failures"] for row in candidate_rows)
        candidate_not_worse = (
            candidate_total > 0
            and challenger_total > 0
            and candidate_passed / candidate_total
            >= challenger_passed / challenger_total - 1e-12
        )
        # Assertion pass rates are diagnostics.  A non-critical miss cannot
        # compensate for, or be promoted into, a hard failure.  Only a fixed
        # critical assertion failure blocks at this layer; the frozen
        # independent judgment interprets the broader comparison.
        status = "pass" if critical_failures == 0 else "fail"
        derived = {
            "status": status,
            "critical_failures": critical_failures,
            "candidate_not_worse": candidate_not_worse,
        }
        for field, expected in derived.items():
            if summary.get(field) != expected:
                errors.append(
                    f"blind_evaluation.artifact summary.{field} is not derived from fixed assertion results"
                )
            if descriptor.get(field) != expected:
                errors.append(
                    f"blind_evaluation.{field} is not derived from fixed assertion results"
                )
    else:
        for field in ("status", "critical_failures", "candidate_not_worse"):
            if summary.get(field) != descriptor.get(field):
                errors.append(f"blind_evaluation.{field} does not match blind_evaluation.artifact summary")

    if summary.get("status") != "pass" or summary.get("critical_failures") != 0:
        errors.append("blind_evaluation.artifact must pass with zero derived critical failures")


def _validate_actuals_validation_receipt(
    raw: object,
    *,
    expected_case: str,
    scored_at: object,
    label: str,
    errors: list[str],
) -> dict | None:
    """Use the scorer's canonical receipt contract at promotion time."""
    receipt_errors = validate_actuals_receipt(
        raw,
        expected_case=expected_case,
        scored_at=scored_at,
        label=label,
    )
    errors.extend(receipt_errors)
    return raw if not receipt_errors and isinstance(raw, dict) else None


def _validate_scored_evaluation(
    payload: dict,
    *,
    expected_case: str,
    label: str,
    candidate_identity: dict[str, str] | None = None,
    errors: list[str],
) -> tuple[dict[str, dict[str, float]] | None, dict | None]:
    if payload.get("case_id") != expected_case:
        errors.append(f"{label} case_id does not match {expected_case}")
    for field in (
        "hash_verified",
        "seal_reverified_after_scoring",
        "actuals_retrieved_after_seal",
    ):
        if payload.get(field) is not True:
            errors.append(f"{label} requires {field}=true")
    if payload.get("forecast_seal_receipt_status") != FORECAST_SEAL_RECEIPT_STATUS_VERIFIED:
        errors.append(
            f"{label} requires forecast_seal_receipt_status="
            f"{FORECAST_SEAL_RECEIPT_STATUS_VERIFIED}"
        )
    if "receipt_verified" in payload:
        errors.append(
            f"{label} prohibits ambiguous legacy receipt_verified; use "
            "forecast_seal_receipt_status"
        )
    if not _meaningful(payload.get("seal_hash")) or not _iso_datetime(payload.get("scored_at")):
        errors.append(f"{label} requires seal_hash and scored_at provenance")
    actuals_receipt = _validate_actuals_validation_receipt(
        payload.get("actuals_validation_receipt"),
        expected_case=expected_case,
        scored_at=payload.get("scored_at"),
        label=label,
        errors=errors,
    )
    if candidate_identity is not None:
        _validate_candidate_identity(
            payload.get("candidate_identity"),
            label=f"holdout candidate evaluation {expected_case}",
            errors=errors,
            expected=candidate_identity,
        )
    metrics = payload.get("metrics")
    counts = payload.get("metric_observation_counts")
    if not isinstance(metrics, dict) or not isinstance(counts, dict):
        errors.append(f"{label} requires metrics and metric_observation_counts")
        return None, actuals_receipt
    parsed: dict[str, dict[str, float]] = {}
    for metric, (error_field, bias_field, interval_field) in HOLDOUT_METRIC_FIELDS.items():
        fields = (error_field, bias_field, interval_field)
        if any(not _finite(metrics.get(field)) for field in fields):
            errors.append(f"{label} missing finite {metric} error/bias/interval metrics")
            continue
        if any(not isinstance(counts.get(field), int) or counts.get(field, 0) <= 0 for field in fields):
            errors.append(f"{label} has no observations for {metric} error/bias/interval metrics")
            continue
        parsed[metric] = {
            "error": float(metrics[error_field]),
            "signed_bias": float(metrics[bias_field]),
            "interval_score": float(metrics[interval_field]),
        }
    return (parsed if set(parsed) == PROFIT_METRICS else None), actuals_receipt


def _validate_holdout_evaluation_units(
    raw: object,
    *,
    case_ids: list[str],
    errors: list[str],
) -> dict[str, dict[str, object]]:
    """Bind statistical cases to economic entities, dates and regimes.

    A different case label is not an independent sample. Multiple cutoffs for
    one issuer stay in one entity cluster and are averaged inside that cluster;
    at least two issuers are required before accuracy can be claimed.
    """

    units: dict[str, dict[str, object]] = {}
    if not isinstance(raw, list) or not raw:
        errors.append("holdout.artifact provenance.evaluation_units is required")
        return units
    for index, row in enumerate(raw):
        label = f"holdout.artifact provenance.evaluation_units[{index}]"
        if not isinstance(row, dict):
            errors.append(f"{label} must be an object")
            continue
        case_id = str(row.get("case_id") or "").strip()
        if not case_id or (case_ids and case_id not in case_ids):
            errors.append(f"{label}.case_id is not declared")
            continue
        if case_id in units:
            errors.append(f"{label} duplicates case_id {case_id}")
            continue
        for field in (
            "entity_cluster_id",
            "horizon_id",
            "mechanism",
            "cycle_or_lifecycle_regime",
        ):
            if not _meaningful(row.get(field)):
                errors.append(f"{label}.{field} is required")
        horizon_period_ids = row.get("horizon_period_ids")
        if (
            not isinstance(horizon_period_ids, list)
            or not horizon_period_ids
            or len(set(horizon_period_ids)) != len(horizon_period_ids)
            or any(not _meaningful(item) for item in horizon_period_ids)
        ):
            errors.append(f"{label}.horizon_period_ids must contain unique receipt period identities")
        if not _iso_datetime(row.get("as_of")):
            errors.append(f"{label}.as_of must be an ISO timestamp")
        start = _date_value(row.get("target_period_start"))
        end = _date_value(row.get("target_period_end"))
        cutoff = _date_value(row.get("as_of"))
        if start is None or end is None:
            errors.append(f"{label} target_period_start/end must be ISO dates")
        elif end < start:
            errors.append(f"{label} target period ends before it starts")
        if cutoff is not None and end is not None and cutoff > end:
            errors.append(f"{label}.as_of cannot be after the target period")
        units[case_id] = row
    if case_ids and set(units) != set(case_ids):
        errors.append(
            "holdout.artifact provenance.evaluation_units must cover every declared case"
        )
    clusters = {
        str(row.get("entity_cluster_id") or "").strip()
        for row in units.values()
        if _meaningful(row.get("entity_cluster_id"))
    }
    if len(clusters) < 2:
        errors.append(
            "validated_on_holdout requires at least two distinct entity clusters; "
            "two cutoffs or overlapping horizons of one issuer remain one cluster"
        )
    return units


def _bind_evaluation_unit_to_actuals_receipt(
    unit: dict[str, object],
    receipt: dict,
    *,
    case_id: str,
    errors: list[str],
) -> None:
    """Prevent a declared holdout entity/horizon from drifting from scored facts."""
    label = f"holdout {case_id} evaluation_unit"
    if unit.get("entity_cluster_id") != receipt.get("entity_id"):
        errors.append(f"{label}.entity_cluster_id does not match the actuals receipt entity_id")
    observations = receipt.get("validated_observations")
    if not isinstance(observations, list) or not observations:
        return
    period_dates: dict[str, tuple[str, str]] = {}
    for observation in observations:
        if not isinstance(observation, dict):
            continue
        period = str(observation.get("period") or "").strip()
        start = str(observation.get("fiscal_period_start") or "").strip()
        end = str(observation.get("fiscal_period_end") or "").strip()
        if period and start and end:
            period_dates.setdefault(period, (start, end))
    receipt_period_ids = sorted(period_dates)
    declared_period_ids = sorted(
        str(item) for item in (unit.get("horizon_period_ids") or [])
        if _meaningful(item)
    )
    if declared_period_ids != receipt_period_ids:
        errors.append(f"{label}.horizon_period_ids do not match validated actual periods")
    if period_dates:
        expected_start = min(start for start, _ in period_dates.values())
        expected_end = max(end for _, end in period_dates.values())
        if unit.get("target_period_start") != expected_start:
            errors.append(f"{label}.target_period_start does not match validated actual periods")
        if unit.get("target_period_end") != expected_end:
            errors.append(f"{label}.target_period_end does not match validated actual periods")


def _validate_holdout_artifact(
    descriptor: dict,
    *,
    evidence_base: Path,
    candidate_identity: dict[str, str] | None,
    errors: list[str],
) -> None:
    artifact, report = _load_bound_json(
        descriptor, base=evidence_base, label="holdout", errors=errors
    )
    if artifact is None or report is None:
        return
    if report.get("schema_version") != "1.0" or report.get("artifact_type") != "holdout_comparison":
        errors.append("holdout.artifact must be schema 1.0 artifact_type=holdout_comparison")
    if not _meaningful(report.get("evaluation_id")) or not _iso_datetime(report.get("generated_at")):
        errors.append("holdout.artifact requires evaluation_id and generated_at")

    provenance = report.get("provenance")
    computed: dict[str, dict[str, float | bool]] = {}
    cluster_diagnostics: dict[str, dict[str, float | bool]] = {}
    evaluation_units: dict[str, dict[str, object]] = {}
    if not isinstance(provenance, dict):
        errors.append("holdout.artifact provenance is required")
    else:
        for field in ("candidate_id", "challenger_id"):
            if not _meaningful(provenance.get(field)):
                errors.append(f"holdout.artifact provenance.{field} is required")
        if provenance.get("candidate_id") == provenance.get("challenger_id"):
            errors.append("holdout.artifact provenance candidate and challenger must differ")
        _validate_candidate_identity(
            provenance.get("candidate_identity"),
            label="holdout candidate_identity",
            errors=errors,
            expected=candidate_identity,
        )
        case_ids = provenance.get("case_ids")
        if (
            not isinstance(case_ids, list)
            or len(case_ids) < 2
            or len(set(case_ids)) != len(case_ids)
            or not all(_meaningful(item) for item in case_ids)
        ):
            errors.append("holdout.artifact provenance.case_ids requires at least two unique holdouts")
            case_ids = []
        evaluation_units = _validate_holdout_evaluation_units(
            provenance.get("evaluation_units"),
            case_ids=case_ids,
            errors=errors,
        )

        evaluations: dict[str, dict[str, dict[str, dict[str, float]]]] = {
            "candidate": {},
            "challenger": {},
        }
        actuals_receipts: dict[str, dict[str, dict]] = {
            "candidate": {},
            "challenger": {},
        }
        for role in ("candidate", "challenger"):
            key = f"{role}_evaluation_artifacts"
            refs = provenance.get(key)
            if not isinstance(refs, list):
                errors.append(f"holdout.artifact provenance.{key} is required")
                continue
            for index, ref in enumerate(refs):
                ref_label = f"holdout.artifact provenance.{key}[{index}]"
                _, payload = _verify_artifact_ref(ref, base=artifact.parent, label=ref_label, errors=errors)
                case_id = str(ref.get("case_id") or "") if isinstance(ref, dict) else ""
                if not _meaningful(case_id) or (case_ids and case_id not in case_ids):
                    errors.append(f"{ref_label} case_id is not declared")
                    continue
                if case_id in evaluations[role]:
                    errors.append(f"{ref_label} duplicates case_id {case_id}")
                    continue
                if payload is not None:
                    parsed, actuals_receipt = _validate_scored_evaluation(
                        payload,
                        expected_case=case_id,
                        label=ref_label,
                        candidate_identity=candidate_identity if role == "candidate" else None,
                        errors=errors,
                    )
                    if parsed is not None:
                        evaluations[role][case_id] = parsed
                    if actuals_receipt is not None:
                        actuals_receipts[role][case_id] = actuals_receipt
            if case_ids and set(evaluations[role]) != set(case_ids):
                errors.append(f"holdout.artifact provenance.{key} must cover every declared case")

        for case_id in case_ids:
            candidate_actuals = actuals_receipts["candidate"].get(case_id)
            challenger_actuals = actuals_receipts["challenger"].get(case_id)
            if candidate_actuals is None or challenger_actuals is None:
                errors.append(
                    f"holdout {case_id} candidate and challenger both require "
                    "locally-consistent untrusted actuals receipts"
                )
                continue
            if candidate_actuals.get("actuals_sha256") != challenger_actuals.get("actuals_sha256"):
                errors.append(
                    f"holdout {case_id} candidate and challenger were not scored against identical actuals"
                )
            if candidate_actuals.get("validated_observations") != challenger_actuals.get("validated_observations"):
                errors.append(
                    f"holdout {case_id} candidate and challenger actual-observation receipts differ"
                )
            unit = evaluation_units.get(case_id)
            if isinstance(unit, dict):
                _bind_evaluation_unit_to_actuals_receipt(
                    unit,
                    candidate_actuals,
                    case_id=case_id,
                    errors=errors,
                )

        if (
            case_ids
            and set(evaluation_units) == set(case_ids)
            and all(set(evaluations[role]) == set(case_ids) for role in evaluations)
        ):
            entity_clusters = sorted(
                {
                    str(evaluation_units[case]["entity_cluster_id"])
                    for case in case_ids
                }
            )
            if len(entity_clusters) < 2:
                entity_clusters = []
            for metric in sorted(PROFIT_METRICS):
                if not entity_clusters:
                    continue
                candidate_cluster_rows: list[dict[str, float]] = []
                challenger_cluster_rows: list[dict[str, float]] = []
                for entity_cluster in entity_clusters:
                    cluster_cases = [
                        case
                        for case in case_ids
                        if str(evaluation_units[case]["entity_cluster_id"]) == entity_cluster
                    ]
                    for role, target in (
                        ("candidate", candidate_cluster_rows),
                        ("challenger", challenger_cluster_rows),
                    ):
                        rows = [evaluations[role][case][metric] for case in cluster_cases]
                        target.append(
                            {
                                field: sum(row[field] for row in rows) / len(rows)
                                for field in ("error", "signed_bias", "interval_score")
                            }
                        )
                candidate_error = sum(row["error"] for row in candidate_cluster_rows) / len(candidate_cluster_rows)
                challenger_error = sum(row["error"] for row in challenger_cluster_rows) / len(challenger_cluster_rows)
                computed[metric] = {
                    "candidate_error": candidate_error,
                    "challenger_error": challenger_error,
                    "candidate_not_worse": candidate_error <= challenger_error + 1e-12,
                    "signed_bias": sum(row["signed_bias"] for row in candidate_cluster_rows) / len(candidate_cluster_rows),
                    "interval_score": sum(row["interval_score"] for row in candidate_cluster_rows) / len(candidate_cluster_rows),
                }
                leave_one_out_deltas: list[float] = []
                for excluded in range(len(entity_clusters)):
                    candidate_kept = [
                        row for index, row in enumerate(candidate_cluster_rows) if index != excluded
                    ]
                    challenger_kept = [
                        row for index, row in enumerate(challenger_cluster_rows) if index != excluded
                    ]
                    if not candidate_kept:
                        continue
                    leave_one_out_deltas.append(
                        sum(row["error"] for row in candidate_kept) / len(candidate_kept)
                        - sum(row["error"] for row in challenger_kept) / len(challenger_kept)
                    )
                cluster_diagnostics[metric] = {
                    "all_candidate_not_worse": bool(leave_one_out_deltas)
                    and max(leave_one_out_deltas) <= 1e-12,
                    "max_candidate_minus_challenger_error": max(leave_one_out_deltas),
                }

    summary = report.get("summary")
    if not isinstance(summary, dict):
        errors.append("holdout.artifact summary is required")
        return
    for field in ("status", "right_reason_ok", "new_systematic_bias"):
        if summary.get(field) != descriptor.get(field):
            errors.append(f"holdout.{field} does not match holdout.artifact summary")
    if summary.get("status") != "pass" or summary.get("right_reason_ok") is not True:
        errors.append("holdout.artifact summary must pass the right-reason check")
    entity_clusters = {
        str(row.get("entity_cluster_id") or "").strip()
        for row in evaluation_units.values()
        if _meaningful(row.get("entity_cluster_id"))
    }
    if summary.get("entity_cluster_count") != len(entity_clusters):
        errors.append("holdout.artifact summary.entity_cluster_count is not derived")
    if summary.get("case_count") != len(evaluation_units):
        errors.append("holdout.artifact summary.case_count is not derived")
    reported_loo = summary.get("leave_one_entity_out")
    if not isinstance(reported_loo, dict):
        errors.append("holdout.artifact summary.leave_one_entity_out is required")
    else:
        for metric, calculated in cluster_diagnostics.items():
            row = reported_loo.get(metric)
            if not isinstance(row, dict):
                errors.append(f"holdout.artifact leave_one_entity_out.{metric} is required")
                continue
            if row.get("all_candidate_not_worse") is not calculated["all_candidate_not_worse"]:
                errors.append(
                    f"holdout.artifact leave_one_entity_out.{metric}.all_candidate_not_worse is not derived"
                )
            if not _close(
                row.get("max_candidate_minus_challenger_error"),
                calculated["max_candidate_minus_challenger_error"],
            ):
                errors.append(
                    f"holdout.artifact leave_one_entity_out.{metric}.max_candidate_minus_challenger_error is not derived"
                )

    report_metrics = summary.get("metrics")
    evidence_metrics = descriptor.get("metrics")
    if not isinstance(report_metrics, dict) or not isinstance(evidence_metrics, dict):
        errors.append("holdout.metrics and holdout.artifact summary.metrics are required")
        return
    for metric in sorted(PROFIT_METRICS):
        calculated = computed.get(metric)
        artifact_row = report_metrics.get(metric)
        evidence_row = evidence_metrics.get(metric)
        if not isinstance(artifact_row, dict) or not isinstance(evidence_row, dict):
            errors.append(f"holdout.metrics.{metric} and artifact summary row are required")
            continue
        if calculated is None:
            continue
        for field in ("candidate_error", "challenger_error", "signed_bias", "interval_score"):
            if not _close(artifact_row.get(field), calculated[field]):
                errors.append(f"holdout.artifact summary.metrics.{metric}.{field} is not derived from evaluations")
            if not _close(evidence_row.get(field), artifact_row.get(field)):
                errors.append(f"holdout.metrics.{metric}.{field} does not match holdout.artifact summary")
        if artifact_row.get("candidate_not_worse") is not calculated["candidate_not_worse"]:
            errors.append(f"holdout.artifact summary.metrics.{metric}.candidate_not_worse is not derived")
        if evidence_row.get("candidate_not_worse") is not artifact_row.get("candidate_not_worse"):
            errors.append(f"holdout.metrics.{metric}.candidate_not_worse does not match artifact summary")


def validate(path: Path, skill_root: Path) -> tuple[list[str], dict]:
    errors: list[str] = []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return [f"cannot read promotion evidence: {exc}"], {}
    if not isinstance(data, dict):
        return ["promotion evidence must be a JSON object"], {}

    if data.get("schema_version") != "1.0":
        errors.append("schema_version must be 1.0")
    change_type = data.get("change_type")
    if change_type not in CHANGE_TYPES:
        errors.append("change_type must be historical_training or method_research")
    candidate_identity = _validate_candidate_identity(
        data.get("candidate_identity"),
        label="candidate_identity",
        errors=errors,
        current_tree_sha256=trainer_tree_sha256(skill_root),
    )

    reflection = _path(data.get("method_reflection"), base=path.parent)
    if reflection is None or not reflection.is_file():
        errors.append("method_reflection must point to an existing file")
    else:
        validator = skill_root / "scripts" / "validate_method_reflection.py"
        result = subprocess.run(
            [sys.executable, str(validator), "--reflection", str(reflection), "--strict"],
            capture_output=True,
            text=True,
        )
        if result.returncode:
            errors.append("method_reflection failed: " + (result.stdout + result.stderr).strip())

    tests = data.get("test_suite")
    if not isinstance(tests, dict):
        errors.append("test_suite is required")
    else:
        if tests.get("suite_id") != PROMOTION_TEST_SUITE_ID:
            errors.append(
                "test_suite.suite_id must select the allowlisted trainer_structural_contracts suite"
            )
        if not _meaningful(tests.get("command")):
            errors.append("test_suite.command is required")
        elif tests.get("command") != " ".join(promotion_test_argv(sys.executable)):
            errors.append("test_suite.command must equal the allowlisted structural-contract command")
        _validate_test_artifact(
            tests,
            evidence_base=path.parent,
            skill_root=skill_root,
            candidate_identity=candidate_identity,
            errors=errors,
        )

    blind = data.get("blind_evaluation")
    if not isinstance(blind, dict):
        errors.append("blind_evaluation is required")
    else:
        _validate_blind_artifact(
            blind,
            evidence_base=path.parent,
            candidate_identity=candidate_identity,
            errors=errors,
        )

    accuracy_claim = data.get("profit_accuracy_claim")
    if change_type == "method_research":
        if accuracy_claim != "not_established":
            errors.append("method_research must set profit_accuracy_claim=not_established")
    elif change_type == "historical_training":
        if accuracy_claim != "validated_on_holdout":
            errors.append("historical_training must set profit_accuracy_claim=validated_on_holdout")
        if not TRUSTED_EXTERNAL_ACTUALS_REGISTRY_AVAILABLE:
            errors.append(
                "historical_training accuracy promotion is fail-closed until a trusted external "
                "actuals registry outside builder control binds raw Actuals, official source "
                "bytes, fact extractions and scored evaluations; local receipts prove internal "
                "consistency only, so use method_research with profit_accuracy_claim=not_established"
            )
        holdout = data.get("holdout")
        if not isinstance(holdout, dict):
            errors.append("historical_training requires holdout evidence")
        else:
            metrics = holdout.get("metrics")
            if not isinstance(metrics, dict):
                errors.append("holdout.metrics is required")
            else:
                for metric in sorted(PROFIT_METRICS):
                    row = metrics.get(metric)
                    if not isinstance(row, dict):
                        errors.append(f"holdout.metrics.{metric} is required")
                        continue
                    for field in (
                        "candidate_error",
                        "challenger_error",
                        "signed_bias",
                        "interval_score",
                    ):
                        if not isinstance(row.get(field), (int, float)):
                            errors.append(f"holdout.metrics.{metric}.{field} must be numeric")
                    if not isinstance(row.get("candidate_not_worse"), bool):
                        errors.append(
                            f"holdout.metrics.{metric}.candidate_not_worse must be a diagnostic boolean"
                        )
            _validate_holdout_artifact(
                holdout,
                evidence_base=path.parent,
                candidate_identity=candidate_identity,
                errors=errors,
            )

    judgment = data.get("independent_judgment")
    if not isinstance(judgment, dict):
        errors.append("independent_judgment is required")
    else:
        expected_artifacts: dict[str, Path | None] = {
            "method_reflection": reflection,
            "test_suite": (
                _path(tests.get("artifact"), base=path.parent)
                if isinstance(tests, dict) else None
            ),
            "blind_evaluation": (
                _path(blind.get("artifact"), base=path.parent)
                if isinstance(blind, dict) else None
            ),
        }
        if change_type == "historical_training":
            holdout = data.get("holdout")
            expected_artifacts["holdout"] = (
                _path(holdout.get("artifact"), base=path.parent)
                if isinstance(holdout, dict) else None
            )
        _validate_independent_judgment(
            judgment,
            evidence_base=path.parent,
            expected_artifacts=expected_artifacts,
            candidate_identity=candidate_identity,
            change_type=str(change_type or ""),
            profit_accuracy_claim=accuracy_claim,
            errors=errors,
        )

    return errors, data


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--evidence", required=True)
    parser.add_argument("--skill-root", required=True)
    args = parser.parse_args()
    errors, data = validate(Path(args.evidence).resolve(), Path(args.skill_root).resolve())
    if errors:
        print(json.dumps({"status": "FAIL", "errors": errors}, ensure_ascii=False, indent=2))
        return 2
    print(
        json.dumps(
            {
                "status": "PASS",
                "change_type": data["change_type"],
                "profit_accuracy_claim": data["profit_accuracy_claim"],
                "independent_review_assurance": ORCHESTRATION_RECEIPT_BOUNDARY,
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
