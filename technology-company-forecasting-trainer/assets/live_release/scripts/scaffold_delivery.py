#!/usr/bin/env python3
"""Create a current-evidence production forecast workspace."""
from __future__ import annotations

import argparse
import datetime as dt
import json
import shutil
import sys
from pathlib import Path


_SCRIPT_DIR = Path(__file__).resolve().parent
if str(_SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPT_DIR))

from artifact_registry import load_registry, resolve_active_paths, validate_registry
from runtime_context import skill_root_from_script


def _now() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat().replace("+00:00", "Z")


def main() -> int:
    skill_root = skill_root_from_script(__file__)
    parser = argparse.ArgumentParser(
        description="Create a current-evidence full-company forecast workspace."
    )
    parser.add_argument("--workspace", required=True)
    parser.add_argument("--entity", required=True)
    parser.add_argument("--security", default=None)
    parser.add_argument("--purpose", default="five-year operating model and valuation")
    parser.add_argument("--currency", default="USD")
    parser.add_argument(
        "--rescaffold-delivered",
        action="store_true",
        help="archive an existing delivery before creating a fresh workspace",
    )
    args = parser.parse_args()
    snapshot_at = _now()

    templates = skill_root / "assets" / "templates"
    registry = load_registry(skill_root / "assets" / "artifact_registry.json")
    problems = validate_registry(registry, skill_root=skill_root)
    if problems:
        raise SystemExit("invalid artifact registry: " + "; ".join(problems))
    method = json.loads(
        (skill_root / "assets" / "method_system.json").read_text(encoding="utf-8")
    )
    method_version = str(method.get("method_version") or "UNSET")

    workspace = Path(args.workspace).resolve()
    delivered = [
        name
        for name in ("forecast_seal.json", "delivery_validation.json")
        if (workspace / name).exists()
    ]
    if delivered:
        if not args.rescaffold_delivered:
            raise SystemExit(
                f"refusing to overwrite delivered workspace {workspace}; "
                "pass --rescaffold-delivered to archive it first"
            )
        archive = workspace.parent / (
            f"{workspace.name}.archived-"
            + dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        )
        workspace.rename(archive)
        print(f"archived previous delivery to {archive}")
    workspace.mkdir(parents=True, exist_ok=True)
    (workspace / "model").mkdir(exist_ok=True)

    manifest = json.loads(
        (templates / "run_manifest_template.json").read_text(encoding="utf-8")
    )
    identity = args.security or args.entity
    manifest.update(
        {
            "run_id": f"run://technology/{identity}/{snapshot_at}/v2",
            "entity": args.entity,
            "security": identity,
            "as_of": snapshot_at,
            "purpose": args.purpose,
            "currency": args.currency,
            "method_version": f"{method_version}+git:UNSET",
        }
    )
    for basis in (manifest.get("accounting_basis") or {}).get("bases", []):
        if isinstance(basis, dict):
            basis["presentation_currency"] = args.currency
    manifest.setdefault("materiality_routes", {})
    manifest["required_artifacts"] = resolve_active_paths(
        registry, manifest, profile="live"
    )
    (workspace / "run_manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )

    source_manifest = json.loads(
        (templates / "source_manifest_template.json").read_text(encoding="utf-8")
    )
    source_manifest.update(
        {"entity": args.entity, "security": identity, "as_of": snapshot_at, "sources": []}
    )
    (workspace / "source_manifest.json").write_text(
        json.dumps(source_manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )

    reserved = {
        "run_manifest.json",
        "source_manifest.json",
        "forecast_snapshot.json",
        "model_graph.json",
    }
    for artifact in registry.get("artifacts", []):
        if (
            not isinstance(artifact, dict)
            or artifact.get("scaffold") is not True
            or (
                "profiles" in artifact
                and "live" not in artifact.get("profiles", [])
            )
            or artifact.get("path") in reserved
        ):
            continue
        source = skill_root / str(artifact["template"])
        target = workspace / str(artifact["path"])
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)

    snapshot = json.loads(
        (templates / "forecast_snapshot_template.json").read_text(encoding="utf-8")
    )
    snapshot.update(
        {
            "forecast_id": f"fcst://technology/{identity}/{snapshot_at}/v2",
            "as_of": snapshot_at,
            "model_version": manifest["method_version"],
            "accounting_basis_id": (manifest.get("accounting_basis") or {}).get(
                "forecast_basis_id", "REPLACE"
            ),
        }
    )
    (workspace / "forecast_snapshot.json").write_text(
        json.dumps(snapshot, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )

    graph = json.loads((templates / "model_graph_template.json").read_text(encoding="utf-8"))
    graph["graph_id"] = f"graph://technology/{identity}/{snapshot_at}/v2"
    graph["as_of"] = snapshot_at
    (workspace / "model_graph.json").write_text(
        json.dumps(graph, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )

    (workspace / "README.md").write_text(
        "# Forecast run workspace\n\n"
        f"Entity: {args.entity}\nSecurity: {identity}\n"
        f"Workspace created at: {snapshot_at}\nPurpose: {args.purpose}\n"
        "Evidence remains open until the publication bundle is frozen.\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {"workspace": str(workspace), "created": sorted(p.name for p in workspace.iterdir())},
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
