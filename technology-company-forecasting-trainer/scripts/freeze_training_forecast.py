#!/usr/bin/env python3
"""Seal a training forecast BEFORE its actuals are retrieved.

Runs the three delivery validators, stamps the workspace state, then writes a
seal over every file except the seal-exempt subtrees (evaluation/,
actuals_vault/). After sealing, any modified, removed, or ADDED file outside
those subtrees makes verification fail (see _seal_core).
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _seal_core as core


def run(cmd):
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode:
        print(result.stdout + result.stderr)
        raise SystemExit(result.returncode)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--workspace", required=True)
    args = parser.parse_args()
    workspace = Path(args.workspace).resolve()
    scripts = Path(__file__).resolve().parent
    if (workspace / "forecast_seal.json").exists():
        raise SystemExit("forecast already sealed")

    run([sys.executable, str(scripts / "validate_time_boundary.py"), "--workspace", str(workspace), "--strict"])
    run([sys.executable, str(scripts / "validate_research_completeness.py"), "--workspace", str(workspace), "--strict"])
    run([sys.executable, str(scripts / "validate_delivery.py"), "--workspace", str(workspace), "--strict"])

    now = dt.datetime.now(dt.timezone.utc).isoformat()
    mode = json.loads((workspace / "mode_config.json").read_text(encoding="utf-8"))
    mode.update({"phase": "sealed", "actuals_retrieval_allowed": True})
    (workspace / "mode_config.json").write_text(json.dumps(mode, indent=2) + "\n", encoding="utf-8")
    state = json.loads((workspace / "training_state.json").read_text(encoding="utf-8"))
    state.update({"phase": "sealed", "forecast_sealed_at": now})
    (workspace / "training_state.json").write_text(json.dumps(state, indent=2) + "\n", encoding="utf-8")
    snap = json.loads((workspace / "forecast_snapshot.json").read_text(encoding="utf-8"))
    snap["forecast_sealed_before_actuals"] = True
    snap["run_mode"] = "historical_train"
    (workspace / "forecast_snapshot.json").write_text(json.dumps(snap, indent=2) + "\n", encoding="utf-8")

    try:
        seal = core.build_seal(workspace, sealed_at=now)
    except core.SealError as exc:
        raise SystemExit(f"seal failed: {exc}")
    (workspace / "forecast_seal.json").write_text(json.dumps(seal, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"status": seal["status"], "sealed_at": now,
                      "pack_hash": seal["pack_hash"], "files": len(seal["files"])}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
