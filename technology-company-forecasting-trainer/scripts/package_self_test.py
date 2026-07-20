#!/usr/bin/env python3
"""Profile-aware package self-test for the forecasting skill family.

Accepts either a package root (containing `skills/<name>/SKILL.md` and the
plugin manifests) or a bare skill root (containing `SKILL.md`). The profile is
detected from the SKILL.md frontmatter `name`:

  technology-company-forecasting-trainer -> trainer profile (full battery)
  technology-company-profit-forecasting  -> live profile (delivery battery,
                                            trainer material must be absent)

This lets the trainer package and the generated live package share one
self-test, so `build_live_release.py --self-test` can verify its own output.
"""
from __future__ import annotations

import csv
import json
import py_compile
import re
import subprocess
import sys
import tempfile
import zipfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

TRAINER_NAME = "technology-company-forecasting-trainer"
LIVE_NAME = "technology-company-profit-forecasting"
NAME_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")


def fail(msg: str) -> None:
    print("FAIL:", msg)
    raise SystemExit(2)


def run(cmd: list[str]) -> None:
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode:
        print(result.stdout)
        print(result.stderr)
        fail("command failed: " + " ".join(cmd))


def parse_frontmatter(skill_md: Path) -> dict[str, str]:
    text = skill_md.read_text(encoding="utf-8")
    if not text.startswith("---\n"):
        fail("SKILL.md missing YAML frontmatter")
    front = text.split("---", 2)[1]
    fields: dict[str, str] = {}
    for key in ("name", "description"):
        match = re.search(rf"^{key}:\s*(.+)$", front, re.M)
        if not match:
            fail(f"SKILL.md frontmatter missing {key}")
        fields[key] = match.group(1).strip()
    return fields


def resolve_skill(root: Path) -> tuple[Path, Path | None]:
    """Return (skill_dir, package_root_or_None)."""
    if (root / "SKILL.md").exists():
        return root, None
    candidates = sorted(root.glob("skills/*/SKILL.md"))
    if len(candidates) != 1:
        fail(f"expected exactly one skills/*/SKILL.md under {root}, found {len(candidates)}")
    return candidates[0].parent, root


LIVE_REQUIRED = [
    "SKILL.md",
    "agents/openai.yaml",
    "evals/trigger_prompts.jsonl",
    "references/codex-parity-execution.md",
    "references/full-company-delivery-contract.md",
    "references/gold-standard-example.md",
    "references/core-source-and-evidence.md",
    "references/research-completeness-and-company-quality.md",
    "references/forward-evidence-and-signal-validation.md",
    "references/core-forecast-workflow.md",
    "references/core-output-and-valuation.md",
    "references/mechanism-router.md",
    "references/mode-router-and-time-boundary.md",
    "references/module-unit-volume-price-cost.md",
    "references/module-capacity-utilization-yield.md",
    "references/module-orders-backlog-recognition.md",
    "references/module-platform-usage-adoption.md",
    "references/module-recurring-contract-revenue.md",
    "references/module-subscriber-content-economics.md",
    "references/module-program-stage-conversion.md",
    "references/module-contracts-jv-capital.md",
    "references/module-perimeter-and-accounting.md",
    "references/module-discrete-accounting-events.md",
    "references/submodule-dta-valuation-allowance.md",
    "references/validated-coverage.md",
    "references/skill-compatibility.md",
    "references/lens-memory-storage.md",
    "references/lens-equipment-process-control.md",
    "references/lens-networking-optics-custom-silicon.md",
    "references/lens-foundry-packaging-materials.md",
    "references/lens-compute-platforms.md",
    "references/lens-cloud-infrastructure-platform.md",
    "references/lens-subscription-content-platform.md",
    "references/lens-enterprise-recurring-software.md",
    "scripts/scaffold_delivery.py",
    "scripts/validate_time_boundary.py",
    "scripts/validate_research_completeness.py",
    "scripts/validate_forward_evidence_workspace.py",
    "scripts/validate_delivery.py",
    "scripts/freeze_snapshot.py",
    "scripts/package_self_test.py",
    "assets/templates/run_manifest_template.json",
    "assets/templates/mode_config_template.json",
    "assets/templates/training_state_template.json",
    "assets/templates/source_manifest_template.json",
    "assets/templates/assumption_register_v2_template.csv",
    "assets/templates/forward_signal_card_template.csv",
    "assets/templates/historical_query_log_template.csv",
    "assets/templates/source_independence_map_template.csv",
    "assets/templates/research_coverage_matrix_template.csv",
    "assets/templates/company_quality_moat_template.csv",
    "assets/templates/technology_commercialization_template.csv",
    "assets/templates/product_customer_driver_template.csv",
    "assets/templates/material_assumption_support_template.csv",
    "assets/templates/method_reflection_template.md",
    "assets/templates/red_team_template.md",
    "assets/templates/final_report_outline.md",
    "assets/templates/forecast_snapshot_template.json",
    "assets/templates/delivery_quality_rubric.json",
    "assets/examples/generic_v80/Technology_Company_Forecasting_v8.0_Gold_Model_Template.xlsx",
    "assets/schemas/run_manifest.schema.json",
    "assets/schemas/source_record.schema.json",
    "assets/schemas/forecast_snapshot.schema.json",
]

