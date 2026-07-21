#!/usr/bin/env python3
"""Deterministically build the live coordinator, specialists and contracts."""
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


def _fail(message: str, detail: str = "") -> int:
    print(json.dumps({"status": "FAIL", "error": message, "detail": detail}, ensure_ascii=False, indent=2))
    return 2


def _copy_tree(source: Path, destination: Path) -> None:
    shutil.copytree(
        source,
        destination,
        ignore=shutil.ignore_patterns("__pycache__", "*.pyc", "*.pyo", ".DS_Store", ".pytest_cache"),
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Build the five-skill forecasting system")
    parser.add_argument("--trainer-skill-root", required=True)
    parser.add_argument("--output-parent", required=True)
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("--promote", action="store_true")
    parser.add_argument("--promotion-evidence")
    args = parser.parse_args()

    trainer = Path(args.trainer_skill_root).resolve()
    output_parent = Path(args.output_parent).resolve()
    source_root = trainer / "assets" / "skill_system"
    manifest_path = source_root / "manifest.json"
    if not manifest_path.is_file():
        return _fail("missing skill-system manifest", str(manifest_path))
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return _fail("invalid skill-system manifest", str(exc))
    capabilities = manifest.get("capabilities")
    if not isinstance(capabilities, dict) or len(capabilities) != 3:
        return _fail("manifest must define exactly three capabilities")

    output_parent.mkdir(parents=True, exist_ok=True)
    live_name = manifest.get("coordinators", {}).get("live")
    if not isinstance(live_name, str) or not live_name:
        return _fail("manifest live coordinator is invalid")
    generated_names = [live_name, *capabilities.keys(), "forecasting-system-contracts"]
    if trainer.name in generated_names:
        return _fail("generated output overlaps the trainer")

    with tempfile.TemporaryDirectory(prefix=".forecast-skill-build-", dir=output_parent.parent) as td:
        stage = Path(td) / "system"
        stage.mkdir()
        live_command = [
            sys.executable,
            str(trainer / "scripts" / "build_live_release.py"),
            "--trainer-skill-root",
            str(trainer),
            "--output-root",
            str(stage / live_name),
        ]
        if args.self_test:
            live_command.append("--self-test")
        if args.promote:
            live_command.append("--promote")
        if args.promotion_evidence:
            live_command.extend(["--promotion-evidence", args.promotion_evidence])
        result = subprocess.run(live_command, capture_output=True, text=True)
        if result.returncode:
            return _fail("live coordinator build failed", (result.stdout + result.stderr)[-12000:])

        for name in capabilities:
            source = source_root / "skills" / name
            if not source.is_dir():
                return _fail("missing capability source", str(source))
            _copy_tree(source, stage / name)
        _copy_tree(source_root / "contracts", stage / "forecasting-system-contracts")

        validator = subprocess.run(
            [
                sys.executable,
                str(trainer / "scripts" / "validate_skill_system.py"),
                "--system-root",
                str(stage),
                "--trainer-root",
                str(trainer),
            ],
            capture_output=True,
            text=True,
        )
        if validator.returncode:
            return _fail("skill-system validation failed", (validator.stdout + validator.stderr)[-12000:])

        # Replace only the allowlisted generated components after the staged
        # system has passed.  The trainer and unrelated repository paths are
        # never deletion targets.
        for name in generated_names:
            destination = output_parent / name
            if destination.exists():
                if not destination.is_dir():
                    return _fail("generated destination is not a directory", str(destination))
                shutil.rmtree(destination)
            shutil.move(str(stage / name), str(destination))

    print(json.dumps({
        "status": "PASS",
        "system_id": manifest.get("system_id"),
        "output_parent": str(output_parent),
        "live_coordinator": live_name,
        "capability_count": len(capabilities),
        "release_eligible": bool(args.promote),
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
