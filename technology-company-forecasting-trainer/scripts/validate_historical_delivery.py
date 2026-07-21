#!/usr/bin/env python3
"""Trainer-owned composition of time-sandbox and forecast validators."""
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--workspace", required=True)
    parser.add_argument("--strict", action="store_true")
    args = parser.parse_args()
    scripts = Path(__file__).resolve().parent
    boundary = subprocess.run(
        [
            sys.executable,
            str(scripts / "validate_time_boundary.py"),
            "--workspace",
            args.workspace,
            "--strict",
        ]
    )
    if boundary.returncode:
        return boundary.returncode
    command = [
        sys.executable,
        str(scripts / "validate_delivery.py"),
        "--workspace",
        args.workspace,
    ]
    if args.strict:
        command.append("--strict")
    return subprocess.run(command).returncode


if __name__ == "__main__":
    raise SystemExit(main())