LIVE_FORBIDDEN = [
    "tests",
    "evals/workflow_cases.jsonl",
    "evals/codex_parity_cases.jsonl",
    "assets/benchmarks",
    "assets/reports",
    "assets/examples/sandisk_v73",
    "assets/live_release",
    "references/historical-training-loop.md",
    "references/training-curriculum.md",
    "references/live-mode-release.md",
    "references/validated-benchmarks.md",
    "references/schemas.md",
    "references/companion-live-skill-contract.md",
    "scripts/scaffold_training_run.py",
    "scripts/freeze_training_forecast.py",
    "scripts/score_training_forecast.py",
    "scripts/score_mechanism_outcomes.py",
    "scripts/validate_method_reflection.py",
    "scripts/scaffold_case.py",
    "scripts/validate_case.py",
    "scripts/build_live_release.py",
    "scripts/run_backtest.py",
    "assets/templates/case_template.json",
    "assets/templates/forecast_error_taxonomy_template.csv",
    "assets/templates/training_actuals_template.json",
    "assets/templates/mechanism_outcome_predictions_template.json",
    "assets/templates/mechanism_outcome_actuals_template.json",
    "assets/templates/mechanism_outcome_score_contract_template.json",
]

TRAINER_REQUIRED = [
    "SKILL.md",
    "agents/openai.yaml",
    "references/companion-live-skill-contract.md",
    "references/codex-parity-execution.md",
    "references/full-company-delivery-contract.md",
    "references/gold-standard-example.md",
    "references/core-source-and-evidence.md",
    "references/forward-evidence-and-signal-validation.md",
    "references/core-forecast-workflow.md",
    "references/core-output-and-valuation.md",
    "references/research-completeness-and-company-quality.md",
    "references/mode-router-and-time-boundary.md",
    "references/historical-training-loop.md",
    "references/live-mode-release.md",
    "references/training-curriculum.md",
    "references/mechanism-router.md",
    "references/module-platform-usage-adoption.md",
    "references/module-discrete-accounting-events.md",
    "references/submodule-dta-valuation-allowance.md",
    "references/module-subscriber-content-economics.md",
    "references/lens-cloud-infrastructure-platform.md",
    "references/lens-subscription-content-platform.md",
    "references/lens-memory-storage.md",
    "references/lens-equipment-process-control.md",
    "references/lens-networking-optics-custom-silicon.md",
    "scripts/scaffold_delivery.py",
    "scripts/validate_research_completeness.py",
    "scripts/validate_delivery.py",
    "scripts/validate_time_boundary.py",
    "scripts/scaffold_training_run.py",
    "scripts/freeze_training_forecast.py",
    "scripts/score_training_forecast.py",
    "scripts/score_mechanism_outcomes.py",
    "scripts/validate_method_reflection.py",
    "scripts/build_live_release.py",
    "scripts/run_backtest.py",
    "scripts/run_equipment_backtest.py",
    "scripts/run_marvell_backtest.py",
    "scripts/run_aws_backtest.py",
    "scripts/run_netflix_backtest.py",
    "scripts/run_nvidia_backtest.py",
    "scripts/run_forward_evidence_backtest.py",
    "scripts/run_amd_intel_backtest.py",
    "scripts/validate_amd_intel_point_in_time.py",
    "scripts/validate_point_in_time_sources.py",
    "scripts/validate_forward_evidence_workspace.py",
    "scripts/regression_check.py",
    "scripts/scope_regression_check.py",
    "assets/live_release/SKILL.md",
    "assets/live_release/openai.yaml",
    "assets/live_release/trigger_prompts.jsonl",
    "assets/templates/run_manifest_template.json",
    "assets/templates/delivery_quality_rubric.json",
    "assets/templates/red_team_template.md",
    "assets/templates/research_coverage_matrix_template.csv",
    "assets/templates/company_quality_moat_template.csv",
    "assets/templates/technology_commercialization_template.csv",
    "assets/templates/product_customer_driver_template.csv",
    "assets/templates/material_assumption_support_template.csv",
    "assets/templates/method_reflection_template.md",
    "assets/templates/mode_config_template.json",
    "assets/templates/training_state_template.json",
    "assets/templates/training_actuals_template.json",
    "assets/templates/forecast_error_taxonomy_template.csv",
    "assets/templates/mechanism_outcome_predictions_template.json",
    "assets/templates/mechanism_outcome_actuals_template.json",
    "assets/templates/mechanism_outcome_score_contract_template.json",
    "assets/examples/sandisk_v73/Sandisk_SNDK_v7.3_五年财务模型.xlsx",
    "assets/examples/sandisk_v73/Sandisk_SNDK_v7.3_模型报告.md",
    "assets/examples/generic_v80/Technology_Company_Forecasting_v8.0_Gold_Model_Template.xlsx",
    "assets/examples/generic_v80/Technology_Company_Forecasting_v8.0_Training_Curriculum.xlsx",
    "assets/benchmarks/training_curriculum_v80.csv",
    "assets/benchmarks/legacy_v5_forecasts.csv",
    "assets/benchmarks/legacy_v6_regression.csv",
    "assets/benchmarks/forward_evidence_cases_v74.json",
    "assets/benchmarks/forward_evidence_signals_v74.csv",
    "assets/benchmarks/forward_evidence_query_log_v74.csv",
    "assets/benchmarks/forward_evidence_independence_map_v74.csv",
    "assets/benchmarks/amd_intel_cases_v75.json",
    "assets/benchmarks/amd_intel_source_ledger_v75.csv",
    "assets/benchmarks/amd_intel_signals_v75.csv",
    "assets/benchmarks/amd_intel_query_log_v75.csv",
    "assets/benchmarks/unified_validation_registry_v75.csv",
]

