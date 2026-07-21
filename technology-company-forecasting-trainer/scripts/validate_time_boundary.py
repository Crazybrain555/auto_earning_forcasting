#!/usr/bin/env python3
"""Validate runtime mode, snapshot metadata and historical cutoff policy."""
from __future__ import annotations

import argparse
import csv
import datetime as dt
import json
import re
import sys
from pathlib import Path


_SCRIPT_DIR = Path(__file__).resolve().parent
if str(_SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPT_DIR))

from runtime_context import skill_root_from_script
from training_runtime_policy import load_training_profile, require_allowed_mode


QUARANTINE_USES = {"quarantine", "none", "audit-only", "monitor", "monitor-only", "actual_only"}
FORECAST_PHASES = {"forecast", "candidate_revision", "calibration", "untouched_holdout"}


def parse(value: object) -> dt.datetime:
    text = str(value or "").strip()
    if not text:
        raise ValueError("missing date")
    if len(text) == 10:
        text += "T23:59:59Z"
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    parsed = dt.datetime.fromisoformat(text)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=dt.timezone.utc)
    return parsed.astimezone(dt.timezone.utc)


def csv_rows(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--workspace", required=True)
    parser.add_argument("--strict", action="store_true")
    args = parser.parse_args()
    workspace = Path(args.workspace)
    profile = load_training_profile(skill_root_from_script(__file__))
    checks: list[dict[str, object]] = []
    errors: list[dict[str, object]] = []
    warnings: list[dict[str, object]] = []

    def add(name: str, passed: bool, detail: str = "", severity: str = "error") -> None:
        record: dict[str, object] = {
            "check": name,
            "passed": passed,
            "detail": detail,
            "severity": "info" if passed else severity,
        }
        checks.append(record)
        if not passed:
            (errors if severity == "error" else warnings).append(record)

    mode_path = workspace / "mode_config.json"
    try:
        mode = json.loads(mode_path.read_text(encoding="utf-8"))
        if not isinstance(mode, dict):
            raise ValueError("mode_config root must be an object")
        add("mode-config", True)
    except Exception as exc:
        mode = {}
        add("mode-config", False, f"cannot read mode_config.json: {exc}")

    try:
        run_mode = require_allowed_mode(profile, mode.get("run_mode"))
        add("profile-mode", True, run_mode)
    except Exception as exc:
        run_mode = str(mode.get("run_mode") or "")
        add("profile-mode", False, str(exc))

    try:
        cutoff = parse(mode.get("as_of"))
        add("as-of", True, cutoff.isoformat())
    except Exception as exc:
        cutoff = None
        add("as-of", False, str(exc))

    cutoff_flag = mode.get("enforce_source_cutoff")
    expected_cutoff_flag = run_mode == "historical_train"
    if not expected_cutoff_flag:
        add("source-cutoff-policy", False, "this validator is owned by historical_train")
    elif cutoff_flag is not True:
        add("source-cutoff-policy", False, "workspace cutoff policy differs from profile")
    else:
        add("source-cutoff-policy", True, "historical cutoff")

    manifest_path = workspace / "run_manifest.json"
    if manifest_path.exists():
        try:
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            if not isinstance(manifest, dict):
                raise ValueError("run_manifest root must be an object")
            add("manifest-mode", manifest.get("run_mode") == run_mode,
                f"manifest={manifest.get('run_mode')}; mode_config={run_mode}")
            manifest_cutoff = manifest.get("time_boundary_enforced")
            manifest_policy_ok = manifest_cutoff is True
            add("manifest-cutoff-policy", manifest_policy_ok,
                f"manifest={manifest_cutoff}; profile={expected_cutoff_flag}")
            try:
                same_timestamp = cutoff is not None and parse(manifest.get("as_of")) == cutoff
            except Exception:
                same_timestamp = False
            add("manifest-snapshot-time", same_timestamp,
                f"manifest={manifest.get('as_of')}; mode_config={mode.get('as_of')}")
        except Exception as exc:
            add("run-manifest", False, f"cannot read run_manifest.json: {exc}")

    phase = str(mode.get("phase") or "forecast")
    actual_allowed = mode.get("actuals_retrieval_allowed")
    if not isinstance(actual_allowed, bool):
        add("actuals-gate", False, "historical mode requires actuals_retrieval_allowed boolean")
    elif phase in FORECAST_PHASES and actual_allowed:
        add("actuals-gate", False, f"actuals_retrieval_allowed=true during {phase}")
    else:
        add("actuals-gate", True, f"phase={phase}; allowed={actual_allowed}")

    used: set[str] = set()
    for row in csv_rows(workspace / "assumption_register.csv"):
        used.update(
            token.strip()
            for token in re.split(r"[;,| ]+", str(row.get("source_ids") or ""))
            if token.strip()
        )
    signal_rows = csv_rows(workspace / "forward_signal_cards.csv")
    for row in signal_rows:
        if str(row.get("allowed_use") or "").strip().lower() not in QUARANTINE_USES:
            source_id = str(row.get("source_id") or "").strip()
            if source_id:
                used.add(source_id)

    source_path = workspace / "source_manifest.json"
    try:
        sources = json.loads(source_path.read_text(encoding="utf-8")).get("sources", [])
        if not isinstance(sources, list):
            raise ValueError("sources must be an array")
        add("source-manifest", True, f"{len(sources)} sources")
    except Exception as exc:
        sources = []
        add("source-manifest", False, f"cannot read source_manifest.json: {exc}")

    for source in sources:
        if not isinstance(source, dict):
            add("source-record", False, "source record must be an object")
            continue
        source_id = str(source.get("source_id") or "UNKNOWN")
        date_value = source.get("version_at") or source.get("published_at")
        permission = str(
            source.get("forecast_permission") or source.get("allowed_use") or ""
        ).strip().lower()
        status = str(source.get("source_time_status") or "").strip().lower()
        quarantined = permission in QUARANTINE_USES or status.startswith("quarantined")
        try:
            after_cutoff = cutoff is not None and parse(date_value) > cutoff
        except Exception:
            after_cutoff = True
        if cutoff_flag is True and after_cutoff and (not quarantined or source_id in used):
            add(
                f"source-cutoff:{source_id}",
                False,
                f"date={date_value}; quarantined={quarantined}; used={source_id in used}",
            )
        else:
            add(f"source-cutoff:{source_id}", True, f"date={date_value}")

    for row in signal_rows:
        signal_id = str(row.get("signal_id") or "UNKNOWN")
        permission = str(row.get("allowed_use") or "").strip().lower()
        try:
            after_cutoff = cutoff is not None and parse(row.get("published_at")) > cutoff
        except Exception:
            after_cutoff = True
        if cutoff_flag is True and after_cutoff and permission not in QUARANTINE_USES:
            add(f"signal-cutoff:{signal_id}", False, str(row.get("published_at") or ""))
        else:
            add(f"signal-cutoff:{signal_id}", True, str(row.get("published_at") or ""))

    for row in csv_rows(workspace / "data_series_register.csv"):
        series_id = str(row.get("series_id") or "").strip()
        if not series_id or series_id.lower() in {"tbd", "replace"}:
            continue
        for field in ("published_at", "retrieved_at", "available_at", "vintage_at", "revision_at"):
            value = row.get(field)
            try:
                admissible = cutoff is not None and parse(value) <= cutoff
            except Exception:
                admissible = False
            add(
                f"series-cutoff:{series_id}:{field}",
                admissible,
                str(value or ""),
            )

    for row in csv_rows(workspace / "financial_fact_ledger.csv"):
        fact_id = str(row.get("fact_id") or "").strip()
        if not fact_id or fact_id.lower() in {"tbd", "replace"}:
            continue
        for field in ("filed_at", "retrieved_at"):
            value = row.get(field)
            try:
                admissible = cutoff is not None and parse(value) <= cutoff
            except Exception:
                admissible = False
            add(f"fact-cutoff:{fact_id}:{field}", admissible, str(value or ""))
        try:
            declared = parse(row.get("as_of_cutoff"))
            matches = cutoff is not None and declared == cutoff
        except Exception:
            matches = False
        add(
            f"fact-cutoff:{fact_id}:declared-boundary",
            matches,
            str(row.get("as_of_cutoff") or ""),
        )

    if run_mode == "historical_train":
        forbidden = [
            str(item).lower()
            for item in mode.get("forbidden_query_terms", [])
            if str(item).strip()
        ]
        for row in csv_rows(workspace / "historical_query_log.csv"):
            query_id = str(row.get("query_id") or "UNKNOWN")
            query = str(row.get("query_text") or "").lower()
            flag = str(row.get("future_outcome_terms_used") or "").strip().lower()
            if flag not in {"", "false", "0", "no", "none"}:
                add(f"query-future-flag:{query_id}", False, flag)
            bad = [term for term in forbidden if term in query]
            if bad:
                add(f"query-forbidden:{query_id}", False, ",".join(bad))
            try:
                if cutoff is not None and parse(row.get("cutoff")) != cutoff:
                    add(f"query-cutoff:{query_id}", False, str(row.get("cutoff") or ""))
            except Exception:
                add(f"query-cutoff:{query_id}", False, "invalid/missing cutoff")

        if phase in FORECAST_PHASES:
            leaking = []
            for path in workspace.rglob("*"):
                if not path.is_file():
                    continue
                name = path.name.lower()
                if any(token in name for token in ("actuals", "evaluation", "score")):
                    leaking.append(str(path.relative_to(workspace)))
            add(
                "pre-seal-actual-files",
                not leaking,
                ", ".join(leaking[:20]),
            )

    result = {
        "workspace": str(workspace),
        "profile": profile["profile"],
        "run_mode": run_mode,
        "phase": phase,
        "as_of": mode.get("as_of"),
        "passed": not errors,
        "errors": len(errors),
        "warnings": len(warnings),
        "checks": checks,
    }
    (workspace / "time_boundary_validation.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if not errors else 2


if __name__ == "__main__":
    raise SystemExit(main())
