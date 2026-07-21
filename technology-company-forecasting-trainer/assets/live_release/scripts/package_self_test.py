#!/usr/bin/env python3
"""Production package boundary and executable scaffold smoke test."""
from __future__ import annotations

import json
import py_compile
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path


def fail(message: str) -> None:
    raise SystemExit("FAIL: " + message)


def main() -> None:
    root = Path(sys.argv[1] if len(sys.argv) > 1 else ".").resolve()
    profile = json.loads((root / "assets" / "profile.json").read_text(encoding="utf-8"))
    if profile.get("profile") != "live":
        fail("runtime profile is not live")
    if "allowed_modes" in profile:
        fail("single-purpose production profile must not carry mode routing")
    scripts = profile.get("runtime_scripts")
    if (
        not isinstance(scripts, list)
        or not scripts
        or len(scripts) != len(set(scripts))
        or any(not isinstance(name, str) or not name.endswith(".py") for name in scripts)
    ):
        fail("runtime_scripts must be a unique non-empty Python file list")
    with tempfile.TemporaryDirectory() as compile_dir:
        compile_root = Path(compile_dir)
        for name in scripts:
            path = root / "scripts" / name
            if not path.is_file():
                fail(f"missing owned runtime {name}")
            py_compile.compile(
                str(path),
                cfile=str(compile_root / f"{Path(name).stem}.pyc"),
                doraise=True,
            )

    for required in (
        "SKILL.md",
        "assets/artifact_registry.json",
        "assets/method_system.json",
        "assets/templates/run_manifest_template.json",
        "assets/templates/forecast_snapshot_template.json",
    ):
        if not (root / required).is_file():
            fail(f"missing {required}")

    with tempfile.TemporaryDirectory() as td:
        workspace = Path(td) / "forecast"
        started = datetime.now(timezone.utc)
        result = subprocess.run(
            [
                sys.executable,
                str(root / "scripts" / "scaffold_delivery.py"),
                "--workspace",
                str(workspace),
                "--entity",
                "SELFTEST",
            ],
            capture_output=True,
            text=True,
        )
        if result.returncode:
            fail("scaffold failed: " + (result.stdout + result.stderr))
        manifest = json.loads(
            (workspace / "run_manifest.json").read_text(encoding="utf-8")
        )
        recorded = datetime.fromisoformat(str(manifest.get("as_of")).replace("Z", "+00:00"))
        if recorded < started:
            fail("scaffold did not record its current snapshot time")
        if "run_mode" in manifest or "baseline_skill_version" in manifest:
            fail("scaffold emitted obsolete mode or duplicate version state")
        if (workspace / "mode_config.json").exists():
            fail("scaffold emitted obsolete mode_config.json")

    print("PASS: live package self-test for technology-company-profit-forecasting")


if __name__ == "__main__":
    main()
