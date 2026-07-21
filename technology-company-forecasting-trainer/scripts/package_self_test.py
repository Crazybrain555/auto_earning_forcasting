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
import hashlib
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
PATH_MENTION_RE = re.compile(r"`((?:references|scripts|assets)/[A-Za-z0-9_./-]+)`")

# Open-ended record templates may intentionally contain zero authored rows.
# Treating every required path as content-bearing encouraged whitespace
# sentinels, which are neither valid records nor useful documentation.
INTENTIONALLY_EMPTY_REQUIRED_FILES = {
    "assets/templates/technical_evidence_records_template.jsonl",
}


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
    "references/data-quality-and-triangulation.md",
    "references/earnings-power-and-mean-reversion.md",
    "references/internal-intangible-investment.md",
    "references/research-sop.md",
    "references/analysis-kernel.md",
    "references/causal-modeling-kernel.md",
    "references/equation-primitives.md",
    "references/industry-economics-and-cycle.md",
    "references/technology-commercialization-and-ip.md",
    "references/valuation-and-market-expectations.md",
    "references/publication-and-monitoring.md",
    "references/research-completeness-and-company-quality.md",
    "references/forward-evidence-and-signal-validation.md",
    "references/core-forecast-workflow.md",
    "references/core-output-and-valuation.md",
    "references/mechanism-router.md",
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
    "assets/templates/run_manifest_template.json",
    "assets/templates/source_manifest_template.json",
    "assets/templates/assumption_register_v2_template.csv",
    "assets/templates/forward_signal_card_template.csv",
    "assets/templates/source_independence_map_template.csv",
    "assets/templates/research_coverage_matrix_template.csv",
    "assets/templates/company_quality_moat_template.csv",
    "assets/templates/technology_commercialization_template.csv",
    "assets/templates/technical_evidence_records_template.jsonl",
    "assets/templates/product_customer_driver_template.csv",
    "assets/templates/material_assumption_support_template.csv",
    "assets/templates/model_graph_template.json",
    "assets/templates/claim_ledger_template.jsonl",
    "assets/templates/scenario_set_template.json",
    "assets/templates/model_checks_template.json",
    "assets/templates/driver_monitoring_template.csv",
    "assets/templates/industry_profit_pool_template.csv",
    "assets/templates/operating_cycle_template.csv",
    "assets/templates/historical_segment_bridge_template.csv",
    "assets/templates/earnings_power_bridge_template.csv",
    "assets/templates/data_series_register_template.csv",
    "assets/templates/financial_fact_ledger_template.csv",
    "assets/templates/internal_intangible_investment_template.json",
    "assets/templates/red_team_template.md",
    "assets/templates/final_report_outline.md",
    "assets/templates/forecast_snapshot_template.json",
    "assets/templates/delivery_quality_rubric.json",
    "assets/templates/research_quality_review_template.json",
    "assets/artifact_registry.json",
    "assets/method_system.json",
    "assets/profile.json",
    "assets/examples/generic_v80/Technology_Company_Forecasting_v8.0_Gold_Model_Template.xlsx",
    "assets/schemas/run_manifest.schema.json",
    "assets/schemas/source_record.schema.json",
    "assets/schemas/forecast_snapshot.schema.json",
    "assets/schemas/forecast_seal.schema.json",
    "assets/schemas/model_graph.schema.json",
    "assets/schemas/claim_record.schema.json",
    "assets/schemas/scenario_set.schema.json",
    "assets/schemas/model_checks.schema.json",
    "assets/schemas/technical_evidence_record.schema.json",
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
    "scripts/_actuals_contract.py",
    "scripts/score_training_forecast.py",
    "scripts/score_mechanism_outcomes.py",
    "scripts/validate_method_reflection.py",
    "scripts/validate_promotion_evidence.py",
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
    "assets/templates/method_reflection_template.md",
    "assets/templates/training_state_template.json",
    "assets/templates/mode_config_template.json",
]

TRAINER_REQUIRED = [
    "SKILL.md",
    "pytest.ini",
    "agents/openai.yaml",
    "references/companion-live-skill-contract.md",
    "references/codex-parity-execution.md",
    "references/full-company-delivery-contract.md",
    "references/gold-standard-example.md",
    "references/core-source-and-evidence.md",
    "references/data-quality-and-triangulation.md",
    "references/earnings-power-and-mean-reversion.md",
    "references/internal-intangible-investment.md",
    "references/research-sop.md",
    "references/analysis-kernel.md",
    "references/causal-modeling-kernel.md",
    "references/equation-primitives.md",
    "references/industry-economics-and-cycle.md",
    "references/technology-commercialization-and-ip.md",
    "references/valuation-and-market-expectations.md",
    "references/multi-skill-system-architecture.md",
    "references/methodological-foundations.md",
    "assets/training_method_overlay.json",
    "references/forward-evidence-and-signal-validation.md",
    "references/core-forecast-workflow.md",
    "references/core-output-and-valuation.md",
    "references/research-completeness-and-company-quality.md",
    "references/historical-training-loop.md",
    "references/live-mode-release.md",
    "references/training-curriculum.md",
    "references/mechanism-router.md",
    "references/module-platform-usage-adoption.md",
    "references/module-discrete-accounting-events.md",
    "references/submodule-dta-valuation-allowance.md",
    "references/module-subscriber-content-economics.md",
    "scripts/scaffold_training_run.py",
    "scripts/freeze_training_forecast.py",
    "scripts/score_training_forecast.py",
    "scripts/_actuals_contract.py",
    "scripts/score_mechanism_outcomes.py",
    "scripts/validate_method_reflection.py",
    "scripts/validate_promotion_evidence.py",
    "scripts/project_historical_capability_view.py",
    "scripts/training_runtime_policy.py",
    "scripts/build_live_release.py",
    "scripts/build_skill_system.py",
    "scripts/validate_skill_system.py",
    "scripts/run_backtest.py",
    "scripts/legacy_backtest_diagnostics.py",
    "scripts/run_equipment_backtest.py",
    "scripts/run_marvell_backtest.py",
    "scripts/run_aws_backtest.py",
    "scripts/run_netflix_backtest.py",
    "scripts/run_nvidia_backtest.py",
    "scripts/run_forward_evidence_backtest.py",
    "scripts/run_amd_intel_backtest.py",
    "scripts/validate_amd_intel_point_in_time.py",
    "scripts/validate_point_in_time_sources.py",
    "scripts/validate_time_boundary.py",
    "assets/method_system.json",
    "assets/profile.json",
    "assets/runtime_ownership.json",
    "scripts/regression_check.py",
    "scripts/scope_regression_check.py",
    "assets/artifact_registry.json",
    "assets/skill_system/manifest.json",
    "assets/skill_system/contracts/protocol_manifest.json",
    "assets/skill_system/contracts/schemas/capability_handoff.schema.json",
    "assets/skill_system/skills/company-evidence-research/SKILL.md",
    "assets/skill_system/skills/company-operating-modeling/SKILL.md",
    "assets/skill_system/skills/company-financial-forecasting/SKILL.md",
    "assets/live_release/SKILL.md",
    "assets/live_release/openai.yaml",
    "assets/live_release/trigger_prompts.jsonl",
    "assets/templates/run_manifest_template.json",
    "assets/templates/delivery_quality_rubric.json",
    "assets/templates/red_team_template.md",
    "assets/templates/research_coverage_matrix_template.csv",
    "assets/templates/company_quality_moat_template.csv",
    "assets/templates/technology_commercialization_template.csv",
    "assets/templates/technical_evidence_records_template.jsonl",
    "assets/templates/product_customer_driver_template.csv",
    "assets/templates/material_assumption_support_template.csv",
    "assets/templates/model_graph_template.json",
    "assets/templates/claim_ledger_template.jsonl",
    "assets/templates/scenario_set_template.json",
    "assets/templates/model_checks_template.json",
    "assets/templates/driver_monitoring_template.csv",
    "assets/templates/industry_profit_pool_template.csv",
    "assets/templates/operating_cycle_template.csv",
    "assets/templates/historical_segment_bridge_template.csv",
    "assets/templates/earnings_power_bridge_template.csv",
    "assets/templates/data_series_register_template.csv",
    "assets/templates/financial_fact_ledger_template.csv",
    "assets/templates/internal_intangible_investment_template.json",
    "assets/templates/research_quality_review_template.json",
    "assets/templates/method_reflection_template.md",
    "assets/templates/mode_config_template.json",
    "assets/templates/training_state_template.json",
    "assets/templates/training_actuals_template.json",
    "assets/templates/historical_query_log_template.csv",
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
    "assets/schemas/technical_evidence_record.schema.json",
    "assets/schemas/forecast_seal.schema.json",
]

LIVE_SKILL_ABSENT = ["historical_train", "pending_clean_holdout", "promote_stable"]

LIVE_PROMPT_ABSENT = ["historical_train"]

SMOKE_SHEETS = [
    "Summary", "Sources", "Historical", "Quarterly_FY1", "Drivers_Assumptions",
    "Financials_PL", "Cash_Capital", "Scenarios", "Scenario_PnL", "Valuation", "Monitoring", "Run_Manifest",
]


