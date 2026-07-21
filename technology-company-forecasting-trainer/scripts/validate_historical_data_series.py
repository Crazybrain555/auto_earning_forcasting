#!/usr/bin/env python3
"""Trainer overlay for point-in-time eligibility on numeric evidence."""
from __future__ import annotations

import argparse
import csv
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path


def _date(value: object) -> datetime:
    text = str(value or "").strip()
    if len(text) == 10:
        text += "T23:59:59Z"
    parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    return parsed.replace(tzinfo=timezone.utc) if parsed.tzinfo is None else parsed.astimezone(timezone.utc)


def _rows(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--register", required=True, type=Path)
    parser.add_argument("--sources", required=True, type=Path)
    parser.add_argument("--graph", required=True, type=Path)
    parser.add_argument("--manifest", required=True, type=Path)
    parser.add_argument("--independence-map", required=True, type=Path)
    parser.add_argument("--facts", type=Path)
    parser.add_argument("--strict", action="store_true")
    args = parser.parse_args()
    manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    errors: list[str] = []
    run_mode = str(manifest.get("run_mode") or "")
    if run_mode in {"historical_train", "sealed_historical"}:
        if manifest.get("time_boundary_enforced") is not True:
            errors.append("historical run cannot disable time_boundary_enforced")
        try:
            boundary = _date(manifest.get("as_of"))
        except Exception:
            boundary = None
            errors.append("run_manifest.as_of is invalid")
        sources = json.loads(args.sources.read_text(encoding="utf-8")).get("sources", [])
        for source in sources:
            if not isinstance(source, dict):
                continue
            source_id = str(source.get("source_id") or "UNKNOWN")
            for field in ("published_at", "version_at"):
                if not str(source.get(field) or "").strip():
                    continue
                try:
                    if boundary is not None and _date(source.get(field)) > boundary:
                        errors.append(f"source {source_id} {field} is after run_manifest.as_of")
                except Exception:
                    errors.append(f"source {source_id} has invalid {field}")
        for row in _rows(args.register):
            series_id = str(row.get("series_id") or "").strip()
            if not series_id or series_id.lower() in {"tbd", "replace"}:
                continue
            for field in ("published_at", "retrieved_at", "available_at", "vintage_at", "revision_at"):
                try:
                    if boundary is not None and _date(row.get(field)) > boundary:
                        errors.append(f"{series_id}: {field} is after run_manifest.as_of")
                except Exception:
                    errors.append(f"{series_id}: invalid {field}")
        if args.facts is not None:
            for row in _rows(args.facts):
                fact_id = str(row.get("fact_id") or "").strip()
                if not fact_id or fact_id.lower() in {"tbd", "replace"}:
                    continue
                for field in ("filed_at", "retrieved_at", "as_of_cutoff"):
                    try:
                        if boundary is not None and _date(row.get(field)) > boundary:
                            errors.append(f"financial fact {fact_id}: {field} is after run_manifest.as_of")
                    except Exception:
                        errors.append(f"financial fact {fact_id}: invalid {field}")
    command = [
        sys.executable,
        str(Path(__file__).resolve().parent / "validate_data_series.py"),
        "--register", str(args.register),
        "--sources", str(args.sources),
        "--graph", str(args.graph),
        "--manifest", str(args.manifest),
        "--independence-map", str(args.independence_map),
    ]
    if args.facts is not None:
        command.extend(["--facts", str(args.facts)])
    if args.strict:
        command.append("--strict")
    base = subprocess.run(command, capture_output=True, text=True)
    try:
        payload = json.loads(base.stdout)
        base_errors = payload.get("errors") if isinstance(payload, dict) else []
        if isinstance(base_errors, list):
            errors.extend(str(item) for item in base_errors)
    except Exception:
        if base.returncode:
            errors.append((base.stdout + base.stderr).strip() or "base validator failed")
    result = {"valid": not errors, "strict": args.strict, "errors": errors}
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if not errors else 2


if __name__ == "__main__":
    raise SystemExit(main())
