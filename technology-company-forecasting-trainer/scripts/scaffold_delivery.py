#!/usr/bin/env python3
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

from runtime_context import skill_root_from_script
from training_runtime_policy import (
    allowed_modes,
    artifact_profile_for_mode,
    load_training_profile,
    require_allowed_mode,
)
from artifact_registry import load_registry, resolve_active_paths, validate_registry


def main() -> int:
    script_dir = Path(__file__).resolve().parent
    skill_root = skill_root_from_script(__file__)
    profile = load_training_profile(skill_root)
    mode_choices = allowed_modes(profile)
    parser = argparse.ArgumentParser(description="Create a coordinator forecast workspace.")
    parser.add_argument("--workspace", required=True)
    parser.add_argument("--entity", required=True)
    parser.add_argument("--security", default=None)
    parser.add_argument("--as-of", help="required only for historical_train")
    parser.add_argument("--purpose", default="five-year operating model and valuation")
    parser.add_argument("--currency", default="USD")
    parser.add_argument(
        "--mode",
        choices=mode_choices,
        default="live_forecast",
    )
    parser.add_argument("--rescaffold-delivered", action="store_true",
                        help="required to scaffold over a sealed/validated workspace; archives the old one first")
    args = parser.parse_args()
    run_mode = require_allowed_mode(profile, args.mode)
    if run_mode == "historical_train" and not args.as_of:
        raise SystemExit("historical_train requires --as-of")
    if args.as_of:
        snapshot_at = args.as_of if "T" in args.as_of else args.as_of + "T23:59:59Z"
    else:
        snapshot_at = dt.datetime.now(dt.timezone.utc).isoformat().replace("+00:00", "Z")

    templates = skill_root / "assets" / "templates"
    artifact_registry = load_registry(skill_root / "assets" / "artifact_registry.json")
    registry_problems = validate_registry(artifact_registry, skill_root=skill_root)
    if registry_problems:
        raise SystemExit("invalid artifact registry: " + "; ".join(registry_problems))
    method_system = json.loads((skill_root / "assets" / "method_system.json").read_text(encoding="utf-8"))
    method_version = str(method_system.get("method_version") or "UNSET")
    workspace = Path(args.workspace).resolve()
    # Never silently overwrite a delivered forecast: templates are copied over
    # the workspace, so re-scaffolding a sealed/validated case destroys its
    # snapshot, report and registers. Archive-and-recreate only on explicit flag.
    delivered = [name for name in ("forecast_seal.json", "delivery_validation.json")
                 if (workspace / name).exists()]
    if delivered:
        if not args.rescaffold_delivered:
            raise SystemExit(
                f"refusing to scaffold over {workspace} - it already holds a delivered forecast "
                f"({', '.join(delivered)}). Rerunning would overwrite its snapshot/report/registers "
                "with templates. Pass --rescaffold-delivered to archive the old workspace and start fresh.")
        stamp = dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        archive = workspace.parent / f"{workspace.name}.archived-{stamp}"
        workspace.rename(archive)
        print(f"archived previous delivery to {archive}")
    workspace.mkdir(parents=True, exist_ok=True)
    (workspace / "model").mkdir(exist_ok=True)

    manifest = json.loads((templates / "run_manifest_template.json").read_text(encoding="utf-8"))
    manifest["run_id"] = f"run://technology/{args.security or args.entity}/{snapshot_at}/v2"
    manifest["entity"] = args.entity
    manifest["security"] = args.security or args.entity
    manifest["as_of"] = snapshot_at
    manifest["purpose"] = args.purpose
    manifest["currency"] = args.currency
    for basis in (manifest.get("accounting_basis") or {}).get("bases", []):
        if isinstance(basis, dict):
            basis["presentation_currency"] = args.currency
    manifest["run_mode"] = run_mode
    if run_mode == "historical_train":
        manifest["time_boundary_enforced"] = True
    else:
        manifest.pop("time_boundary_enforced", None)
    manifest.setdefault("materiality_routes", {})
    selected_profile = artifact_profile_for_mode(run_mode)
    manifest["artifact_profile"] = selected_profile
    manifest["required_artifacts"] = resolve_active_paths(
        artifact_registry, manifest, profile=selected_profile
    )
    manifest["method_version"] = f"{method_version}+git:UNSET"
    manifest["baseline_skill_version"] = method_version
    (workspace / "run_manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


    mode_config = json.loads((templates / "mode_config_template.json").read_text(encoding="utf-8"))
    mode_config["run_mode"] = run_mode
    mode_config["phase"] = "forecast"
    mode_config["as_of"] = manifest["as_of"]
    if run_mode == "historical_train":
        mode_config["enforce_source_cutoff"] = True
        mode_config["actuals_retrieval_allowed"] = False
        mode_config["open_web_after_seal_for_actuals"] = True
        mode_config["unknown_date_policy"] = "quarantine"
        mode_config["post_cutoff_policy"] = "quarantine"
        mode_config["allowed_source_statuses"] = ["eligible_pre_cutoff"]
    else:
        for key in (
            "enforce_source_cutoff",
            "actuals_retrieval_allowed",
            "open_web_after_seal_for_actuals",
            "unknown_date_policy",
            "post_cutoff_policy",
            "allowed_source_statuses",
            "forbidden_query_terms",
        ):
            mode_config.pop(key, None)
        mode_config["evidence_acceptance"] = "current_until_bundle_freeze"
    (workspace / "mode_config.json").write_text(json.dumps(mode_config, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    if run_mode == "historical_train":
        training_state = json.loads((templates / "training_state_template.json").read_text(encoding="utf-8"))
        training_state["case_id"] = f"{args.security or args.entity}@{snapshot_at}"
        training_state["phase"] = "forecast"
        training_state["baseline_skill_version"] = method_version
        (workspace / "training_state.json").write_text(json.dumps(training_state, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    source_manifest = json.loads((templates / "source_manifest_template.json").read_text(encoding="utf-8"))
    source_manifest["entity"] = args.entity
    source_manifest["security"] = args.security or args.entity
    source_manifest["as_of"] = manifest["as_of"]
    source_manifest["sources"] = []
    (workspace / "source_manifest.json").write_text(json.dumps(source_manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    # Registry is the one artifact inventory.  Conditional templates are made
    # available without making their routes active or requiring empty shells.
    special_paths = {
        "run_manifest.json", "mode_config.json", "source_manifest.json",
        "training_state.json", "forecast_snapshot.json", "model_graph.json",
    }
    for artifact in artifact_registry.get("artifacts", []):
        if (
            not isinstance(artifact, dict)
            or artifact.get("scaffold") is not True
            or (
                "profiles" in artifact
                and selected_profile not in artifact.get("profiles", [])
            )
            or artifact.get("path") in special_paths
        ):
            continue
        source = skill_root / str(artifact["template"])
        target = workspace / str(artifact["path"])
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)
    snapshot = json.loads((templates / "forecast_snapshot_template.json").read_text(encoding="utf-8"))
    snapshot["forecast_id"] = f"fcst://technology/{args.security or args.entity}/{snapshot_at}/v2"
    snapshot["as_of"] = manifest["as_of"]
    snapshot["model_version"] = manifest["method_version"]
    snapshot["accounting_basis_id"] = (manifest.get("accounting_basis") or {}).get(
        "forecast_basis_id", "REPLACE"
    )
    snapshot["run_mode"] = run_mode
    (workspace / "forecast_snapshot.json").write_text(json.dumps(snapshot, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    graph = json.loads((templates / "model_graph_template.json").read_text(encoding="utf-8"))
    graph["graph_id"] = f"graph://technology/{args.security or args.entity}/{snapshot_at}/v2"
    graph["as_of"] = manifest["as_of"]
    (workspace / "model_graph.json").write_text(json.dumps(graph, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    readme = f"""# Forecast run workspace\n\nEntity: {args.entity}\nSecurity: {args.security or args.entity}\nSnapshot recorded at: {manifest['as_of']}\nPurpose: {args.purpose}
Run mode: {run_mode}\n\nFollow `references/research-sop.md`: author evidence, facts, assumptions and the smallest executable causal graph once; generate or reconcile downstream schedules from stable IDs. Place the formula workbook at `model/model.xlsx`. Keep the manifest stages current, then run:\n\n```bash\npython3 {script_dir / 'validate_delivery.py'} --workspace {workspace} --strict\n```\n"""
    (workspace / "README.md").write_text(readme, encoding="utf-8")

    print(json.dumps({"workspace": str(workspace), "created": sorted(p.name for p in workspace.iterdir())}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