TRAINER_SKILL_NEEDLES = [
    "one common forecasting system",
    "mechanism",
    "human-required",
    "mandatory full-model execution contract",
    "validate_delivery.py --strict",
    "formula-driven",
    "red team",
    "forward evidence",
    "signalcard",
    "historical_train",
    "sandbox",
    "seal",
    "actuals",
    "right-reason",
    "swap fold",
    "git",
    "technology-company-profit-forecasting",
    "build_live_release.py",
]

TRAINER_PROMPT_NEEDLES = [
    "formula-driven xlsx", "strict delivery validator", "immutable snapshot",
    "forward-evidence signalcards", "historical_train", "sandbox", "seal",
    "actuals", "right-reason", "swap fold", "git",
]

LIVE_SKILL_NEEDLES = [
    "one common forecasting system",
    "mechanism",
    "human-required",
    "mandatory full-model execution contract",
    "validate_delivery.py --strict",
    "formula-driven",
    "red team",
    "forward evidence",
    "signalcard",
    "live_forecast",
    "audit_only",
    "market-implied",
    "immutable",
    "technology-company-forecasting-trainer",
]

LIVE_SKILL_ABSENT = ["historical_train", "pending_clean_holdout", "promote_stable"]

LIVE_PROMPT_NEEDLES = [
    "live_forecast", "run workspace", "formula-driven xlsx", "strict delivery validator",
    "immutable snapshot", "signalcards", "red team", "human-required",
]

