#!/usr/bin/env python3
"""Deterministically build the companion live production skill.

Copies the trainer skill tree, prunes trainer-only material, installs the
maintained live SKILL.md / openai.yaml / trigger prompts from
`assets/live_release/`, applies a small set of mandatory literal patches,
then audits the result: every `references/`, `scripts/`, `assets/` path
mentioned by the live SKILL.md must exist, every trainer-only path must be
absent, and (with --self-test) the live package self-test must pass.

The live SKILL.md is maintained as a whole file, not derived by regex
surgery, so the production skill can never be mangled by pattern edits.
Stable labeling of the output is a promotion decision, not a build step.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import re
import shutil
import stat
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

_SCRIPT_DIR = Path(__file__).resolve().parent
if str(_SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPT_DIR))

from validate_promotion_evidence import (
    PROMOTION_TEST_SUITE_ID,
    promotion_test_argv,
    trainer_tree_sha256,
)
from artifact_registry import resolve_active_paths
from package_self_test import LIVE_REQUIRED

LIVE_SKILL_NAME = "technology-company-profit-forecasting"

# Directories and files that must never ship in the production skill.
TRAINER_ONLY_PATHS = [
    "tests",
    "evals/workflow_cases.jsonl",
    "evals/codex_parity_cases.jsonl",
    "assets/benchmarks",
    "assets/reports",
    "assets/examples/sandisk_v73",
    "assets/examples/generic_v80/Technology_Company_Forecasting_v8.0_Training_Curriculum.xlsx",
    "assets/live_release",
    "assets/skill_system",
    "assets/schemas/backtest_result.schema.json",
    "assets/schemas/forecast_case.schema.json",
    "references/historical-training-loop.md",
    "references/training-curriculum.md",
    "references/live-mode-release.md",
    "references/validated-benchmarks.md",
    "references/schemas.md",
    "references/companion-live-skill-contract.md",
]

# Training/promotion templates removed from the live profile. Shared runtime
# code reads assets/profile.json and never opens training-only state in live.
TRAINER_ONLY_TEMPLATES = [
    "assets/templates/case_template.json",
    "assets/templates/forecast_error_taxonomy_template.csv",
    "assets/templates/training_actuals_template.json",
    "assets/templates/mechanism_outcome_predictions_template.json",
    "assets/templates/mechanism_outcome_actuals_template.json",
    "assets/templates/mechanism_outcome_score_contract_template.json",
    "assets/templates/method_reflection_template.md",
    "assets/templates/training_state_template.json",
]

# Single-purpose production has one evidence lifecycle: accept current evidence
# until bundle freeze, then publish a new version for later evidence.  A second
# mode document would be duplicate state, so it is not part of the live package.
PRODUCTION_EXCLUDED_PATHS = [
    "assets/templates/mode_config_template.json",
]

# (relative file, old literal, new literal) - every patch is mandatory; a
# missing literal means the trainer source drifted and the build must fail
# rather than ship a dangling pointer.
LITERAL_PATCHES = [
    ("references/gold-standard-example.md", "assets/examples/sandisk_v73/", "assets/examples/generic_v80/"),
    ("references/codex-parity-execution.md", "assets/examples/sandisk_v73/", "assets/examples/generic_v80/"),
    (
        "assets/examples/generic_v80/README.md",
        "- `Technology_Company_Forecasting_v8.0_Training_Curriculum.xlsx`: formatted development/holdout curriculum and loop checklist.\n",
        "",
    ),
]

PATH_MENTION_RE = re.compile(r"`((?:references|scripts|assets)/[A-Za-z0-9_./-]+)`")


def remove(path: Path) -> None:
    if path.is_dir():
        shutil.rmtree(path)
    elif path.exists():
        path.unlink()


def fail(msg: str) -> int:
    print(json.dumps({"status": "FAIL", "error": msg}, indent=2))
    return 2


def _text_sha256(value: str) -> str:
    return "sha256:" + hashlib.sha256(value.encode("utf-8")).hexdigest()


def run_allowlisted_promotion_tests(
    skill_root: Path,
    suite_id: object,
) -> tuple[dict[str, object] | None, str | None]:
    """Execute the fixed trainer suite without accepting evidence-supplied argv."""

    if suite_id != PROMOTION_TEST_SUITE_ID:
        return None, "promotion evidence did not select an allowlisted test suite"
    argv = promotion_test_argv(sys.executable)
    tree_before = trainer_tree_sha256(skill_root)
    started_at = datetime.now(timezone.utc).isoformat()
    env = os.environ.copy()
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    env["PYTEST_DISABLE_PLUGIN_AUTOLOAD"] = "1"
    for inherited in ("PYTEST_ADDOPTS", "PYTEST_PLUGINS", "PYTHONPATH", "PYTHONHOME"):
        env.pop(inherited, None)
    try:
        result = subprocess.run(
            argv,
            cwd=skill_root,
            capture_output=True,
            text=True,
            env=env,
            timeout=1800,
        )
    except subprocess.TimeoutExpired as exc:
        return None, f"allowlisted promotion test suite timed out after {exc.timeout} seconds"
    finished_at = datetime.now(timezone.utc).isoformat()
    tree_after = trainer_tree_sha256(skill_root)
    report: dict[str, object] = {
        "suite_id": PROMOTION_TEST_SUITE_ID,
        "command_argv": argv,
        "cwd": str(skill_root),
        "started_at": started_at,
        "finished_at": finished_at,
        "tested_tree_sha256": tree_before,
        "exit_code": result.returncode,
        "stdout_sha256": _text_sha256(result.stdout),
        "stderr_sha256": _text_sha256(result.stderr),
    }
    if tree_after != tree_before:
        return report, "allowlisted promotion test suite mutated the trainer tree"
    if result.returncode != 0:
        diagnostic = (result.stdout + "\n" + result.stderr).strip()
        return report, (
            f"allowlisted promotion test suite failed with exit_code={result.returncode}: "
            + diagnostic[-12000:]
        )
    return report, None


def main() -> int:
    parser = argparse.ArgumentParser(description="Build the live production skill from the trainer skill.")
    parser.add_argument("--trainer-skill-root", required=True)
    parser.add_argument("--output-root", required=True, help="Output skill directory; conventionally ends in technology-company-profit-forecasting")
    parser.add_argument("--self-test", action="store_true", help="Run the live package self-test on the output")
    parser.add_argument(
        "--promote",
        action="store_true",
        help="Mark the candidate release-eligible only after promotion evidence passes",
    )
    parser.add_argument(
        "--promotion-evidence",
        help="JSON evidence for anti-drift promotion; required with --promote",
    )
    args = parser.parse_args()

    src = Path(args.trainer_skill_root).resolve()
    out = Path(args.output_root).resolve()
    template_dir = src / "assets" / "live_release"

    promotion: dict[str, object] | None = None
    promotion_test_run: dict[str, object] | None = None
    if args.promote:
        if not args.self_test:
            return fail("--promote requires --self-test")
        if not args.promotion_evidence:
            return fail("--promote requires --promotion-evidence")
        promotion_path = Path(args.promotion_evidence).resolve()
        validator = src / "scripts" / "validate_promotion_evidence.py"
        result = subprocess.run(
            [
                sys.executable,
                str(validator),
                "--evidence",
                str(promotion_path),
                "--skill-root",
                str(src),
            ],
            capture_output=True,
            text=True,
        )
        if result.returncode:
            return fail("promotion evidence failed: " + (result.stdout + result.stderr).strip())
        promotion = json.loads(promotion_path.read_text(encoding="utf-8"))
        promotion_test_run, test_error = run_allowlisted_promotion_tests(
            src,
            (promotion.get("test_suite") or {}).get("suite_id")
            if isinstance(promotion.get("test_suite"), dict)
            else None,
        )
        if test_error:
            return fail(test_error)
    elif args.promotion_evidence:
        return fail("--promotion-evidence has no effect without --promote")

    for required in [
        src / "SKILL.md",
        template_dir / "SKILL.md",
        template_dir / "openai.yaml",
        template_dir / "trigger_prompts.jsonl",
        src / "assets" / "profile.json",
        src / "assets" / "runtime_ownership.json",
    ]:
        if not required.exists():
            return fail(f"missing trainer input: {required}")

    runtime_ownership = json.loads(
        (src / "assets" / "runtime_ownership.json").read_text(encoding="utf-8")
    )
    if runtime_ownership.get("schema_version") != "forecast-runtime-ownership/v1":
        return fail("invalid runtime ownership schema")
    ownership_profiles = runtime_ownership.get("profiles")
    if not isinstance(ownership_profiles, dict):
        return fail("runtime ownership profiles must be an object")
    runtime_entries: list[dict[str, str]] = []
    for owner in ("shared", "live"):
        entries = ownership_profiles.get(owner)
        if not isinstance(entries, list) or not entries:
            return fail(f"runtime ownership {owner} must be a non-empty array")
        for entry in entries:
            if not isinstance(entry, dict):
                return fail(f"runtime ownership {owner} entry must be an object")
            source = entry.get("source")
            target = entry.get("target")
            if (
                not isinstance(source, str)
                or not isinstance(target, str)
                or not source.endswith(".py")
                or not target.startswith("scripts/")
                or not target.endswith(".py")
            ):
                return fail(f"invalid runtime ownership entry: {entry}")
            if not (src / source).is_file():
                return fail(f"owned runtime source is missing: {source}")
            runtime_entries.append({"source": source, "target": target})
    runtime_targets = [entry["target"] for entry in runtime_entries]
    if len(runtime_targets) != len(set(runtime_targets)):
        return fail("live runtime ownership has duplicate targets")
    runtime_script_names = [Path(target).name for target in runtime_targets]

    # Refuse overlapping paths BEFORE any destructive step: an out that equals
    # or contains (or sits inside) the trainer source would delete the method.
    if src == out or src in out.parents or out in src.parents:
        return fail(f"trainer-skill-root and output-root overlap ({src} vs {out}); refusing")
    if out.exists():
        shutil.rmtree(out)
    out.mkdir(parents=True)

    # Positive ownership build.  Start from the package self-test contract,
    # then add files reached by the live entrypoint, canonical stage registry,
    # live artifact registry and shared runtime profile.  An unrelated trainer
    # file is absent by construction; negative lists below remain assurance,
    # not the mechanism that defines production.
    live_skill_text = (template_dir / "SKILL.md").read_text(encoding="utf-8")
    source_method = json.loads(
        (src / "assets" / "method_system.json").read_text(encoding="utf-8")
    )
    source_registry = json.loads(
        (src / "assets" / "artifact_registry.json").read_text(encoding="utf-8")
    )
    owned_files = set(LIVE_REQUIRED)
    owned_files.update(PATH_MENTION_RE.findall(live_skill_text))
    for stage in source_method.get("stages", []):
        if isinstance(stage, dict):
            owned_files.update(
                rel for rel in (stage.get("files") or []) if isinstance(rel, str)
            )
    for artifact in source_registry.get("artifacts", []):
        if not isinstance(artifact, dict) or "live" not in (artifact.get("profiles") or []):
            continue
        if artifact.get("path") == "mode_config.json":
            continue
        template = artifact.get("template")
        if isinstance(template, str) and template:
            owned_files.add(template)
    owned_files.update(rel for rel, _old, _new in LITERAL_PATCHES)
    owned_files.difference_update(PRODUCTION_EXCLUDED_PATHS)
    if (src / "LICENSE.txt").is_file():
        owned_files.add("LICENSE.txt")

    maintained_outputs = {
        "SKILL.md",
        "agents/openai.yaml",
        "evals/trigger_prompts.jsonl",
        *runtime_targets,
    }
    for rel in sorted(owned_files - maintained_outputs):
        source = src / rel
        if not source.is_file():
            return fail(f"owned live source is missing: {rel}")
        destination = out / rel
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination)

    # Install the maintained live profile files.
    shutil.copy2(template_dir / "SKILL.md", out / "SKILL.md")
    (out / "agents").mkdir(exist_ok=True)
    shutil.copy2(template_dir / "openai.yaml", out / "agents" / "openai.yaml")
    (out / "evals").mkdir(exist_ok=True)
    shutil.copy2(template_dir / "trigger_prompts.jsonl", out / "evals" / "trigger_prompts.jsonl")
    for entry in runtime_entries:
        target = out / entry["target"]
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src / entry["source"], target)
    (out / "assets" / "profile.json").write_text(
        json.dumps(
            {
                "schema_version": "forecast-skill-profile/v1",
                "profile": "live",
                "runtime_scripts": runtime_script_names,
            },
            ensure_ascii=False,
            indent=2,
        ) + "\n",
        encoding="utf-8",
    )

    # Convert shared configuration into a live-only runtime contract instead of
    # shipping trainer profiles or references to files pruned above.
    method_path = out / "assets" / "method_system.json"
    method = json.loads(method_path.read_text(encoding="utf-8"))
    live_profile = (method.get("profiles") or {}).get("live")
    if not isinstance(live_profile, dict):
        return fail("assets/method_system.json has no live profile")
    method["profiles"] = {"live": live_profile}
    for stage in method.get("stages", []):
        if not isinstance(stage, dict):
            continue
        stage["gates"] = [
            gate for gate in (stage.get("gates") or [])
            if not str(gate).startswith("trainer_")
        ]
    method_path.write_text(json.dumps(method, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    manifest_path = out / "assets" / "templates" / "run_manifest_template.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["required_artifacts"] = resolve_active_paths(
        source_registry,
        manifest,
        profile="live",
    )
    manifest["required_artifacts"] = [
        path for path in manifest["required_artifacts"] if path != "mode_config.json"
    ]
    for key in list(manifest):
        if (
            key.startswith("training_")
            or key in {
                "time_boundary_enforced",
                "run_mode",
                "baseline_skill_version",
                "artifact_profile",
            }
        ):
            manifest.pop(key)
    manifest_path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )

    fact_template_path = out / "assets" / "templates" / "financial_fact_ledger_template.csv"
    with fact_template_path.open(encoding="utf-8-sig", newline="") as handle:
        fact_rows = list(csv.reader(handle))
    cutoff_column = fact_rows[0].index("as_of_cutoff")
    with fact_template_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle, lineterminator="\n")
        writer.writerows(
            [value for index, value in enumerate(row) if index != cutoff_column]
            for row in fact_rows
        )

    for relative_path, removed_fields in (
        (
            "assets/schemas/run_manifest.schema.json",
            {
                "time_boundary_enforced",
                "training_iteration_id",
                "training_pair_id",
                "training_case_role",
                "run_mode",
                "baseline_skill_version",
                "artifact_profile",
            },
        ),
        (
            "assets/schemas/forecast_snapshot.schema.json",
            {"forecast_sealed_before_actuals", "run_mode"},
        ),
    ):
        schema_path = out / relative_path
        schema = json.loads(schema_path.read_text(encoding="utf-8"))
        properties = schema.get("properties") or {}
        for field in removed_fields:
            properties.pop(field, None)
        if isinstance(schema.get("required"), list):
            schema["required"] = [field for field in schema["required"] if field not in removed_fields]
        schema_path.write_text(json.dumps(schema, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    snapshot_template_path = out / "assets" / "templates" / "forecast_snapshot_template.json"
    snapshot_template = json.loads(snapshot_template_path.read_text(encoding="utf-8"))
    snapshot_template.pop("forecast_sealed_before_actuals", None)
    snapshot_template.pop("run_mode", None)
    snapshot_template_path.write_text(
        json.dumps(snapshot_template, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )

    # Source custody keeps observable chronology and vintage metadata.  Case
    # eligibility and outcome permissions belong to the Trainer adapter, not a
    # production SourceRecord.
    source_schema_path = out / "assets" / "schemas" / "source_record.schema.json"
    source_schema = json.loads(source_schema_path.read_text(encoding="utf-8"))
    source_properties = source_schema.get("properties") or {}
    source_properties.pop("as_of_valid", None)
    source_properties.setdefault(
        "available_at",
        {
            "type": "string",
            "format": "date-time",
            "description": "Earliest verified availability to the research process for provenance and vintage audit.",
        },
    )
    source_required = list(source_schema.get("required") or [])
    if "available_at" not in source_required:
        retrieved_index = (
            source_required.index("retrieved_at")
            if "retrieved_at" in source_required
            else len(source_required)
        )
        source_required.insert(retrieved_index, "available_at")
    source_schema["required"] = source_required
    source_schema_path.write_text(
        json.dumps(source_schema, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    source_template_path = out / "assets" / "templates" / "source_manifest_template.json"
    source_template = json.loads(source_template_path.read_text(encoding="utf-8"))
    for source in source_template.get("sources", []):
        if not isinstance(source, dict):
            continue
        source.setdefault(
            "available_at",
            source.get("version_at") or source.get("published_at") or source.get("retrieved_at"),
        )
        source.pop("source_time_status", None)
        source.pop("forecast_permission", None)
    source_template_path.write_text(
        json.dumps(source_template, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    registry_path = out / "assets" / "artifact_registry.json"
    registry = json.loads(registry_path.read_text(encoding="utf-8"))
    live_artifacts = []
    for artifact in registry.get("artifacts", []):
        if not isinstance(artifact, dict) or "live" not in artifact.get("profiles", []):
            continue
        if artifact.get("path") == "mode_config.json":
            continue
        artifact.pop("profiles", None)
        live_artifacts.append(artifact)
    registry["artifacts"] = live_artifacts
    registry_path.write_text(
        json.dumps(registry, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )

    for rel, old, new in LITERAL_PATCHES:
        target = out / rel
        if not target.exists():
            return fail(f"patch target missing: {rel}")
        text = target.read_text(encoding="utf-8")
        if old not in text:
            return fail(f"patch literal not found in {rel}: {old}")
        target.write_text(text.replace(old, new), encoding="utf-8")

    # Audit 1: the live SKILL.md must not reference a pruned path.
    skill_text = (out / "SKILL.md").read_text(encoding="utf-8")
    missing = sorted({m for m in PATH_MENTION_RE.findall(skill_text) if not (out / m).exists()})
    if missing:
        return fail("live SKILL.md references missing paths: " + ", ".join(missing))

    # Audit 2: no trainer-only material may survive.
    survivors = [
        rel
        for rel in TRAINER_ONLY_PATHS + TRAINER_ONLY_TEMPLATES + PRODUCTION_EXCLUDED_PATHS
        if (out / rel).exists()
    ]
    if survivors:
        return fail("trainer-only paths survived the build: " + ", ".join(survivors))

    # Audit 3: the live frontmatter must carry the production name.
    if f"name: {LIVE_SKILL_NAME}" not in skill_text.split("---", 2)[1]:
        return fail(f"live SKILL.md frontmatter must set name: {LIVE_SKILL_NAME}")

    # Audit 4: shared configuration must no longer advertise the trainer or
    # require a pruned training artifact.
    live_method = json.loads(method_path.read_text(encoding="utf-8"))
    live_manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    live_registry = json.loads(registry_path.read_text(encoding="utf-8"))
    if set(live_method.get("profiles") or {}) != {"live"}:
        return fail("live method_system must contain only the live profile")
    serialized_method = json.dumps(live_method, ensure_ascii=False)
    dangling = sorted(
        rel for rel in TRAINER_ONLY_PATHS
        if rel.startswith("references/") and rel in serialized_method
    )
    if dangling:
        return fail("live method_system references pruned files: " + ", ".join(dangling))
    if "training_state.json" in (live_manifest.get("required_artifacts") or []):
        return fail("live run manifest must not require training_state.json")
    if "mode_config.json" in (live_manifest.get("required_artifacts") or []):
        return fail("live run manifest must not require duplicate mode_config.json")
    if any(
        artifact.get("path") == "training_state.json"
        for artifact in live_registry.get("artifacts", [])
        if isinstance(artifact, dict)
    ):
        return fail("live artifact registry must not advertise training_state.json")
    live_runtime_profile = json.loads(
        (out / "assets" / "profile.json").read_text(encoding="utf-8")
    )
    if (
        live_runtime_profile.get("profile") != "live"
        or "allowed_modes" in live_runtime_profile
        or live_runtime_profile.get("runtime_scripts") != runtime_script_names
    ):
        return fail("live runtime profile was not generated correctly")

    for script in (out / "scripts").glob("*.py"):
        script.chmod(script.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)

    if args.self_test:
        result = subprocess.run([sys.executable, str(out / "scripts" / "package_self_test.py"), str(out)], capture_output=True, text=True)
        if result.returncode:
            print(result.stdout)
            print(result.stderr)
            return fail("live package self-test failed")

    # A plain build is a candidate artifact. Promotion eligibility is separate
    # from the subsequent git commit/push and requires explicit evidence.
    print(json.dumps({
        "status": "PASS",
        "profile": "live_forecast_only",
        "skill_name": LIVE_SKILL_NAME,
        "output": str(out),
        "self_test": bool(args.self_test),
        "release_eligible": bool(args.promote),
        "release_is_git_commit": False,
        "change_type": promotion.get("change_type") if promotion else None,
        "profit_accuracy_claim": promotion.get("profit_accuracy_claim") if promotion else "not_evaluated",
        "promotion_test_run": promotion_test_run,
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
