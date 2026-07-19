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
import json
import re
import shutil
import stat
import subprocess
import sys
from pathlib import Path

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
    "assets/schemas/backtest_result.schema.json",
    "assets/schemas/forecast_case.schema.json",
    "references/historical-training-loop.md",
    "references/training-curriculum.md",
    "references/live-mode-release.md",
    "references/validated-benchmarks.md",
    "references/schemas.md",
    "references/companion-live-skill-contract.md",
]

# Training/promotion templates removed from the live profile. Note that
# training_state_template.json and mode_config_template.json stay: the live
# scaffold_delivery.py reads both when creating any delivery workspace.
TRAINER_ONLY_TEMPLATES = [
    "assets/templates/case_template.json",
    "assets/templates/forecast_error_taxonomy_template.csv",
    "assets/templates/training_actuals_template.json",
    "assets/templates/mechanism_outcome_predictions_template.json",
    "assets/templates/mechanism_outcome_actuals_template.json",
    "assets/templates/mechanism_outcome_score_contract_template.json",
]

KEEP_SCRIPTS = {
    "scaffold_delivery.py",
    "validate_time_boundary.py",
    "validate_research_completeness.py",
    "validate_forward_evidence_workspace.py",
    "validate_delivery.py",
    "freeze_snapshot.py",
    "package_self_test.py",
}

# (relative file, old literal, new literal) - every patch is mandatory; a
# missing literal means the trainer source drifted and the build must fail
# rather than ship a dangling pointer.
LITERAL_PATCHES = [
    ("references/gold-standard-example.md", "assets/examples/sandisk_v73/", "assets/examples/generic_v80/"),
    ("references/codex-parity-execution.md", "assets/examples/sandisk_v73/", "assets/examples/generic_v80/"),
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


def main() -> int:
    parser = argparse.ArgumentParser(description="Build the live production skill from the trainer skill.")
    parser.add_argument("--trainer-skill-root", required=True)
    parser.add_argument("--output-root", required=True, help="Output skill directory; conventionally ends in technology-company-profit-forecasting")
    parser.add_argument("--self-test", action="store_true", help="Run the live package self-test on the output")
    args = parser.parse_args()

    src = Path(args.trainer_skill_root).resolve()
    out = Path(args.output_root).resolve()
    template_dir = src / "assets" / "live_release"

    for required in [src / "SKILL.md", template_dir / "SKILL.md", template_dir / "openai.yaml", template_dir / "trigger_prompts.jsonl"]:
        if not required.exists():
            return fail(f"missing trainer input: {required}")

    # Refuse overlapping paths BEFORE any destructive step: an out that equals
    # or contains (or sits inside) the trainer source would delete the method.
    if src == out or src in out.parents or out in src.parents:
        return fail(f"trainer-skill-root and output-root overlap ({src} vs {out}); refusing")
    if out.exists():
        shutil.rmtree(out)
    shutil.copytree(src, out, ignore=shutil.ignore_patterns("__pycache__", "*.pyc", ".DS_Store"))

    for rel in TRAINER_ONLY_PATHS + TRAINER_ONLY_TEMPLATES:
        remove(out / rel)
    for script in list((out / "scripts").glob("*")):
        if script.is_file() and script.name not in KEEP_SCRIPTS:
            script.unlink()

    # Install the maintained live profile files.
    shutil.copy2(template_dir / "SKILL.md", out / "SKILL.md")
    (out / "agents").mkdir(exist_ok=True)
    shutil.copy2(template_dir / "openai.yaml", out / "agents" / "openai.yaml")
    (out / "evals").mkdir(exist_ok=True)
    shutil.copy2(template_dir / "trigger_prompts.jsonl", out / "evals" / "trigger_prompts.jsonl")

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
    survivors = [rel for rel in TRAINER_ONLY_PATHS + TRAINER_ONLY_TEMPLATES if (out / rel).exists()]
    if survivors:
        return fail("trainer-only paths survived the build: " + ", ".join(survivors))

    # Audit 3: the live frontmatter must carry the production name.
    if f"name: {LIVE_SKILL_NAME}" not in skill_text.split("---", 2)[1]:
        return fail(f"live SKILL.md frontmatter must set name: {LIVE_SKILL_NAME}")

    for script in (out / "scripts").glob("*.py"):
        script.chmod(script.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)

    if args.self_test:
        result = subprocess.run([sys.executable, str(out / "scripts" / "package_self_test.py"), str(out)], capture_output=True, text=True)
        if result.returncode:
            print(result.stdout)
            print(result.stderr)
            return fail("live package self-test failed")

    # The release itself is the git commit/push that contains this rebuilt skill.
    print(json.dumps({
        "status": "PASS",
        "profile": "live_forecast_only",
        "skill_name": LIVE_SKILL_NAME,
        "output": str(out),
        "self_test": bool(args.self_test),
        "release_is_git_commit": True,
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