LIVE_PROMPT_ABSENT = ["historical_train"]

SMOKE_SHEETS = [
    "Summary", "Sources", "Historical", "Quarterly_FY1", "Drivers_Assumptions",
    "Financials_PL", "Cash_Capital", "Scenarios", "Valuation", "Monitoring", "Run_Manifest",
]


def write_minimal_workbook(path: Path, sheet_names: list[str]) -> None:
    """Write a minimal xlsx zip whose xl/workbook.xml lists the given sheets."""
    ns = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
    rns = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
    sheets = "".join(
        f'<sheet name="{name}" sheetId="{i+1}" r:id="rId{i+1}"/>' for i, name in enumerate(sheet_names)
    )
    workbook = f'<?xml version="1.0" encoding="UTF-8" standalone="yes"?><workbook xmlns="{ns}" xmlns:r="{rns}"><sheets>{sheets}</sheets></workbook>'
    sheet_xml = f'<?xml version="1.0" encoding="UTF-8" standalone="yes"?><worksheet xmlns="{ns}"><sheetData/></worksheet>'
    rels = "".join(
        f'<Relationship Id="rId{i+1}" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet{i+1}.xml"/>'
        for i in range(len(sheet_names))
    )
    workbook_rels = f'<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">{rels}</Relationships>'
    overrides = "".join(
        f'<Override PartName="/xl/worksheets/sheet{i+1}.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>'
        for i in range(len(sheet_names))
    )
    content_types = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
        '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
        '<Default Extension="xml" ContentType="application/xml"/>'
        '<Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>'
        f"{overrides}</Types>"
    )
    root_rels = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/>'
        "</Relationships>"
    )
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("[Content_Types].xml", content_types)
        zf.writestr("_rels/.rels", root_rels)
        zf.writestr("xl/workbook.xml", workbook)
        zf.writestr("xl/_rels/workbook.xml.rels", workbook_rels)
        for i in range(len(sheet_names)):
            zf.writestr(f"xl/worksheets/sheet{i+1}.xml", sheet_xml)


def synthetic_report() -> str:
    filler = (
        "This synthetic self-test delivery exercises the validator chain only. "
        "It contains no company research and must never be presented as analysis. "
    )
    sections = [
        ("Information cutoff", "The information cutoff and price timestamp are frozen at the run as_of."),
        ("Conclusion", "Self-test conclusion placeholder with readiness disclosure."),
        ("Base forecast", "Base forecast placeholder rows spanning revenue, margin, and profit."),
        ("Drivers and customers", "Drivers placeholder: products, customers, units, ASP, mix, share."),
        ("Forward evidence and research synthesis", "Forward evidence placeholder: investor dialogue, independent research, technical papers, source independence clusters, rejected signals and falsification triggers."),
        ("Cash flow and capital", "Cash flow placeholder: working capital, capex, free cash flow."),
        ("Scenarios", "Scenario placeholder: Bear, Base, Bull and regime branches."),
        ("Valuation", "Valuation placeholder: multiples, DCF, normalized value."),
        ("Reverse implied expectations", "Reverse placeholder: market-implied growth and margin."),
        ("Monitoring and triggers", "Monitoring placeholder: upgrade and kill triggers."),
        ("Limitations", "Limitation placeholder: human-required items and confidence caps."),
        ("买入纪律 (buy price)", "Recommended buy price placeholder with margin of safety logic."),
        ("一致性检查 (arithmetic)", "Arithmetic consistency check placeholder: implied tax rate, segment sums, EPS x shares."),
        ("核心变量 (thesis carriers)", "Thesis carriers placeholder: the 1-3 driver quantities that carry the call."),
        ("隐含指标 (implied diagnostics)", "Implied diagnostics placeholder: implied yoy, incremental margin flow-through, implied share."),
        ("线下项筛查 (below the line)", "Tax rate and valuation allowance reviewed; interest and FX modeled; no impairment or restructuring; share count and buyback dilution stated."),
    ]
    body = ["# Self-test delivery report", ""]
    for title, text in sections:
        body.append(f"## {title}")
        body.append("")
        body.append(text + " " + filler * 4)
        body.append("")
    return "\n".join(body)


