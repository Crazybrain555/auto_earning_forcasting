#!/usr/bin/env python3
"""Render provider-neutral systemd units for the Forecast Ops runner."""

from __future__ import annotations

import argparse
import re
from pathlib import Path


TEMPLATE_DIR = Path(__file__).resolve().parent / "systemd"
UNIT_TEMPLATES = (
    "forecast-ops-backend.service",
    "forecast-sites-bridge.service",
    "forecast-replica-backup.service",
    "forecast-replica-backup.timer",
)
SAFE_USER = re.compile(r"[a-z_][a-z0-9_-]{0,31}")


def _absolute(value: Path, label: str) -> Path:
    value = Path(value)
    if not value.is_absolute() or "\n" in str(value) or "\r" in str(value):
        raise ValueError(f"{label} must be a single-line absolute path")
    return value


def render_units(
    *,
    runner_root: Path,
    backend_env_file: Path,
    bridge_env_file: Path,
    output_dir: Path,
    runner_user: str = "forecastops",
) -> list[Path]:
    runner_root = _absolute(runner_root, "runner_root")
    backend_env_file = _absolute(backend_env_file, "backend_env_file")
    bridge_env_file = _absolute(bridge_env_file, "bridge_env_file")
    output_dir = _absolute(output_dir, "output_dir")
    if not SAFE_USER.fullmatch(runner_user):
        raise ValueError("runner_user is invalid")

    replacements = {
        "@RUNNER_ROOT@": str(runner_root),
        "@BACKEND_ENV_FILE@": str(backend_env_file),
        "@BRIDGE_ENV_FILE@": str(bridge_env_file),
        "@RUNNER_USER@": runner_user,
    }
    output_dir.mkdir(parents=True, exist_ok=True)
    rendered: list[Path] = []
    for unit_name in UNIT_TEMPLATES:
        source = (TEMPLATE_DIR / f"{unit_name}.in").read_text(encoding="utf-8")
        for marker, value in replacements.items():
            source = source.replace(marker, value)
        unresolved = re.findall(r"@[A-Z_]+@", source)
        if unresolved:
            raise ValueError(f"unresolved placeholders in {unit_name}: {unresolved}")
        destination = output_dir / unit_name
        destination.write_text(source, encoding="utf-8")
        rendered.append(destination)
    return rendered


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--runner-root", type=Path, required=True)
    parser.add_argument("--backend-env-file", type=Path, required=True)
    parser.add_argument("--bridge-env-file", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--runner-user", default="forecastops")
    args = parser.parse_args()
    for path in render_units(
        runner_root=args.runner_root,
        backend_env_file=args.backend_env_file,
        bridge_env_file=args.bridge_env_file,
        output_dir=args.output_dir,
        runner_user=args.runner_user,
    ):
        print(path)


if __name__ == "__main__":
    main()