def write_minimal_workbook(path: Path, sheet_names: list[str]) -> None:
    """Write a minimal xlsx zip whose xl/workbook.xml lists the given sheets."""
    ns = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
    rns = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
    sheets = "".join(
        f'<sheet name="{name}" sheetId="{i+1}" r:id="rId{i+1}"/>' for i, name in enumerate(sheet_names)
    )
    workbook = f'<?xml version="1.0" encoding="UTF-8" standalone="yes"?><workbook xmlns="{ns}" xmlns:r="{rns}"><sheets>{sheets}</sheets></workbook>'
    summary_sheet_xml = (
        f'<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        f'<worksheet xmlns="{ns}"><sheetData>'
        '<row r="1"><c r="A1" t="inlineStr"><is><t>Balance Check Q1 Q2 Q3 Q4</t></is></c></row>'
        '<row r="2"><c r="B2"><v>150</v></c></row>'
        '<row r="3"><c r="B3"><v>60</v></c></row>'
        '<row r="4"><c r="B4"><v>90</v></c></row>'
        '</sheetData></worksheet>'
    )
    scenario_input_sheet_xml = (
        f'<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        f'<worksheet xmlns="{ns}"><sheetData><row r="12">'
        '<c r="B12"><v>40</v></c><c r="C12"><v>60</v></c><c r="D12"><v>1</v></c>'
        '</row></sheetData></worksheet>'
    )
    scenario_formula_rows = "".join(
        f'<row r="{row}">' + "".join(
            f'<c r="{column}{row}"><f>Scenarios!$B$12+{offset}</f><v>{offset}</v></c>'
            for offset, column in enumerate("BCDEFGHIJ", 1)
        ) + '</row>'
        for row in (20, 21, 22, 30, 31, 32, 40, 41, 42, 50, 51, 52)
    )
    scenario_pnl_sheet_xml = (
        f'<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        f'<worksheet xmlns="{ns}"><sheetData>{scenario_formula_rows}</sheetData></worksheet>'
    )
    empty_sheet_xml = f'<?xml version="1.0" encoding="UTF-8" standalone="yes"?><worksheet xmlns="{ns}"><sheetData/></worksheet>'
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
        for i, sheet_name in enumerate(sheet_names):
            if sheet_name == "Summary":
                sheet_xml = summary_sheet_xml
            elif sheet_name == "Scenarios":
                sheet_xml = scenario_input_sheet_xml
            elif sheet_name == "Scenario_PnL":
                sheet_xml = scenario_pnl_sheet_xml
            else:
                sheet_xml = empty_sheet_xml
            zf.writestr(
                f"xl/worksheets/sheet{i+1}.xml",
                sheet_xml,
            )


