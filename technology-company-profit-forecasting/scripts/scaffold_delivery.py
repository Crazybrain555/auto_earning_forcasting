#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import datetime as dt
import json
import shutil
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser(description="Create a deterministic full-company forecast workspace.")
    parser.add_argument("--workspace", required=True)
    parser.add_argument("--entity", required=True)
    parser.add_argument("--security", default=None)
    parser.add_argument("--as-of", required=True, help="YYYY-MM-DD or ISO timestamp")
    parser.add_argument("--purpose", default="five-year operating model and valuation")
    parser.add_argument("--currency", default="USD")
    parser.add_argument("--accounting-basis", default="GAAP")
    parser.add_argument("--mode", choices=["historical_train","live_forecast","audit_only"], default="live_forecast")
    parser.add_argument("--rescaffold-delivered", action="store_true",
                        help="required to scaffold over a sealed/validated workspace; archives the old one first")
    args = parser.parse_args()

    script_dir = Path(__file__).resolve().parent
    skill_root = script_dir.parent
    templates = skill_root / "assets" / "templates"
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
    manifest["run_id"] = f"run://technology/{args.security or args.entity}/{args.as_of}/v1"
    manifest["entity"] = args.entity
    manifest["security"] = args.security or args.entity
    manifest["as_of"] = args.as_of if "T" in args.as_of else args.as_of + "T23:59:59Z"
    manifest["purpose"] = args.purpose
    manifest["currency"] = args.currency
    manifest["accounting_basis"] = args.accounting_basis
    manifest["run_mode"] = args.mode
    manifest["time_boundary_enforced"] = args.mode == "historical_train"
    manifest["baseline_skill_version"] = "3.0.0"
    (workspace / "run_manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


    mode_config = json.loads((templates / "mode_config_template.json").read_text(encoding="utf-8"))
    mode_config["run_mode"] = args.mode
    mode_config["phase"] = "forecast"
    mode_config["as_of"] = manifest["as_of"]
    mode_config["enforce_source_cutoff"] = args.mode == "historical_train"
    mode_config["actuals_retrieval_allowed"] = False
    mode_config["open_web_after_seal_for_actuals"] = args.mode == "historical_train"
    (workspace / "mode_config.json").write_text(json.dumps(mode_config, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    training_state = json.loads((templates / "training_state_template.json").read_text(encoding="utf-8"))
    training_state["case_id"] = f"{args.security or args.entity}@{args.as_of}"
    training_state["phase"] = "forecast"
    training_state["baseline_skill_version"] = "3.0.0"
    (workspace / "training_state.json").write_text(json.dumps(training_state, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    source_manifest = json.loads((templates / "source_manifest_template.json").read_text(encoding="utf-8"))
    source_manifest["entity"] = args.entity
    source_manifest["security"] = args.security or args.entity
    source_manifest["as_of"] = manifest["as_of"]
    source_manifest["sources"] = []
    (workspace / "source_manifest.json").write_text(json.dumps(source_manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    shutil.copy2(templates / "assumption_register_v2_template.csv", workspace / "assumption_register.csv")
    shutil.copy2(templates / "forward_signal_card_template.csv", workspace / "forward_signal_cards.csv")
    shutil.copy2(templates / "historical_query_log_template.csv", workspace / "historical_query_log.csv")
    shutil.copy2(templates / "source_independence_map_template.csv", workspace / "source_independence_map.csv")
    shutil.copy2(templates / "research_coverage_matrix_template.csv", workspace / "research_coverage_matrix.csv")
    shutil.copy2(templates / "company_quality_moat_template.csv", workspace / "company_quality_moat_register.csv")
    shutil.copy2(templates / "technology_commercialization_template.csv", workspace / "technology_commercialization_register.csv")
    shutil.copy2(templates / "product_customer_driver_template.csv", workspace / "product_customer_driver_schedule.csv")
    shutil.copy2(templates / "material_assumption_support_template.csv", workspace / "material_assumption_support.csv")
    shutil.copy2(templates / "red_team_template.md", workspace / "red_team.md")
    shutil.copy2(templates / "final_report_outline.md", workspace / "report.md")
    shutil.copy2(templates / "forecast_snapshot_template.json", workspace / "forecast_snapshot.json")
    shutil.copy2(templates / "delivery_quality_rubric.json", workspace / "delivery_quality_rubric.json")

    readme = f"""# Forecast run workspace\n\nEntity: {args.entity}\nSecurity: {args.security or args.entity}\nAs of: {manifest['as_of']}\nPurpose: {args.purpose}
Run mode: {args.mode}\n\nComplete the official Source Pack, forward SignalCards, research-coverage matrix, company-quality/moat register, technology-commercialization register, product/customer driver schedule, material-assumption support table, historical query log and source-independence map. Place the formula workbook at `model/model.xlsx`. Keep all manifests current, then run:\n\n```bash\npython3 {script_dir / 'validate_delivery.py'} --workspace {workspace} --strict\n```\n"""
    (workspace / "README.md").write_text(readme, encoding="utf-8")

    print(json.dumps({"workspace": str(workspace), "created": sorted(p.name for p in workspace.iterdir())}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
