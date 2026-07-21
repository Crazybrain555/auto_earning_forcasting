#!/usr/bin/env python3
"""External watchdog for the Forecast Ops production loop.

Checks, from any operator machine, that:
  1. the hosted console's bridge heartbeat is fresh (the runner is alive),
  2. the hosted snapshot keeps refreshing (production data is not stale),
  3. the local pulled replica is recent enough to count as a backup.

Prints one line per problem, exits non-zero on failure, and can raise a
macOS notification. stdlib only, so launchd/cron can run it with the
system python3.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import subprocess
import sys
import urllib.request
from pathlib import Path


def _fetch_json(url: str, timeout: float) -> dict:
    request = urllib.request.Request(url, headers={"User-Agent": "forecast-watchdog/1.0"})
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8"))


def _age_seconds(value: str, now: dt.datetime) -> float:
    stamp = dt.datetime.fromisoformat(value.replace("Z", "+00:00"))
    return (now - stamp).total_seconds()


def check(
    site_url: str,
    replica_current: Path | None,
    bridge_max_age: float,
    snapshot_max_age: float,
    replica_max_age_hours: float,
) -> list[str]:
    issues: list[str] = []
    now = dt.datetime.now(dt.timezone.utc)
    base = site_url.rstrip("/")

    try:
        bridge = _fetch_json(f"{base}/api/bridge/status", timeout=30).get("bridge") or {}
        if not bridge.get("online"):
            issues.append("bridge is offline")
        else:
            age = _age_seconds(str(bridge.get("last_seen_at")), now)
            if age > bridge_max_age:
                issues.append(f"bridge heartbeat is {age:.0f}s old (limit {bridge_max_age:.0f}s)")
    except Exception as error:  # a watchdog reports, it never crashes
        issues.append(f"bridge status check failed: {error}")

    try:
        snapshot = _fetch_json(f"{base}/api/snapshot", timeout=60)
        age = _age_seconds(str(snapshot.get("generated_at")), now)
        if age > snapshot_max_age:
            issues.append(
                f"snapshot is {age / 60:.0f} min old (limit {snapshot_max_age / 60:.0f} min)"
            )
    except Exception as error:
        issues.append(f"snapshot check failed: {error}")

    if replica_current is not None:
        manifest = replica_current / "manifest.json"
        try:
            payload = json.loads(manifest.read_text(encoding="utf-8"))
            age_hours = _age_seconds(str(payload.get("created_at")), now) / 3600
            if age_hours > replica_max_age_hours:
                issues.append(
                    f"local replica is {age_hours:.0f}h old (limit {replica_max_age_hours:.0f}h)"
                )
        except Exception as error:
            issues.append(f"replica check failed ({manifest}): {error}")

    return issues


def notify(message: str) -> None:
    if sys.platform != "darwin":
        return
    text = message.replace("\\", "").replace('"', "'")
    script = f'display notification "{text}" with title "Forecast Ops watchdog"'
    subprocess.run(["osascript", "-e", script], check=False, capture_output=True)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--site-url", required=True, help="hosted console base URL")
    parser.add_argument("--replica-current", type=Path, default=None,
                        help="path to replica/current; omit to skip the replica check")
    parser.add_argument("--bridge-max-age", type=float, default=600.0)
    parser.add_argument("--snapshot-max-age", type=float, default=1800.0)
    parser.add_argument("--replica-max-age-hours", type=float, default=50.0)
    parser.add_argument("--notify", action="store_true",
                        help="raise a macOS notification on failure")
    args = parser.parse_args()

    issues = check(
        args.site_url,
        args.replica_current,
        args.bridge_max_age,
        args.snapshot_max_age,
        args.replica_max_age_hours,
    )
    stamp = dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    if not issues:
        print(f"{stamp} ok")
        return 0
    for issue in issues:
        print(f"{stamp} ALERT {issue}")
    if args.notify:
        notify("; ".join(issues))
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