def delivery_smoke_test(skill: Path, profile: str, td: Path) -> None:
    workspace = td / "delivery"
    run([sys.executable, str(skill / "scripts/scaffold_delivery.py"), "--workspace", str(workspace), "--entity", "TEST", "--security", "TEST", "--as-of", "2026-07-18"])
    manifest = json.loads((workspace / "run_manifest.json").read_text(encoding="utf-8"))
    manifest["fiscal_calendar"] = "calendar year"
    manifest["research_completeness_required"] = False
    manifest["forward_evidence_min_signals"] = 3  # smoke exercises plumbing, not research policy
    manifest["workbook_formula_min"] = 0  # synthetic/legacy example workbooks carry no formulas
    manifest["outputs_canonical_relaxed"] = True  # smoke snapshot keeps template nulls
    manifest["driver_tree_relaxed"] = True  # smoke exercises plumbing, not modeling doctrine
    manifest["interval_floor_relaxed"] = True  # smoke snapshot carries template nulls
    manifest["workbook_checks_relaxed"] = True  # legacy example workbook predates Check-row doctrine
    manifest["quarterly_spine_relaxed"] = True
    manifest["selected_mechanisms"] = ["unit-volume-price-cost"]
    manifest["phase_status"] = {key: "complete" for key in manifest["phase_status"]}
    (workspace / "run_manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    src = json.loads((workspace / "source_manifest.json").read_text(encoding="utf-8"))
    src["sources"] = [
        {
            "source_id": f"SRC{i}",
            "source_type": "filing" if i == 0 else ("earnings" if i == 1 else "official-product"),
            "publisher": "Example Corp",
            "published_at": f"2026-0{min(i+1,6)}-01T00:00:00Z",
            "retrieved_at": "2026-07-18T00:00:00Z",
            "period_scope": "FY2026",
            "evidence_tier": "E0" if i == 0 else "E1",
            "content_hash": f"unhashed:smoke-fixture-{i}",
            "location": f"https://example.com/{i}",
            "claim_or_fact": "official fact",
            "allowed_use": "base anchor",
            "limitations": "",
        }
        for i in range(6)
    ]
    (workspace / "source_manifest.json").write_text(json.dumps(src, indent=2), encoding="utf-8")
    with (workspace / "assumption_register.csv").open("a", encoding="utf-8") as handle:
        handle.write("A1,TEST,Total,unit-volume-price-cost,revenue,FY2027,base,10,USD bn,E1,SRC1,medium,TEST,,8,next earnings,analyst,\n")
    sig = [
        ["S1", "TEST", "SIG1", "Example Corp", "2026-04-01", "official-dialogue", "E1", "state_signal", "C1", "2", "2", "2", "2", "1", "1", "2", "0-1y", "base_driver", "demand", "raise usage", "https://example.com/s1", "incentive reviewed"],
        ["S2", "TEST", "SIG2", "Independent Research", "2026-05-01", "industry-research", "E3", "timing_signal", "C2", "2", "2", "2", "2", "0", "-1", "2", "0-1y", "base_driver", "inventory", "lower ASP", "https://example.com/s2", "method recorded"],
        ["S3", "TEST", "SIG3", "Paper", "2026-03-01", "technical-paper-standard", "E2", "failure_boundary", "C3", "2", "2", "1", "2", "0", "1", "1", "2-5y", "scenario_probability", "FY+2 unit ASP", "bounds ASP uplift", "https://example.com/s3", "not commercial"],
        ["S4", "TEST", "SIG4", "JEDEC", "2026-02-01", "technical-paper-standard", "E2", "feasibility_bound", "C3", "2", "2", "2", "2", "0", "1", "2", "2-5y", "timing_signal", "FY+2 shipments", "ramp gated by ratification", "https://example.com/s4", "standard timing"],
    ]
    with (workspace / "forward_signal_cards.csv").open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f)
        w.writerow(["signal_id", "case_id", "source_id", "publisher", "published_at", "source_family", "evidence_tier", "evidence_role", "independence_cluster", "method_transparency", "specificity", "causal_proximity", "falsifiability", "incentive_bias", "direction", "strength", "horizon", "allowed_use", "model_driver", "model_impact", "source_url", "limitations"])
        w.writerows(sig)
    with (workspace / "historical_query_log.csv").open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f)
        w.writerow(["query_id", "case_id", "searched_at", "cutoff", "query_text", "domains", "result_source_ids", "future_outcome_terms_used", "reviewer", "notes"])
        lane_queries = [
            ("Q1", "TEST 10-K annual report SEC EDGAR filing", "sec.gov"),
            ("Q2", "TEST earnings call transcript investor day management guidance", "ir.example.com"),
            ("Q3", "TEST supplier customer value chain cross-company commentary", "example.com"),
            ("Q4", "TrendForce IDC industry shipment data", "trendforce.com"),
            ("Q5", "sell-side broker research report analyst note", "example.com"),
            ("Q6", "expert network channel check supply chain", "example.com"),
            ("Q7", "arXiv IEEE JEDEC standard patent paper roadmap", "arxiv.org"),
        ]
        for qid, qtext, doms in lane_queries:
            w.writerow([qid, "TEST", "2026-07-18T12:00:00Z", "2026-07-18T23:59:59Z", qtext, doms, "SIG1", "false", "reviewer", "point-in-time"])
    with (workspace / "source_independence_map.csv").open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f)
        w.writerow(["cluster_id", "original_source_id", "derived_source_id", "relationship", "independence_weight", "notes"])
        for i in range(3):
            w.writerow([f"C{i+1}", f"SIG{i+1}", "", "original", 1.0, "independent source chain"])
    (workspace / "red_team.md").write_text(
        "# Red-team review\n\n"
        "| ID | Severity | Area | Finding | Evidence | Model impact | Required action | Status |\n"
        "|---|---|---|---|---|---|---|---|\n"
        "| RT-001 | P1 | double counting | Double-count capex and COGS test | SRC0 | FCF | reconcile | closed |\n"
        "| RT-002 | P1 | valuation | Normalization and terminal valuation challenge | SRC0 | value | stress | closed |\n"
        "| RT-003 | P1 | demand | Base demand unsupported | SRC1 | revenue | cap share | closed |\n"
        "| RT-004 | P1 | supply | Capacity constraint omitted | SRC2 | revenue | add supply | closed |\n"
        "| RT-005 | P1 | accounting | GAAP cash bridge incomplete | SRC0 | profit | bridge | closed |\n"
        "| RT-006 | P1 | source independence | Repeated reports may share one original source cluster | SIG1/SIG2 | Base | map source chains | closed |\n",
        encoding="utf-8",
    )
    if profile == "trainer":
        report_text = (skill / "assets/examples/sandisk_v73/Sandisk_SNDK_v7.3_模型报告.md").read_text(encoding="utf-8") + "\n\n## Forward evidence and research synthesis\nInvestor dialogue, independent research, technical papers, source independence clusters, rejected signals and falsification triggers were reviewed.\n\n## 买入纪律\nRecommended buy price derives from the Bear fair value with a stated margin of safety.\n\n## 一致性检查\nArithmetic consistency check: implied tax rate, segment sums, EPS x shares reconcile.\n\n## 核心变量\nThesis carriers named.\n\n## 隐含指标\nImplied yoy and incremental margin stated.\n"
        (workspace / "report.md").write_text(report_text, encoding="utf-8")
        (workspace / "model").mkdir(exist_ok=True)
        (workspace / "model/model.xlsx").write_bytes((skill / "assets/examples/sandisk_v73/Sandisk_SNDK_v7.3_五年财务模型.xlsx").read_bytes())
    else:
        (workspace / "report.md").write_text(synthetic_report(), encoding="utf-8")
        (workspace / "model").mkdir(exist_ok=True)
        write_minimal_workbook(workspace / "model/model.xlsx", SMOKE_SHEETS)
    snap = json.loads((workspace / "forecast_snapshot.json").read_text(encoding="utf-8"))
    snap["source_pack_hash"] = "sha256:test"
    snap["mechanism_weights"] = {"unit-volume-price-cost": 1.0}
    snap["scenario_probabilities"] = {"bear": 0.2, "base": 0.55, "bull": 0.2, "regime_break": 0.05}
    (workspace / "forecast_snapshot.json").write_text(json.dumps(snap, indent=2), encoding="utf-8")
    run([sys.executable, str(skill / "scripts/validate_delivery.py"), "--workspace", str(workspace), "--strict"])