def synthetic_report() -> str:
    filler = (
        "This synthetic self-test delivery exercises the validator chain only. "
        "It contains no company research and must never be presented as analysis. "
    )
    sections = [
        ("Snapshot timestamp", "The live snapshot and price timestamps are recorded; historical runs additionally freeze an information cutoff."),
        ("Conclusion", "Self-test conclusion placeholder with readiness disclosure."),
        ("Base forecast", "Base forecast placeholder rows spanning revenue, margin, and profit."),
        ("Drivers and customers", "Drivers placeholder: products, customers, units, ASP, mix, share."),
        ("Forward evidence and research synthesis", "Forward evidence placeholder: investor dialogue, independent research, technical papers, source independence clusters, rejected signals and falsification triggers."),
        ("Cash flow and capital", "Cash flow placeholder: working capital, capex, free cash flow."),
        ("Scenarios", "Scenario placeholder: reference path, material rival states and regime branches."),
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


def synthetic_model_graph() -> dict:
    return {
        "schema_version": "2.0",
        "graph_id": "graph://technology/TEST/20260718/v2",
        "as_of": "2026-07-18T00:00:00Z",
        "nodes": [
            {"id": "ai_units", "kind": "observable", "unit": "unit", "data_series_ids": ["D1", "D2"]},
            {"id": "ai_asp", "kind": "input", "unit": "USD/unit", "data_series_ids": ["D3", "D4"]},
            {"id": "ai_revenue", "kind": "derived", "unit": "USD", "financial_role": "revenue"},
            {"id": "cash_cost", "kind": "input", "unit": "USD"},
            {"id": "operating_profit", "kind": "derived", "unit": "USD", "financial_role": "operating_profit"},
            {"id": "nonoperating_income", "kind": "input", "unit": "USD"},
            {"id": "pretax_profit", "kind": "derived", "unit": "USD", "financial_role": "pretax_profit"},
            {"id": "tax_expense", "kind": "input", "unit": "USD", "financial_role": "tax_expense"},
            {"id": "nci_net_income", "kind": "input", "unit": "USD", "financial_role": "noncontrolling_interest_net_income"},
            {"id": "profit", "kind": "derived", "unit": "USD", "financial_role": "gaap_net_income_attributable"},
            {"id": "asp_break", "kind": "falsification", "unit": "dimensionless"},
            {"id": "competitive_supply", "kind": "competitor_response", "unit": "dimensionless"},
        ],
        "equations": [
            {"id": "eq_revenue", "output": "ai_revenue", "operation": "multiply", "inputs": ["ai_units", "ai_asp"]},
            {"id": "eq_operating_profit", "output": "operating_profit", "operation": "subtract", "inputs": ["ai_revenue", "cash_cost"]},
            {"id": "eq_pretax_profit", "output": "pretax_profit", "operation": "add", "inputs": ["operating_profit", "nonoperating_income"]},
            {"id": "eq_profit", "output": "profit", "operation": "subtract", "inputs": ["pretax_profit", "tax_expense", "nci_net_income"]},
        ],
        "main_line": {
            "carrier_node_ids": ["ai_units", "ai_asp"],
            "target_node_ids": ["profit"],
            "falsification_ids": ["asp_break"],
            "competitor_response_node_ids": ["competitive_supply"],
        },
    }


def synthetic_investment_contract() -> dict:
    def integrated_period(period: str, revenue: float, operating: float, pretax: float, tax: float, attributable: float) -> dict:
        consolidated = pretax - tax
        nci = consolidated - attributable
        return {
            "period": period,
            "income_statement": {
                "revenue": revenue,
                "operating_costs_and_expenses": revenue - operating,
                "operating_profit": operating,
                "nonoperating_income_expense_net": pretax - operating,
                "pretax_profit": pretax,
                "tax_expense": tax,
                "tax": tax,
                "nopat": operating - tax,
                "net_income": consolidated,
                "net_income_attributable_to_noncontrolling_interests": nci,
                "net_income_attributable": attributable,
            },
            "balance_sheet": {"cash": 0.0, "assets": revenue, "liabilities": 0.0, "equity": revenue},
            "cash_flow_statement": {
                "net_income": consolidated,
                "cash_from_operations": consolidated,
                "capex": 0.0,
                "free_cash_flow": consolidated,
                "net_change_in_cash": 0.0,
            },
            "roll_forwards": {
                "cash": {"opening": 0.0, "net_change": 0.0, "closing": 0.0},
                "ppe": {"opening": 0.0, "capex": 0.0, "depreciation": 0.0, "disposals": 0.0, "closing": 0.0},
                "debt": {"opening": 0.0, "borrowings": 0.0, "repayments": 0.0, "closing": 0.0},
                "working_capital": {"opening": 0.0, "change": 0.0, "closing": 0.0},
            },
        }

    return {
        "persistence_analysis": {
            "mean_reversion": {
                "status": "accepted",
                "object": "normalized_operating_margin",
                "unit": "ratio",
                "reference_class": "same lifecycle, qualification gate, capital intensity and cycle state",
                "reference_class_source_ids": ["SRC0", "SRC5"],
                "target_median": 0.18,
                "target_low": 0.12,
                "target_high": 0.24,
                "sample_selection_limits": "Survivors and incomparable qualification regimes are excluded.",
                "company_departure": "Qualification delays the response from new competitive capacity.",
                "speed_driver_node_ids": ["competitive_supply"],
                "fade_horizon_periods": 5,
                "falsification_node_ids": ["asp_break"],
                "scenario_ids": ["demand_contraction", "central_operating_path", "supply_tightness"],
            },
            "cost_behavior": [{
                "cost_line": "cash_operating_cost", "status": "accepted", "materiality": "critical",
                "activity_driver_node_id": "ai_units", "activity_unit": "unit",
                "elasticity_up": 0.55, "elasticity_down": 0.25,
                "adjustment_lag_periods": 2, "committed_resource_floor": 30.0,
                "floor_unit": "USDm", "exit_or_adjustment_cost": 5.0,
                "estimation_method": "company history plus named scenario sensitivity",
                "source_ids": ["SRC0", "SRC5"],
                "scenario_ids": ["demand_contraction", "central_operating_path", "supply_tightness"],
                "notes": "Down-state behavior reflects committed facilities and exit costs.",
            }],
        },
        "investment_case": {
            "decision_question": "What ASP supports value creation?",
            "variant_view": "The observed price implies a faster ASP fade.",
            "falsification_ids": ["asp_break"],
        },
        "integrated_model": {
            "periods": [
                integrated_period("FY2027", 100.0, 18.0, 17.0, 5.0, 12.0),
                integrated_period("FY2028", 110.0, 19.0, 18.0, 4.5, 13.5),
                integrated_period("FY2029", 120.0, 20.0, 19.0, 4.75, 14.25),
            ]
        },
        "value_creation": {
            "wacc": 0.10,
            "periods": [{
                "period": "FY2027", "reported_nopat": 14.0,
                "after_tax_normalization_adjustments": 1.0, "normalized_nopat": 15.0,
                "beginning_invested_capital": 75.0, "ending_invested_capital": 81.0,
                "average_invested_capital": 78.0, "average_roic": 15.0 / 78.0,
                "reinvestment": 6.0, "invested_capital_bridge_adjustment": 0.0,
                "reinvestment_rate": 0.40, "prior_normalized_nopat": 13.8,
                "incremental_invested_capital": 6.0, "incremental_nopat": 1.2,
                "incremental_roic": 0.20, "incremental_return_lag_periods": 1,
                "fundamental_growth": 0.08,
            }],
            "fade": {
                "terminal_roic": 0.15, "years_to_fade": 10,
                "competitive_response": "New supply compresses excess returns.",
                "schedule": [{
                    "period": "Terminal", "average_roic": 0.15,
                    "incremental_roic": 0.15, "reinvestment_rate": 0.20,
                    "fundamental_growth": 0.03,
                    "competitive_or_obsolescence_driver_node_ids": ["competitive_supply"],
                    "erosion_or_renewal_event": "Qualified supply closes the excess-return gap.",
                }],
            },
        },
        "valuation": {
            "currency": "USD",
            "dcf": {"pv_explicit_free_cash_flow": 450.0, "pv_terminal_value": 550.0, "enterprise_value": 1000.0},
            "residual_income": {"current_book_value": 600.0, "pv_residual_income": 330.0, "equity_value": 930.0},
            "reconciliation": {"dcf_equity_value": 910.0, "residual_income_equity_value": 930.0, "difference_pct": 20.0 / 910.0, "explanation": "Fade timing differs."},
            "enterprise_to_equity": {"enterprise_value": 1000.0, "cash": 50.0, "non_operating_assets": 20.0, "debt": 150.0, "noncontrolling_interest": 10.0, "other_adjustments": 0.0, "equity_value": 910.0},
            "per_share": {"equity_value": 910.0, "diluted_shares": 100.0, "value_per_share": 9.10},
            "terminal": {"wacc": 0.10, "growth_rate": 0.03, "terminal_roic": 0.15, "implied_reinvestment_rate": 0.20},
        },
        "market_implied_expectations": {
            "price_as_of": "2026-07-18", "observed_price": 7.0,
            "named_driver": "AI ASP", "implied_driver_value": 42.0,
            "model_driver_value": 50.0, "unit": "USD/unit",
            "falsification_trigger": "Contract ASP falls below USD 42/unit.",
        },
    }


def delivery_smoke_test(skill: Path, profile: str, td: Path) -> None:
    workspace = td / "delivery"
    scaffold = [
        sys.executable,
        str(skill / "scripts/scaffold_delivery.py"),
        "--workspace",
        str(workspace),
        "--entity",
        "TEST",
        "--security",
        "TEST",
    ]
    if profile == "trainer":
        scaffold.extend(["--as-of", "2026-07-18"])
    run(scaffold)
    manifest = json.loads((workspace / "run_manifest.json").read_text(encoding="utf-8"))
    manifest["fiscal_calendar"] = "calendar year"
    manifest["research_completeness_required"] = False
    manifest["readiness_target"] = "screen-grade"
    manifest["readiness_result"] = "screen-grade"
    manifest["analysis_primitives"] = ["unit-volume-price-cost"]
    manifest["materiality_routes"] = {
        "technology_ip": "material",
        "operating_cycle": "material",
        "internal_intangible": "material",
    }
    manifest["accounting_basis"] = {
        "forecast_basis_id": "ACCT-US-2026",
        "historical_basis_ids": ["ACCT-US-2026"],
        "bases": [{
            "basis_id": "ACCT-US-2026", "framework": "US_GAAP", "jurisdiction": "US",
            "version": "FASB ASC effective for fiscal years beginning 2026-01-01",
            "effective_at": "2026-01-01T00:00:00Z", "presentation_currency": "USD",
            "major_policy_choices": [{
                "policy_id": "revenue-recognition", "policy_area": "revenue_recognition",
                "choice": "ASC 606 contract-specific recognition", "source_ids": ["SRC0"],
            }],
        }],
        "comparability_bridges": [],
    }
    manifest["phase_status"] = {key: "complete" for key in manifest["phase_status"]}
    (workspace / "run_manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    src = json.loads((workspace / "source_manifest.json").read_text(encoding="utf-8"))
    source_profiles = [
        ("Example Corp", ["Example Corp Filing Team"], "issuer-filings", "regulatory_filings"),
        ("Example Corp", ["Example Corp IR Team"], "issuer-dialogue", "invoice_value_divided_by_accepted_units"),
        ("Independent Demand Data", ["Demand Panel Team"], "demand-panel", "sell_through_panel"),
        ("Independent Price Data", ["Price Panel Team"], "price-panel", "independent_transaction_price_panel"),
        ("Example Corp", ["Example Corp Product Team"], "issuer-product", "product_documentation"),
        ("Independent Research", ["Independent Research Team"], "external-research", "independent_research_synthesis"),
    ]
    source_roles = (
        "historical_fact", "management_claim", "leading_indicator",
        "leading_indicator", "technical_boundary", "assumption_support",
    )
    source_epistemic_classes = (
        "official_reported_fact", "management_statement_or_plan",
        "independent_external_observation", "independent_external_observation",
        "technical_evidence", "expert_or_analyst_opinion",
    )
    source_origin_record_kinds = (
        "entity_primary_disclosure", "entity_primary_disclosure",
        "original_measurement_observation", "original_measurement_observation",
        "scholarly_or_engineering_record", "expert_or_analyst_interpretation",
    )
    src["sources"] = [
        {
            "source_id": f"SRC{i}",
            "source_type": "filing" if i == 0 else (
                "earnings" if i == 1 else ("industry-research" if i == 5 else "official-product")
            ),
            "origin_record_kind": source_origin_record_kinds[i],
            "epistemic_class": source_epistemic_classes[i],
            "publisher": source_profiles[i][0],
            "authors": source_profiles[i][1],
            "root_original_source_id": f"SRC{i}",
            "derived_from_source_id": None,
            "common_origin": False,
            "independence_cluster": source_profiles[i][2],
            "measurement_method_id": source_profiles[i][3],
            "published_at": (
                "2026-07-19T00:00:00Z"
                if profile == "live" else f"2026-0{min(i+1,6)}-01T00:00:00Z"
            ),
            "retrieved_at": (
                "2026-07-19T00:00:00Z" if profile == "live" else "2026-07-18T00:00:00Z"
            ),
            "available_at": (
                "2026-07-19T00:00:00Z" if profile == "live" else f"2026-0{min(i+1,6)}-01T00:00:00Z"
            ),
            "period_scope": "FY2026",
            "evidence_tier": "E0" if i == 0 else "E1",
            "content_hash": f"unhashed:smoke-fixture-{i}",
            "location": f"https://example.com/{i}",
            "claim_or_fact": "official fact",
            "allowed_use": "base anchor",
            "limitations": "",
            "authority": "audited_filing" if i == 0 else (
                "company" if i in {1, 4} else "third_party"
            ),
            "independence": "first_party" if i in {0, 1, 4} else "independent",
            "directness": "direct",
            "role": source_roles[i],
            "as_of_valid": True,
            "scope_match": {"entity": True, "product": True, "geography": True, "period": True, "unit": True},
        }
        for i in range(6)
    ]
    if profile == "live":
        for source in src["sources"]:
            source.pop("as_of_valid", None)
    (workspace / "source_manifest.json").write_text(json.dumps(src, indent=2), encoding="utf-8")
    (workspace / "internal_intangible_investment.json").write_text(
        json.dumps(
            {
                "schema_version": "internal-intangible-investment/v1",
                "materiality_threshold_pct_revenue": 1.0,
                "categories": [{
                    "category_id": "synthetic_internal_investment",
                    "status": "not_material_with_reason",
                    "reason": (
                        "Synthetic smoke-test disclosure supports a numeric immateriality "
                        "exception and carries no company conclusion."
                    ),
                    "source_ids": ["SRC0"],
                    "materiality_test": {
                        "amount": 0.5,
                        "revenue": 100.0,
                        "pct_revenue": 0.5,
                    },
                }],
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    assumption_path = workspace / "assumption_register.csv"
    with assumption_path.open(encoding="utf-8-sig", newline="") as handle:
        assumption_header = next(csv.reader(handle))
    with assumption_path.open("a", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=assumption_header)
        writer.writerow({
            "assumption_id": "A1", "node_id": "ai_asp", "entity": "TEST", "segment": "AI",
            "primitive": "unit-volume-price-cost", "metric": "ASP", "period": "FY2027",
            "frequency": "quarterly", "scenario": "central_operating_path", "value": "50", "unit": "USD/unit",
            "input_type": "assumption", "source_ids": "SRC0;SRC1", "claim_ids": "C1",
            "confidence": "medium", "applies_to": "AI revenue", "does_not_apply_to": "legacy revenue",
            "test_delta": "ASP -10%", "falsification_id": "asp_break", "next_evidence": "next earnings",
            "owner": "analyst", "notes": "",
        })
    signal_date = "2026-07-19" if profile == "live" else "2026-07-01"
    sig = [
        ["S1", "TEST", "SRC0", "C1", "Example Corp", signal_date, "issuer-filing", "E0", "state_signal", "issuer-filings", "2", "2", "2", "2", "0", "1", "2", "0-1y", "base_driver", "ai_asp", "reported ASP anchors the named driver", "https://example.com/s1", "reported scope only"],
        ["S2", "TEST", "SRC5", "", "Independent Research", signal_date, "industry-research", "E3", "timing_signal", "external-research", "2", "2", "2", "2", "0", "-1", "2", "0-1y", "monitor", "inventory", "monitor inventory pressure", "https://example.com/s2", "method recorded"],
        ["S3", "TEST", "SRC5", "C2", "Independent Research", signal_date, "technical-paper-standard", "E2", "failure_boundary", "external-research", "2", "2", "1", "2", "0", "1", "1", "2-5y", "scenario_only", "ai_asp", "bounds ASP uplift in a rival state", "https://example.com/s3", "not commercial"],
        ["S4", "TEST", "SRC5", "", "Independent Research", signal_date, "technical-paper-standard", "E2", "feasibility_bound", "external-research", "2", "2", "2", "2", "0", "1", "2", "2-5y", "monitor", "ai_units", "monitor ratification timing", "https://example.com/s4", "standard timing"],
    ]
    with (workspace / "forward_signal_cards.csv").open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f)
        w.writerow(["signal_id", "case_id", "source_id", "claim_ids", "publisher", "published_at", "source_family", "evidence_tier", "evidence_role", "independence_cluster", "method_transparency", "specificity", "causal_proximity", "falsifiability", "incentive_bias", "direction", "strength", "horizon", "allowed_use", "model_driver", "model_impact", "source_url", "limitations"])
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
        w.writerow(["source_id", "cluster_id", "root_original_source_id", "derived_from_source_id", "relationship", "common_origin", "publisher", "authors", "measurement_method_id", "independence_basis", "notes"])
        for i, (publisher, authors, cluster, method) in enumerate(source_profiles):
            w.writerow([f"SRC{i}", cluster, f"SRC{i}", "", "original", "false", publisher, ";".join(authors), method, "root observation", "independent source chain"])
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
        report_text = (skill / "assets/examples/sandisk_v73/Sandisk_SNDK_v7.3_模型报告.md").read_text(encoding="utf-8") + "\n\n## Forward evidence and research synthesis\nInvestor dialogue, independent research, technical papers, source independence clusters, rejected signals and falsification triggers were reviewed.\n\n## 买入纪律\nRecommended buy price derives from the Bear fair value with a stated margin of safety.\n\n## 一致性检查\nArithmetic consistency check: implied tax rate, segment sums, EPS x shares reconcile.\n\n## 核心变量\nThesis carriers named.\n\n## 隐含指标\nImplied yoy and incremental margin stated.\n\n## 线下项筛查\nTax rate and valuation allowance are normalized. Interest income, interest expense and FX are modeled from cash, debt and currency exposure. No material impairment, restructuring or other one-off item is assumed. Share count and buyback dilution are explicit.\n"
        (workspace / "report.md").write_text(report_text, encoding="utf-8")
        (workspace / "model").mkdir(exist_ok=True)
        write_minimal_workbook(workspace / "model/model.xlsx", SMOKE_SHEETS)
    else:
        (workspace / "report.md").write_text(synthetic_report(), encoding="utf-8")
        (workspace / "model").mkdir(exist_ok=True)
        write_minimal_workbook(workspace / "model/model.xlsx", SMOKE_SHEETS)
    with (workspace / "report.md").open("a", encoding="utf-8") as handle:
        handle.write("\n\nFY+1 base revenue point 100.\n")
    snap = json.loads((workspace / "forecast_snapshot.json").read_text(encoding="utf-8"))
    snap["accounting_basis_id"] = "ACCT-US-2026"
    snap["source_pack_hash"] = "sha256:test"
    snap["scenario_probabilities"] = {
        "demand_contraction": 0.2,
        "central_operating_path": 0.55,
        "supply_tightness": 0.2,
        "competitive_supply_break": 0.05,
    }
    snap.update(synthetic_investment_contract())
    snap["valuation_summary"].update({
        "reference_scenario_id": "central_operating_path",
        "fair_value_by_scenario_id": {"central_operating_path": 9.10},
        "not_valued_scenario_ids": [
            "demand_contraction",
            "supply_tightness",
            "competitive_supply_break",
        ],
        "valuation_completeness": "reference_only_executable",
        "recommended_buy_price": None,
        "action": "watch",
    })
    snap["outputs"]["year_1"].update({
        "period": "FY2027", "low_scenario_id": "demand_contraction", "high_scenario_id": "supply_tightness",
        "revenue_point": 100.0, "revenue_low": 90.0, "revenue_high": 115.0,
        "operating_profit_point": 18.0, "operating_profit_low": 14.0,
        "operating_profit_high": 24.0,
        "pretax_profit_point": 17.0, "pretax_profit_low": 13.0,
        "pretax_profit_high": 23.0,
        "tax_expense_point": 5.0, "tax_expense_low": 4.0, "tax_expense_high": 5.0,
        "noncontrolling_interest_net_income_point": 0.0,
        "noncontrolling_interest_net_income_low": 0.0,
        "noncontrolling_interest_net_income_high": 0.0,
        "net_income_point": 12.0, "net_income_low": 9.0, "net_income_high": 18.0,
        "profit_point": 12.0, "profit_low": 9.0, "profit_high": 18.0,
    })
    snap["outputs"]["year_2"].update({
        "period": "FY2028", "low_scenario_id": "demand_contraction", "high_scenario_id": "supply_tightness",
        "revenue_point": 110.0, "revenue_low": 90.0, "revenue_high": 130.0,
        "operating_profit_point": 19.0, "operating_profit_low": 14.0,
        "operating_profit_high": 25.0,
        "pretax_profit_point": 18.0, "pretax_profit_low": 13.0,
        "pretax_profit_high": 24.0,
        "tax_expense_point": 4.5, "tax_expense_low": 4.0, "tax_expense_high": 6.0,
        "noncontrolling_interest_net_income_point": 0.0,
        "noncontrolling_interest_net_income_low": 0.0,
        "noncontrolling_interest_net_income_high": 0.0,
        "net_income_point": 13.5, "net_income_low": 9.0, "net_income_high": 18.0,
        "profit_point": 13.5,
        "profit_low": 9.0, "profit_high": 18.0,
    })
    snap["outputs"]["year_3_distribution"].update({
        "period": "FY2029", "low_scenario_id": "demand_contraction", "high_scenario_id": "supply_tightness",
        "revenue_point": 120.0, "revenue_low": 95.0, "revenue_high": 150.0,
        "operating_profit_point": 20.0, "operating_profit_low": 13.0,
        "operating_profit_high": 28.0,
        "pretax_profit_point": 19.0, "pretax_profit_low": 12.0,
        "pretax_profit_high": 27.0,
        "tax_expense_point": 4.75, "tax_expense_low": 4.0, "tax_expense_high": 6.0,
        "noncontrolling_interest_net_income_point": 0.0,
        "noncontrolling_interest_net_income_low": 0.0,
        "noncontrolling_interest_net_income_high": 0.0,
        "net_income_point": 14.25, "net_income_low": 8.0, "net_income_high": 21.0,
        "profit_point": 14.25,
        "profit_low": 8.0, "profit_high": 21.0,
    })
    snap["historical_base"] = {"trailing_organic_growth_pct": 8.0, "base_period": "FY2026", "note": "fixture"}
    snap["driver_tree"] = {
        "main_line": "AI capacity ramp",
        "thesis_carriers": ["FY+2 AI unit ASP (USD/unit)", "FY+2 AI shipments (units)"],
        "partition": {
            "partition_id": "primary-revenue-segments",
            "dimension": "analytical_segment",
            "exhaustive": True,
            "mutually_exclusive": True,
            "declared_residual": 0.0,
        },
        "segments": [
            {"name": "Traditional", "basis": "volume_price", "revenue_point": 80.0, "main_line": False},
            {
                "name": "AI", "basis": "capacity_ramp", "revenue_point": 20.0,
                "main_line": True, "unit": "units", "capacity": 500.0,
                "volume": 400.0, "price": 50.0, "unit_cost": 30.0,
            },
        ],
        "cross_check_views": [],
    }
    snap["growth_challenger_review"] = [{
        "challenger": "trailing_organic_growth", "horizon": "year_2", "status": "accepted",
        "challenger_growth_pct": 8.0, "driver_tree_growth_pct": 10.0,
        "difference_direction": "acceleration", "material_difference": True,
        "materiality_basis": "The two-point gap changes FY+2 revenue materially.",
        "transition_driver_node_ids": ["ai_units"],
        "named_state_ids": ["terminal_demand_up", "capacity_available"],
        "bridge": [{"driver_node_id": "ai_units", "delta_growth_pct": 2.0}],
        "notes": "Named demand and capacity states reconcile the transition.",
    }, *[{
        "challenger": challenger, "horizon": "year_2", "status": "not_available_with_reason",
        "notes": "No point-in-time comparable series exists for this synthetic fixture.",
    } for challenger in ("run_rate", "company_guidance", "consensus", "reference_class")]]
    (workspace / "forecast_snapshot.json").write_text(json.dumps(snap, indent=2), encoding="utf-8")
    graph = synthetic_model_graph()
    (workspace / "model_graph.json").write_text(json.dumps(graph, indent=2), encoding="utf-8")

    def write_scaffold_csv(name: str, rows: list[dict[str, object]]) -> None:
        path = workspace / name
        with path.open(encoding="utf-8-sig", newline="") as handle:
            header = next(csv.reader(handle))
        with path.open("w", encoding="utf-8-sig", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=header)
            writer.writeheader()
            writer.writerows(rows)

    product_driver_common = {
        "materiality": "critical", "primary_tree_or_cross_check": "primary",
        "partition_id": "primary-revenue-segments", "partition_dimension": "analytical_segment",
        "partition_exhaustive": "true", "partition_mutually_exclusive": "true",
        "revenue_unit": "USD", "payer_or_customer": "named customer groups",
        "end_user": "end demand", "equation_primitive": "unit-volume-price-cost",
        "volume_usage_or_deployment_driver": "ai_units", "price_arpu_or_asp": "ai_asp",
        "cost_and_capacity_constraint": "cash_cost", "program_stage": "qualified production",
        "evidence_source_ids": "SRC0;SRC1", "assumption_ids": "A1", "confidence": "medium",
        "schedule_status": "accepted", "consolidation_link": "ai_revenue",
        "residual_or_ratio_carry": "false", "human_required": "false",
    }
    write_scaffold_csv("product_customer_driver_schedule.csv", [
        {**product_driver_common, "segment_or_product": "Traditional", "driver_node_ids": "ai_units;cash_cost"},
        {**product_driver_common, "segment_or_product": "AI", "driver_node_ids": "ai_units;ai_asp;cash_cost"},
    ])
    write_scaffold_csv("technology_commercialization_register.csv", [{
        "technology_or_product": "Competing accelerator route",
        "materiality": "critical",
        "current_stage": "prototype evidence only",
        "technical_parameter": "prototype benchmark throughput",
        "parameter_unit": "relative index",
        "trl": "not asserted",
        "mrl": "not established",
        "paper_source_ids": "SRC5",
        "patent_evidence_status": "not_material_with_reason",
        "patent_not_material_reason": "Synthetic package fixture tests paper-to-scenario permission only.",
        "benchmark_or_prototype": "Controlled prototype benchmark under declared laboratory conditions.",
        "manufacturing_process_and_yield": "No production-process or yield inference is permitted.",
        "customer_evaluation_or_qualification": "No customer qualification evidence is available.",
        "capacity_available_at": "unknown",
        "production_evidence": "none",
        "commercial_evidence": "none",
        "revenue_evidence": "none",
        "competitor_route": "A rival prototype could become a qualified supply route.",
        "technical_bottleneck": "Production transfer and customer qualification remain unproved.",
        "allowed_model_use": "scenario_only",
        "driver_node_ids": "competitive_supply",
        "falsification_trigger": "Independent production qualification is not observed by the scenario date.",
        "confidence": "low",
        "reviewer": "synthetic-independent-reviewer",
    }])
    technical_evidence_record = {
        "schema_version": "technical-evidence-record/v2",
        "record_id": "TECH-SMOKE-1",
        "technology_or_product": "Competing accelerator route",
        "source_id": "SRC5",
        "doi": "10.5555/synthetic.2026.1",
        "doi_unavailable_reason": "",
        "stable_identifier": "doi:10.5555/synthetic.2026.1",
        "version": "synthetic version of record dated 2026-03-01",
        "publication_status": "peer_reviewed",
        "scholarly_record_status": "current",
        "status_checked_at": "2026-07-20T00:00:00Z",
        "status_source_ids": ["SRC5"],
        "evidence_design": "experimental",
        "exact_claim": "The prototype completed the named benchmark under the declared laboratory conditions.",
        "experimental_conditions": "Laboratory prototype; controlled workload; no production line transfer.",
        "sample_applicability": "applicable",
        "sample_applicability_reason": None,
        "sample_description": "Sixteen synthetic prototype devices in one declared test campaign.",
        "sample_size_value": 16,
        "sample_size_unit": "prototype devices",
        "benchmark_applicability": "applicable",
        "benchmark_applicability_reason": None,
        "benchmark_name": "Synthetic accelerator benchmark",
        "benchmark_version": "v1",
        "benchmark_result": "Prototype completion was observed; commercial performance was not tested.",
        "uncertainty": "Single campaign; no independent replication or production confidence interval.",
        "data_availability": "restricted",
        "data_location_or_reason": "Synthetic package fixture; underlying measurements are not distributed.",
        "code_availability": "not_available",
        "code_location_or_reason": "Synthetic package fixture contains no executable benchmark code.",
        "computational_reproducibility": "not_attempted",
        "reproduction_source_ids": [],
        "independent_replication_status": "not_checked",
        "independent_replication_source_ids": [],
        "orthogonal_engineering_evidence": "No orthogonal production test is claimed.",
        "orthogonal_engineering_evidence_source_ids": [],
        "funding": "Synthetic fixture; no issuer funding is represented.",
        "conflicts_of_interest": "Synthetic fixture; no economic conflict is represented.",
        "competing_technologies": "The incumbent route remains the production reference.",
        "negative_results": "Production transfer, yield, qualification and cost were not established.",
        "production_transfer_status": "laboratory_only",
        "production_transfer_differences": "Factory process, scale, yield and customer qualification are unobserved.",
        "production_transfer_bridge": None,
        "technical_boundary": "Prototype feasibility only; no demand, capacity, adoption, revenue or timing permission.",
        "allowed_use": "scenario_only",
        "driver_node_ids": ["competitive_supply"],
        "scenario_ids": ["competitive_supply_break"],
        "commercialization_permission": "none",
        "limitations": "The record opens a rival-state scenario but cannot enter the reference forecast as a parameter.",
    }
    (workspace / "technical_evidence_records.jsonl").write_text(
        json.dumps(technical_evidence_record, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

    series_common = {
        "published_at": "2026-07-19T00:00:00Z" if profile == "live" else "2026-07-01T00:00:00Z",
        "retrieved_at": "2026-07-19T00:00:00Z" if profile == "live" else "2026-07-18T00:00:00Z",
        "observation_value": "100", "observation_type": "flow",
        "available_at": "2026-07-19T00:00:00Z" if profile == "live" else "2026-07-15T00:00:00Z",
        "revision_of_series_id": "none", "classification_version": "2026Q2-v1",
        "input_series_ids": "none",
        "vintage_at": "2026-07-19T00:00:00Z" if profile == "live" else "2026-07-01T00:00:00Z",
        "revision_at": "2026-07-19T00:00:00Z" if profile == "live" else "2026-07-01T00:00:00Z",
        "period_start": "2026-04-01",
        "period_end": "2026-06-30", "frequency": "quarterly", "unit": "unit",
        "currency": "N/A", "entity_scope": "market", "product_scope": "AI device",
        "metric_construct_id": "accepted_end_customer_shipments_flow",
        "geography_scope": "global", "population_coverage": "named panel with disclosed coverage",
        "transformation": "none required; raw reported series", "revision_policy": "retain each vintage",
        "lag_days": "19" if profile == "live" else "15", "allowed_model_use": "base_parameter", "driver_node_ids": "ai_units",
        "conclusion_critical": "true", "status": "accepted", "notes": "",
    }
    asp_series_common = {
        **series_common,
        "unit": "USD/unit",
        "driver_node_ids": "ai_asp",
        "product_scope": "AI device contract pricing",
        "metric_construct_id": "matched_realized_net_asp",
    }
    write_scaffold_csv("data_series_register.csv", [
        {
            **series_common, "series_id": "D1", "metric_name": "terminal demand",
            "vintage_id": "D1-v1",
            "source_id": "SRC0", "original_source_id": "SRC0", "independence_cluster": "issuer-filings",
            "measurement_method_id": "regulatory_filings",
            "metric_definition": "units accepted by end customers", "known_bias": "scope excludes small vendors",
            "cross_check_series_ids": "D2", "cross_check_result": "definition bridge reconciles within 3%",
        },
        {
            **series_common, "series_id": "D2", "metric_name": "channel-adjusted shipments",
            "vintage_id": "D2-v1", "observation_value": "102",
            "source_id": "SRC2", "original_source_id": "SRC2", "independence_cluster": "demand-panel",
            "measurement_method_id": "sell_through_panel",
            "metric_definition": "sell-through adjusted for channel inventory", "known_bias": "survey non-response",
            "cross_check_series_ids": "D1", "cross_check_result": "definition bridge reconciles within 3%",
        },
        {
            **asp_series_common, "series_id": "D3", "metric_name": "realized contract ASP",
            "vintage_id": "D3-v1", "observation_value": "50",
            "source_id": "SRC1", "original_source_id": "SRC1", "independence_cluster": "issuer-dialogue",
            "measurement_method_id": "invoice_value_divided_by_accepted_units",
            "metric_definition": "recognized product revenue divided by accepted units on a matched scope",
            "known_bias": "reported mix can differ from the forecast product mix",
            "cross_check_series_ids": "D4", "cross_check_result": "mix and timing bridge reconciles within 2%",
        },
        {
            **asp_series_common, "series_id": "D4", "metric_name": "independent market ASP",
            "vintage_id": "D4-v1", "observation_value": "51",
            "source_id": "SRC3", "original_source_id": "SRC3", "independence_cluster": "price-panel",
            "measurement_method_id": "independent_transaction_price_panel",
            "metric_definition": "volume-weighted transaction price for the matched qualified product set",
            "known_bias": "panel coverage excludes privately negotiated long-tail contracts",
            "cross_check_series_ids": "D3", "cross_check_result": "mix and timing bridge reconciles within 2%",
        },
    ])
    financial_fact = {
        "fact_id": "F1", "entity_id": "TEST", "accounting_basis_id": "ACCT-US-2026", "source_id": "SRC0",
        "accession_or_filing_id": "TEST-2026-10K",
        "filed_at": "2026-07-19T00:00:00Z" if profile == "live" else "2026-03-01T00:00:00Z",
        "retrieved_at": "2026-07-19T00:00:00Z" if profile == "live" else "2026-07-18T00:00:00Z",
        "form": "10-K", "fiscal_year": "2025", "fiscal_period": "FY",
        "period_start": "2025-01-01", "period_end": "2025-12-31", "fact_name": "Revenue",
        "taxonomy": "us-gaap", "tag": "RevenueFromContractWithCustomerExcludingAssessedTax",
        "dimensions": "consolidated", "unit": "USD", "decimals": "-6", "scale": "1000000",
        "sign": "positive", "reported_value": "100", "normalized_value": "100", "currency": "USD",
        "statement_or_note_anchor": "income statement revenue", "extraction_method": "rendered filing checked",
        "amendment_or_restatement": "original", "predecessor_fact_id": "",
        "comparability_adjustment": "no adjustment", "status": "accepted", "conflict_note": "no conflict",
    }
    if profile == "trainer":
        financial_fact["as_of_cutoff"] = "2026-07-18T23:59:59Z"
    write_scaffold_csv("financial_fact_ledger.csv", [financial_fact])
    earnings_rows = []
    earnings_periods = {
        "FY2027": (("revenue", 100, 0, "ai_revenue"), ("core_operating_profit", 20, -80, "operating_profit"),
                   ("gaap_operating_profit", 18, -2, "operating_profit"), ("pretax_profit", 17, -1, "pretax_profit"),
                   ("gaap_net_income_attributable", 12, -5, "profit")),
        "FY2028": (("revenue", 110, 0, "ai_revenue"), ("core_operating_profit", 21, -89, "operating_profit"),
                   ("gaap_operating_profit", 19, -2, "operating_profit"), ("pretax_profit", 18, -1, "pretax_profit"),
                   ("gaap_net_income_attributable", 13.5, -4.5, "profit")),
        "FY2029": (("revenue", 120, 0, "ai_revenue"), ("core_operating_profit", 22, -98, "operating_profit"),
                   ("gaap_operating_profit", 20, -2, "operating_profit"), ("pretax_profit", 19, -1, "pretax_profit"),
                   ("gaap_net_income_attributable", 14.25, -4.75, "profit")),
    }
    tax_by_period = {"FY2027": 5, "FY2028": 4.5, "FY2029": 4.75}
    for period, period_layers in earnings_periods.items():
        for layer, amount, bridge, node in period_layers:
            row = {
                "period": period, "profit_layer": layer, "reported_amount": str(amount),
                "bridge_from_prior_layer": str(bridge),
                "tax_expense": str(tax_by_period[period]) if layer == "gaap_net_income_attributable" else "",
                "net_income_attributable_to_noncontrolling_interests": "0" if layer == "gaap_net_income_attributable" else "",
                "normalization_adjustment": "0", "normalized_amount": str(amount),
                "cash_support": str(amount), "accrual_component": "0", "investment_adjustment": "0",
                "cycle_adjustment": "0", "persistence_driver": "named demand and cost equations",
                "competitive_response": "qualified supply response", "fade_target": str(amount),
                "fade_horizon": "3", "source_ids": "SRC0;SRC1", "driver_node_ids": node,
                "status": "accepted", "notes": "synthetic contract fixture",
            }
            if layer == "gaap_operating_profit":
                operating_tax = amount * 0.20
                nopat = amount - operating_tax
                row.update({
                    "operating_tax_expense": str(operating_tax),
                    "nopat": str(nopat),
                    "cash_support": str(nopat),
                    "accrual_component": "0",
                    "noa_bridge_residual": "0",
                })
            earnings_rows.append(row)
    write_scaffold_csv("earnings_power_bridge.csv", earnings_rows)
    claim = {
        "claim_id": "C1", "text": "AI ASP is contractually supported", "claim_type": "reported_fact",
        "proposition_scope": "reported_history",
        "source_ids": ["SRC0"],
        "evidence_links": [
            {
                "source_id": source_id,
                "relation": "support",
                "evidence_function": "direct_anchor",
                "authority_scope": "Named FY2026 ASP fact within the issuer reporting perimeter.",
                "measurement_or_construct_basis": "Invoice value divided by accepted units for the named period.",
                "incentive_conflict": "Issuer incentive is disclosed and bounded to the reported proposition.",
                "reconciliation_status": "not_applicable",
                "permission_rationale": "The source observes the same ASP construct, unit, period, and entity scope.",
                "observation_ids": [],
            }
            for source_id in ("SRC0",)
        ],
        "allowed_use": "base_parameter", "driver_node_ids": ["ai_asp"],
        "as_of": "2026-07-18T00:00:00Z", "status": "accepted", "limitations": [],
    }
    scenario_claim = {
        "claim_id": "C2",
        "text": "Independent research bounds the rival ASP state",
        "claim_type": "analyst_assumption",
        "proposition_scope": "scenario_only",
        "source_ids": ["SRC5"],
        "evidence_links": [{
            "source_id": "SRC5",
            "relation": "support",
            "evidence_function": "direct_anchor",
            "authority_scope": "Independent research interpretation within its stated sample.",
            "measurement_or_construct_basis": "Named ASP construct and rival-state horizon.",
            "incentive_conflict": "Research incentives disclosed for independent review.",
            "reconciliation_status": "not_applicable",
            "permission_rationale": "The source bounds only the named rival state.",
            "observation_ids": [],
        }],
        "allowed_use": "scenario_only",
        "driver_node_ids": ["ai_asp"],
        "as_of": "2026-07-18T00:00:00Z",
        "status": "accepted",
        "limitations": [],
    }
    (workspace / "claim_ledger.jsonl").write_text(
        json.dumps(claim) + "\n" + json.dumps(scenario_claim) + "\n",
        encoding="utf-8",
    )

    chain_fields = (
        "revenue", "operating_costs_and_expenses", "operating_profit",
        "nonoperating_income_expense_net", "pretax_profit", "tax_expense",
        "net_income", "net_income_attributable_to_noncontrolling_interests",
        "net_income_attributable",
    )
    chain_columns = dict(zip(chain_fields, "BCDEFGHIJ"))
    chain_rows = {
        "demand_contraction": 20,
        "central_operating_path": 30,
        "supply_tightness": 40,
        "competitive_supply_break": 50,
    }
    chain_period_offsets = {"FY2027": 0, "FY2028": 1, "FY2029": 2}

    def scenario_profit_period(
        scenario_id: str,
        period: str,
        revenue: float,
        operating: float,
        pretax: float,
        tax: float,
        nci: float,
        shock_node: str | None = None,
    ) -> dict:
        consolidated = pretax - tax
        row_number = chain_rows[scenario_id] + chain_period_offsets[period]
        values = {
            "revenue": revenue,
            "operating_costs_and_expenses": revenue - operating,
            "operating_profit": operating,
            "nonoperating_income_expense_net": pretax - operating,
            "pretax_profit": pretax,
            "tax_expense": tax,
            "net_income": consolidated,
            "net_income_attributable_to_noncontrolling_interests": nci,
            "net_income_attributable": consolidated - nci,
        }
        return {
            "period": period,
            **values,
            "model_cells": {
                field: f"Scenario_PnL!{chain_columns[field]}{row_number}"
                for field in chain_fields
            },
            "applied_shock_node_ids": [shock_node] if shock_node else [],
            "joint_state_id": f"{scenario_id}-joint-path",
        }

    scenario_paths = {
        "demand_contraction": [
            scenario_profit_period("demand_contraction", "FY2027", 90.0, 14.0, 13.0, 4.0, 0.0),
            scenario_profit_period("demand_contraction", "FY2028", 90.0, 14.0, 13.0, 4.0, 0.0, "ai_asp"),
            scenario_profit_period("demand_contraction", "FY2029", 95.0, 13.0, 12.0, 4.0, 0.0, "ai_asp"),
        ],
        "central_operating_path": [
            scenario_profit_period("central_operating_path", "FY2027", 100.0, 18.0, 17.0, 5.0, 0.0),
            scenario_profit_period("central_operating_path", "FY2028", 110.0, 19.0, 18.0, 4.5, 0.0),
            scenario_profit_period("central_operating_path", "FY2029", 120.0, 20.0, 19.0, 4.75, 0.0),
        ],
        "supply_tightness": [
            scenario_profit_period("supply_tightness", "FY2027", 115.0, 24.0, 23.0, 5.0, 0.0),
            scenario_profit_period("supply_tightness", "FY2028", 130.0, 25.0, 24.0, 6.0, 0.0, "ai_asp"),
            scenario_profit_period("supply_tightness", "FY2029", 150.0, 28.0, 27.0, 6.0, 0.0, "ai_asp"),
        ],
        "competitive_supply_break": [
            scenario_profit_period("competitive_supply_break", "FY2027", 95.0, 16.0, 15.0, 4.0, 0.0),
            scenario_profit_period("competitive_supply_break", "FY2028", 100.0, 16.0, 15.0, 4.0, 0.0),
            scenario_profit_period(
                "competitive_supply_break", "FY2029", 105.0, 15.0, 14.0, 4.0, 0.0,
                "competitive_supply",
            ),
        ],
    }
    scenario_set = {"schema_version": "2.0", "scenarios": [
        {"id": "demand_contraction", "role": "alternative", "probability": 0.2, "shocks": [{"node_id": "ai_asp", "operation": "set", "value": 40, "unit": "USD/unit", "model_cell_or_formula": "Scenarios!B12", "effective_period": "FY2028", "lag_periods": 0}], "profit_chain_periods": scenario_paths["demand_contraction"], "narrative": "price pressure"},
        {"id": "central_operating_path", "role": "reference", "probability": 0.55, "shocks": [], "profit_chain_periods": scenario_paths["central_operating_path"], "narrative": "central causal path"},
        {"id": "supply_tightness", "role": "alternative", "probability": 0.2, "shocks": [{"node_id": "ai_asp", "operation": "set", "value": 60, "unit": "USD/unit", "model_cell_or_formula": "Scenarios!C12", "effective_period": "FY2028", "lag_periods": 0}], "profit_chain_periods": scenario_paths["supply_tightness"], "narrative": "tight supply"},
        {"id": "competitive_supply_break", "role": "alternative", "probability": 0.05, "shocks": [{"node_id": "competitive_supply", "operation": "set", "value": 1, "unit": "dimensionless", "model_cell_or_formula": "Scenarios!D12", "effective_period": "FY2028", "lag_periods": 1}], "profit_chain_periods": scenario_paths["competitive_supply_break"], "narrative": "new supply"},
    ]}
    (workspace / "scenario_set.json").write_text(json.dumps(scenario_set, indent=2), encoding="utf-8")
    (workspace / "model_checks.json").write_text(json.dumps({"schema_version": "2.0", "checks": [
        {
            "id": "BS_CHECK", "category": "balance_sheet",
            "calculation": {"operation": "signed_sum", "terms": [
                {"name": "assets", "coefficient": 1.0, "model_cell": "Summary!B2"},
                {"name": "liabilities", "coefficient": -1.0, "model_cell": "Summary!B3"},
                {"name": "equity", "coefficient": -1.0, "model_cell": "Summary!B4"},
            ]},
            "value": 0.0, "tolerance": 0.0, "unit": "USD", "status": "passed",
        }
    ]}, indent=2), encoding="utf-8")
    with (workspace / "driver_monitoring.csv").open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["driver_id", "model_cell_or_formula", "monitor_type", "thesis_link", "series", "source_id", "frequency", "last_observed_at", "next_expected_at", "milestone_date", "current_value", "model_value", "unit", "trigger_operator", "trigger_value", "action_if_breached", "owner", "status"])
        writer.writerow(["ai_asp", "Drivers!F18", "continuous", "main line", "contract ASP", "SRC1", "quarterly", "2026-06-30", "2026-09-30", "", "48", "50", "USD/unit", "below", "42", "re-underwrite price path", "analyst", "active"])
        writer.writerow(["asp_break", "Tech_Gates!B12", "milestone", "falsification", "contract ASP breach", "SRC1", "event_driven", "2026-06-30", "2026-08-15", "2026-08-15", "0", "0", "dimensionless", "above", "0", "invalidate base case", "analyst", "active"])
        writer.writerow(["competitive_supply", "Tech_Gates!B13", "milestone", "technology scenario gate", "independent production qualification", "SRC5", "event_driven", "2026-06-30", "2027-06-30", "2027-06-30", "0", "1", "dimensionless", "above", "0", "re-underwrite rival supply timing", "analyst", "active"])
    pool_common = {
        "boundary_id": "AI_GLOBAL", "period": "FY2027", "geography": "global",
        "product_scope": "AI devices", "currency": "USD", "profit_measure": "operating_profit",
        "capacity_or_supply": "500 units", "pricing_mechanism": "contract ASP",
        "entry_exit_barrier": "customer qualification", "competitor_response": "qualified new supply",
        "response_lead_time_days": "365", "cycle_state": "balanced", "source_ids": "SRC0;SRC1",
        "driver_node_ids": "ai_asp;competitive_supply", "as_of": "2026-07-18",
        "data_vintage_at": "2026-07-01", "status": "accepted", "notes": "",
    }
    write_scaffold_csv("industry_profit_pool.csv", [
        {**pool_common, "row_type": "total", "value_chain_node": "industry total", "revenue_pool": "100", "profit_pool": "20", "invested_capital": "75", "company_revenue_share": "1", "company_profit_share": "1"},
        {**pool_common, "row_type": "component", "value_chain_node": "AI devices", "revenue_pool": "100", "profit_pool": "20", "invested_capital": "75", "company_revenue_share": "1", "company_profit_share": "1"},
    ])
    cycle_rows = []
    for index, family in enumerate([
        "end_demand", "sell_through", "sell_in_or_orders", "channel_or_customer_inventory",
        "company_inventory", "backlog_and_cancellations", "production_utilization_yield",
        "installed_and_announced_capacity", "spot_contract_realized_price",
        "unit_cost_and_cash_conversion",
    ], 1):
        cycle_rows.append({
            "branch_id": "AI", "state_family": family, "metric_name": family.replace("_", " "),
            "period": "FY2027Q2", "frequency": "quarterly", "value": str(100 + index),
            "unit": "unit", "ownership_or_location": "company or channel", "lead_lag_days": "30",
            "source_ids": "SRC0;SRC2", "data_series_ids": "D1;D2", "driver_node_ids": "ai_units",
            "as_of": "2026-07-18", "data_vintage_at": "2026-07-01", "applicability": "material",
            "status": "accepted", "notes": "synthetic state",
        })
    cycle_check_common = {
        "record_type": "equation_check", "branch_id": "AI", "state_family": "",
        "period": "FY2027Q2", "frequency": "quarterly", "source_ids": "SRC0;SRC2",
        "data_series_ids": "D1;D2", "driver_node_ids": "ai_units",
        "as_of": "2026-07-18", "data_vintage_at": "2026-07-01",
        "applicability": "material", "status": "accepted", "unit_conversion_factor": "1",
        "check_tolerance": "0.001", "check_residual": "0",
        "equation_status": "accepted", "notes": "synthetic recomputed equation",
    }
    cycle_rows.extend([
        {**cycle_check_common, "equation_id": "AI-channel-roll", "equation_type": "channel_inventory_roll",
         "metric_name": "sell-in stock-flow", "lhs_value": "410", "rhs_1_value": "400",
         "rhs_2_value": "10", "lhs_unit": "unit", "rhs_1_unit": "unit",
         "rhs_2_unit": "unit", "model_cell_or_formula": "Checks!B20"},
        {**cycle_check_common, "equation_id": "AI-company-roll", "equation_type": "company_inventory_roll",
         "metric_name": "shipment stock-flow", "lhs_value": "400", "rhs_1_value": "410",
         "rhs_2_value": "20", "rhs_3_value": "30", "lhs_unit": "unit",
         "rhs_1_unit": "unit", "rhs_2_unit": "unit", "rhs_3_unit": "unit",
         "model_cell_or_formula": "Checks!B21"},
        {**cycle_check_common, "equation_id": "AI-revenue-check", "equation_type": "revenue_recognition",
         "metric_name": "accepted quantity times price", "lhs_value": "20000", "rhs_1_value": "400",
         "rhs_2_value": "50", "lhs_unit": "USD", "rhs_1_unit": "unit",
         "rhs_2_unit": "USD/unit", "model_cell_or_formula": "Checks!B22"},
    ])
    write_scaffold_csv("operating_cycle_register.csv", cycle_rows)
    historical_rows = []
    for year, revenue in (("FY2024", 80.0), ("FY2025", 90.0), ("FY2026", 100.0)):
        historical_rows.extend([
            {
                "period": year, "period_type": "annual", "row_type": "consolidated",
                "reported_segment": "Total", "normalized_segment": "Total",
                "actual_or_forecast": "actual", "revenue": str(revenue),
                "cost": str(revenue * 0.6), "gross_profit": str(revenue * 0.4),
                "operating_profit": str(revenue * 0.2),
                "gaap_net_income_attributable": str(revenue * 0.12),
                "invested_capital": "75", "currency": "USD",
                "scope_basis": "continuing operations; consolidated attributable basis",
                "comparability_status": "comparable", "data_status": "reported",
                "latest_actual": "false", "perimeter_bridge": "none_no_change",
                "accounting_bridge": "none_no_change", "source_ids": "SRC0",
                "partition_id": "reported-segments", "partition_dimension": "reported_operating_segment",
                "partition_exhaustive": "true", "partition_mutually_exclusive": "true",
                "check_to_consolidated": "0", "segment_reconciliation_status": "reconciled",
                "status": "accepted", "notes": "synthetic complete history",
            },
            {
                "period": year, "period_type": "annual", "row_type": "segment",
                "reported_segment": "AI", "normalized_segment": "AI",
                "actual_or_forecast": "actual", "revenue": str(revenue), "currency": "USD",
                "scope_basis": "continuing operations; reported segment basis",
                "comparability_status": "comparable", "data_status": "reported",
                "latest_actual": "false", "perimeter_bridge": "none_no_change",
                "accounting_bridge": "none_no_change", "source_ids": "SRC0",
                "partition_id": "reported-segments", "partition_dimension": "reported_operating_segment",
                "status": "accepted", "notes": "single reported operating segment",
            },
        ])
    historical_rows.extend([
        {
            "period": "H1-2027", "period_type": "interim", "row_type": "consolidated",
            "reported_segment": "Total", "normalized_segment": "Total",
            "actual_or_forecast": "actual", "revenue": "55", "cost": "33",
            "gross_profit": "22", "operating_profit": "11",
            "gaap_net_income_attributable": "6.6", "invested_capital": "75", "currency": "USD",
            "scope_basis": "continuing operations; consolidated attributable basis",
            "comparability_status": "comparable", "data_status": "reported",
            "latest_actual": "true", "perimeter_bridge": "none_no_change",
            "accounting_bridge": "none_no_change", "source_ids": "SRC0",
            "partition_id": "reported-segments", "partition_dimension": "reported_operating_segment",
            "partition_exhaustive": "true", "partition_mutually_exclusive": "true",
            "check_to_consolidated": "0", "segment_reconciliation_status": "reconciled",
            "status": "accepted", "notes": "latest disclosed interim",
        },
        {
            "period": "H1-2027", "period_type": "interim", "row_type": "segment",
            "reported_segment": "AI", "normalized_segment": "AI",
            "actual_or_forecast": "actual", "revenue": "55", "currency": "USD",
            "scope_basis": "continuing operations; reported segment basis",
            "comparability_status": "comparable", "data_status": "reported",
            "latest_actual": "false", "perimeter_bridge": "none_no_change",
            "accounting_bridge": "none_no_change", "source_ids": "SRC0",
            "partition_id": "reported-segments", "partition_dimension": "reported_operating_segment",
            "status": "accepted", "notes": "single reported operating segment",
        },
        {
            "period": "FY2027E", "period_type": "first_forecast", "row_type": "consolidated",
            "reported_segment": "Total", "normalized_segment": "Total",
            "actual_or_forecast": "forecast", "revenue": "115", "cost": "69",
            "gross_profit": "46", "operating_profit": "23",
            "gaap_net_income_attributable": "13.8", "invested_capital": "75", "currency": "USD",
            "scope_basis": "continuing operations; consolidated attributable basis",
            "comparability_status": "comparable", "data_status": "derived",
            "latest_actual": "false", "perimeter_bridge": "none_no_change",
            "accounting_bridge": "none_no_change", "source_ids": "SRC0;SRC1",
            "segment_reconciliation_status": "not_applicable", "bridge_from_period": "H1-2027",
            "revenue_bridge_delta": "60", "cost_bridge_delta": "36",
            "gross_profit_bridge_delta": "24", "operating_profit_bridge_delta": "12",
            "gaap_net_income_attributable_bridge_delta": "7.2",
            "forecast_bridge": "H2 unit, ASP and cash-cost nodes bridge the latest interim",
            "driver_node_ids": "ai_units;ai_asp;cash_cost", "status": "accepted",
            "notes": "synthetic first forecast bridge",
        },
    ])
    write_scaffold_csv("historical_segment_bridge.csv", historical_rows)
    frozen_names = (
        "source_manifest.json",
        "source_independence_map.csv",
        "forward_signal_cards.csv",
        "model_graph.json",
        "scenario_set.json",
        "data_series_register.csv",
        "material_assumption_support.csv",
        "claim_ledger.jsonl",
    )
    frozen = {
        name: "sha256:" + hashlib.sha256((workspace / name).read_bytes()).hexdigest()
        for name in frozen_names
    }
    (workspace / "research_quality_review.json").write_text(
        json.dumps({
            "schema_version": "research-quality-review/v1",
            "review_id": "synthetic-independent-review",
            "reviewed_at": "2026-07-18T20:00:00Z",
            "builder_id": "synthetic-builder",
            "reviewer_id": "synthetic-independent-reviewer",
            "independent_of_builder": True,
            "orchestration_receipt": {
                "assurance_boundary": "orchestration_receipt_only_not_cryptographic_identity",
                "receipt_id": "orchestration-receipt://package-self-test",
                "orchestrator": "package-self-test",
                "reviewer_session_id": "session:synthetic-reviewer",
                "reviewer_task_id": "task:synthetic-research-review",
                "builder_session_id": "session:synthetic-builder",
                "frozen_inputs_delivered_at": "2026-07-18T19:50:00Z",
                "review_started_at": "2026-07-18T19:52:00Z",
                "initial_conclusion_at": "2026-07-18T19:58:00Z",
                "review_completed_at": "2026-07-18T20:00:00Z",
                "receipt_issued_at": "2026-07-18T20:01:00Z",
                "builder_rebuttal": {"status": "not_provided", "provided_at": None},
            },
            "frozen_artifacts": frozen,
            "principal_contradiction": {
                "carrier_node_ids": ["ai_units", "ai_asp"],
                "falsification_node_ids": ["asp_break"],
                "rival_hypothesis": "Qualified competing supply removes price persistence.",
                "judgment": "adequate",
                "reasoning": "The fixture supplies definition-compatible demand and price observations and a named rival.",
                "source_ids": ["SRC0", "SRC1"],
            },
            "claim_authority_judgments": [{
                "claim_id": "C2",
                "reviewed_source_ids": ["SRC5"],
                "reviewed_source_epistemic_classes": {
                    "SRC5": "expert_or_analyst_opinion"
                },
                "reviewed_source_origin_record_kinds": {
                    "SRC5": "expert_or_analyst_interpretation"
                },
                "reviewed_observation_bindings": {},
                "authority_sufficiency": "adequate",
                "permitted_use": "scenario_only",
                "rationale": (
                    "Independent reviewer accepts only the bounded rival-state use."
                ),
            }],
            "material_judgments": [],
            "overall": {
                "research_sufficiency": "adequate",
                "readiness_cap": "research-grade",
                "rationale": "Synthetic contract fixture only; the frozen lineage is internally complete.",
                "unresolved_material_disagreements": [],
            },
        }, indent=2) + "\n",
        encoding="utf-8",
    )
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
    for directory in (
        "broad", "equipment", "marvell", "aws", "netflix", "nvidia",
        "forward-evidence", "amd-intel",
    ):
        metrics = json.loads((td / directory / "metrics.json").read_text(encoding="utf-8"))
        diagnostic = json.loads(
            (td / directory / "diagnostics.json").read_text(encoding="utf-8")
        )
        if "gate_results" in metrics:
            fail(f"{directory}: legacy threshold results cannot be a metrics release gate")
        if metrics.get("legacy_threshold_diagnostics") != {
            "artifact": "diagnostics.json",
            "diagnostic_only": True,
            "promotion_authority": "none",
        }:
            fail(f"{directory}: metrics must link the non-promotion diagnostic artifact")
        if (
            diagnostic.get("schema_version") != "legacy-backtest-diagnostics/v1"
            or diagnostic.get("diagnostic_only") is not True
            or diagnostic.get("promotion_authority") != "none"
            or not isinstance(diagnostic.get("threshold_observations"), dict)
        ):
            fail(f"{directory}: malformed legacy threshold diagnostic artifact")


def live_functional_battery(skill: Path, td: Path) -> None:
    for script in (skill / "scripts").glob("*.py"):
        py_compile.compile(str(script), doraise=True)
    profile = json.loads((skill / "assets" / "profile.json").read_text(encoding="utf-8"))
    if "allowed_modes" in profile or "source_cutoff_modes" in profile:
        fail("single-purpose production profile must not define mode routing")
    if (skill / "scripts" / "validate_time_boundary.py").exists():
        fail("historical time-boundary validator must not ship in the live skill")
    if (skill / "assets" / "templates" / "mode_config_template.json").exists():
        fail("single-purpose production must not ship duplicate mode configuration")


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

    profile_path = skill / "assets" / "profile.json"
    if not profile_path.is_file():
        fail(f"missing runtime profile {profile_path}")
    runtime_profile = json.loads(profile_path.read_text(encoding="utf-8"))
    if runtime_profile.get("profile") != profile:
        fail(
            f"runtime profile {runtime_profile.get('profile')!r} does not match "
            f"SKILL.md profile {profile!r}"
        )
    runtime_scripts = runtime_profile.get("runtime_scripts")
    if (
        not isinstance(runtime_scripts, list)
        or not runtime_scripts
        or any(not isinstance(item, str) or not item.endswith(".py") for item in runtime_scripts)
        or len(runtime_scripts) != len(set(runtime_scripts))
    ):
        fail("profile.runtime_scripts must be a unique non-empty .py list")

    required = list(TRAINER_REQUIRED if profile == "trainer" else LIVE_REQUIRED)
    required.extend(f"scripts/{name}" for name in runtime_scripts)
    for rel in required:
        path = skill / rel
        if not path.exists() or (
            path.is_file()
            and path.stat().st_size == 0
            and rel not in INTENTIONALLY_EMPTY_REQUIRED_FILES
        ):
            fail(f"missing or empty {path}")

    if profile == "live":
        present = [rel for rel in LIVE_FORBIDDEN if (skill / rel).exists()]
        if present:
            fail("trainer-only material must not ship in the live skill: " + ", ".join(present))

    skill_source = (skill / "SKILL.md").read_text(encoding="utf-8")
    text = skill_source.lower()
    missing_mentions = sorted(
        path for path in set(PATH_MENTION_RE.findall(skill_source))
        if not (skill / path).exists()
    )
    if missing_mentions:
        fail("SKILL.md references missing paths: " + ", ".join(missing_mentions))
    if profile == "live":
        for needle in LIVE_SKILL_ABSENT:
            if needle in text:
                fail(f"live SKILL.md must not contain trainer token: {needle}")

    prompt = (skill / "agents/openai.yaml").read_text(encoding="utf-8").lower()
    if profile == "live":
        for needle in LIVE_PROMPT_ABSENT:
            if needle in prompt:
                fail(f"live openai prompt must not contain trainer token: {needle}")

    method = json.loads((skill / "assets" / "method_system.json").read_text(encoding="utf-8"))
    assurance = method.get("assurance_philosophy") or {}
    construction = method.get("construction_philosophy") or {}
    if "improvement_objective" in method:
        fail("production method must not own the trainer improvement objective")
    if profile == "trainer":
        overlay = json.loads(
            (skill / "assets" / "training_method_overlay.json").read_text(encoding="utf-8")
        )
        objective = overlay.get("improvement_objective") or {}
        if objective.get("not_a_scalar_optimization") is not True:
            fail("training overlay must keep forecasting quality outside scalar optimization")
        if objective.get("metrics_are") != "diagnostic_evidence_not_the_objective":
            fail("training overlay must treat metrics as diagnostic evidence")
    if construction.get("canonical_sop") != "references/research-sop.md":
        fail("method system must name the single canonical SOP")
    if assurance.get("tests_are") != "orthogonal_views_not_a_completeness_score":
        fail("method system must define tests as orthogonal views")
    stages = method.get("stages") or []
    stage_ids = [stage.get("id") for stage in stages if isinstance(stage, dict)]
    if not stage_ids or len(stage_ids) != len(set(stage_ids)):
        fail("method system stage IDs must be non-empty and unique")
    if stage_ids[-1:] != ["publish_monitor_version"]:
        fail("production method must end with publish_monitor_version")

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