def trainer_functional_battery(skill: Path, td: Path) -> None:
    cmds = [
        [sys.executable, str(skill / "scripts/validate_case.py"), str(skill / "assets/templates/case_template.json")],
        [sys.executable, str(skill / "scripts/run_backtest.py"), "--benchmark", str(skill / "assets/benchmarks/new_value_chain_benchmark.csv"), "--cases", str(skill / "assets/benchmarks/new_cases.json"), "--output-dir", str(td / "broad")],
        [sys.executable, str(skill / "scripts/regression_check.py"), "--baseline", str(skill / "assets/benchmarks/legacy_v5_forecasts.csv"), "--candidate", str(skill / "assets/benchmarks/legacy_v6_regression.csv")],
        [sys.executable, str(skill / "scripts/run_equipment_backtest.py"), "--benchmark", str(skill / "assets/benchmarks/equipment_benchmark_v62.csv"), "--cases", str(skill / "assets/benchmarks/equipment_cases_v62.json"), "--output-dir", str(td / "equipment")],
        [sys.executable, str(skill / "scripts/run_marvell_backtest.py"), "--benchmark", str(skill / "assets/benchmarks/marvell_benchmark_v63.csv"), "--cases", str(skill / "assets/benchmarks/marvell_cases_v63.json"), "--output-dir", str(td / "marvell")],
        [sys.executable, str(skill / "scripts/run_aws_backtest.py"), "--benchmark", str(skill / "assets/benchmarks/aws_benchmark_v71.csv"), "--cases", str(skill / "assets/benchmarks/aws_cases_v71.json"), "--output-dir", str(td / "aws")],
        [sys.executable, str(skill / "scripts/run_netflix_backtest.py"), "--benchmark", str(skill / "assets/benchmarks/netflix_benchmark_v72.csv"), "--cases", str(skill / "assets/benchmarks/netflix_cases_v72.json"), "--output-dir", str(td / "netflix"), "--name", "netflix"],
        [sys.executable, str(skill / "scripts/run_nvidia_backtest.py"), "--benchmark", str(skill / "assets/benchmarks/nvidia_benchmark_v72.csv"), "--cases", str(skill / "assets/benchmarks/nvidia_cases_v72.json"), "--output-dir", str(td / "nvidia"), "--name", "nvidia"],
        [sys.executable, str(skill / "scripts/validate_point_in_time_sources.py"), "--cases", str(skill / "assets/benchmarks/forward_evidence_cases_v74.json"), "--signals", str(skill / "assets/benchmarks/forward_evidence_signals_v74.csv"), "--query-log", str(skill / "assets/benchmarks/forward_evidence_query_log_v74.csv"), "--independence-map", str(skill / "assets/benchmarks/forward_evidence_independence_map_v74.csv")],
        [sys.executable, str(skill / "scripts/run_forward_evidence_backtest.py"), "--cases", str(skill / "assets/benchmarks/forward_evidence_cases_v74.json"), "--output-dir", str(td / "forward-evidence")],
        [sys.executable, str(skill / "scripts/validate_amd_intel_point_in_time.py"), "--cases", str(skill / "assets/benchmarks/amd_intel_cases_v75.json"), "--signals", str(skill / "assets/benchmarks/amd_intel_signals_v75.csv"), "--query-log", str(skill / "assets/benchmarks/amd_intel_query_log_v75.csv")],
        [sys.executable, str(skill / "scripts/run_amd_intel_backtest.py"), "--cases", str(skill / "assets/benchmarks/amd_intel_cases_v75.json"), "--output-dir", str(td / "amd-intel")],
        [sys.executable, str(skill / "scripts/scope_regression_check.py"), "--baseline", str(skill / "assets/benchmarks/sandisk_scope_baseline_v61.csv"), "--candidate", str(skill / "assets/benchmarks/sandisk_scope_candidate_v72.csv")],
    ]
    with ThreadPoolExecutor(max_workers=min(6, len(cmds))) as executor:
        futures = [executor.submit(run, cmd) for cmd in cmds]
        for future in futures:
            future.result()


def live_functional_battery(skill: Path, td: Path) -> None:
    for script in (skill / "scripts").glob("*.py"):
        py_compile.compile(str(script), doraise=True)
    live_ws = td / "live-mode"
    live_ws.mkdir()
    (live_ws / "mode_config.json").write_text(json.dumps({"run_mode": "live_forecast", "phase": "forecast"}), encoding="utf-8")
    run([sys.executable, str(skill / "scripts/validate_time_boundary.py"), "--workspace", str(live_ws), "--strict"])


def main() -> None:
    root = Path(sys.argv[1] if len(sys.argv) > 1 else ".").resolve()
    skill, package_root = resolve_skill(root)
    front = parse_frontmatter(skill / "SKILL.md")
    name = front["name"]

    if not NAME_RE.match(name) or len(name) > 64:
        fail(f"skill name violates the Agent Skills constraint (lowercase letters, digits, hyphens, <=64 chars): {name}")
    if not front["description"] or len(front["description"]) > 1024:
        fail(f"description must be non-empty and <=1024 characters (got {len(front['description'])})")

    if name == TRAINER_NAME:
        profile = "trainer"
    elif name == LIVE_NAME:
        profile = "live"
    else:
        fail(f"unrecognized skill name {name}; expected {TRAINER_NAME} or {LIVE_NAME}")

    if package_root is not None:
        if skill.name != name:
            fail(f"skill directory name {skill.name} must match frontmatter name {name}")
        for manifest in [package_root / ".codex-plugin/plugin.json", package_root / ".claude-plugin/plugin.json"]:
            if not manifest.exists():
                continue
            obj = json.loads(manifest.read_text(encoding="utf-8"))
            if obj.get("name") != name:
                fail(f"plugin manifest name must match skill name in {manifest}")
            if not obj.get("version"):
                fail(f"missing version in {manifest}")

    required = TRAINER_REQUIRED if profile == "trainer" else LIVE_REQUIRED
    for rel in required:
        path = skill / rel
        if not path.exists() or (path.is_file() and path.stat().st_size == 0):
            fail(f"missing or empty {path}")

    if profile == "live":
        present = [rel for rel in LIVE_FORBIDDEN if (skill / rel).exists()]
        if present:
            fail("trainer-only material must not ship in the live skill: " + ", ".join(present))

    text = (skill / "SKILL.md").read_text(encoding="utf-8").lower()
    needles = TRAINER_SKILL_NEEDLES if profile == "trainer" else LIVE_SKILL_NEEDLES
    for needle in needles:
        if needle.lower() not in text:
            fail(f"SKILL.md missing required rule: {needle}")
    if profile == "live":
        for needle in LIVE_SKILL_ABSENT:
            if needle in text:
                fail(f"live SKILL.md must not contain trainer token: {needle}")

    prompt = (skill / "agents/openai.yaml").read_text(encoding="utf-8").lower()
    prompt_needles = TRAINER_PROMPT_NEEDLES if profile == "trainer" else LIVE_PROMPT_NEEDLES
    for needle in prompt_needles:
        if needle not in prompt:
            fail(f"openai default prompt missing {needle}")
    if profile == "live":
        for needle in LIVE_PROMPT_ABSENT:
            if needle in prompt:
                fail(f"live openai prompt must not contain trainer token: {needle}")

    with tempfile.TemporaryDirectory() as td_raw:
        td = Path(td_raw)
        if profile == "trainer":
            trainer_functional_battery(skill, td)
        else:
            live_functional_battery(skill, td)
        delivery_smoke_test(skill, profile, td)

    print(f"PASS: {profile} package self-test for {name}")


if __name__ == "__main__":
    main()
