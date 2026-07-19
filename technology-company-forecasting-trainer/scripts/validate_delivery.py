#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import datetime as dt
import json
import re
import sys
import subprocess
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET


REQUIRED_FILES = [
    "run_manifest.json",
    "source_manifest.json",
    "assumption_register.csv",
    "red_team.md",
    "report.md",
    "forecast_snapshot.json",
    "delivery_quality_rubric.json",
    "forward_signal_cards.csv",
    "historical_query_log.csv",
    "source_independence_map.csv",
    "research_coverage_matrix.csv",
    "company_quality_moat_register.csv",
    "technology_commercialization_register.csv",
    "product_customer_driver_schedule.csv",
    "material_assumption_support.csv",
    "mode_config.json",
    "training_state.json",
]

SHEET_CONCEPTS = {
    "summary": ["summary", "摘要", "封面"],
    "sources": ["source", "evidence", "证据"],
    "history": ["history", "historical", "历史", "基期"],
    "quarterly": ["quarter", "季度"],
    "drivers": ["driver", "assumption", "驱动", "假设"],
    "financials": ["financial", "p&l", "income", "损益", "经营模型"],
    "cash": ["cash", "capital", "现金", "资本"],
    "scenarios": ["scenario", "情景"],
    "valuation": ["valuation", "估值", "implicit", "隐含"],
    "monitoring": ["monitor", "trigger", "quality", "监测", "质量"],
    "manifest": ["manifest", "交付清单", "run"],
}

REPORT_SECTION_GROUPS = {
    "cutoff": ["information cutoff", "信息截面", "截止"],
    "conclusion": ["conclusion", "结论"],
    "base": ["base forecast", "base财务", "base预测", "基准预测"],
    "drivers": ["drivers", "驱动", "客户", "产品"],
    "forward_evidence": ["forward evidence", "前瞻证据", "研究综合", "投资者交流", "论文", "专家"],
    "cash": ["cash flow", "现金流", "资本"],
    "scenarios": ["scenario", "情景", "bear", "bull"],
    "valuation": ["valuation", "估值"],
    "reverse": ["reverse", "隐含", "反向"],
    "monitoring": ["monitor", "触发", "待验证"],
    "limitations": ["limitation", "限制", "human-required", "可信度"],
}


def parse_datetime(value: str) -> dt.datetime:
    value = value.strip()
    if value.endswith("Z"):
        value = value[:-1] + "+00:00"
    parsed = dt.datetime.fromisoformat(value)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=dt.timezone.utc)
    return parsed.astimezone(dt.timezone.utc)


def workbook_sheet_names(path: Path) -> list[str]:
    with zipfile.ZipFile(path) as zf:
        xml = zf.read("xl/workbook.xml")
    root = ET.fromstring(xml)
    ns = {"m": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
    return [node.attrib.get("name", "") for node in root.findall(".//m:sheets/m:sheet", ns)]


def contains_any(text: str, needles: list[str]) -> bool:
    lowered = text.lower()
    return any(n.lower() in lowered for n in needles)


def fail_record(checks: list[dict], name: str, detail: str, severity: str = "error") -> None:
    checks.append({"check": name, "passed": False, "severity": severity, "detail": detail})


def pass_record(checks: list[dict], name: str, detail: str = "") -> None:
    checks.append({"check": name, "passed": True, "severity": "info", "detail": detail})


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate a full-company forecast delivery workspace.")
    parser.add_argument("--workspace", required=True)
    parser.add_argument("--strict", action="store_true")
    args = parser.parse_args()

    workspace = Path(args.workspace).resolve()
    checks: list[dict] = []
    if not workspace.exists():
        print(json.dumps({"passed": False, "error": f"workspace missing: {workspace}"}, indent=2))
        return 2

    for name in REQUIRED_FILES:
        path = workspace / name
        if path.exists() and path.stat().st_size > 0:
            pass_record(checks, f"file:{name}")
        else:
            fail_record(checks, f"file:{name}", "missing or empty")

    model_candidates = [workspace / "model" / "model.xlsx", workspace / "model.xlsx"]
    model_path = next((p for p in model_candidates if p.exists()), None)
    if model_path:
        pass_record(checks, "file:model.xlsx", str(model_path))
    else:
        fail_record(checks, "file:model.xlsx", "expected model/model.xlsx or model.xlsx")

    # Manifest
    manifest_path = workspace / "run_manifest.json"
    manifest = {}
    if manifest_path.exists():
        try:
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            required = ["run_id","entity","security","as_of","purpose","fiscal_calendar","currency","accounting_basis","horizons","selected_mechanisms","readiness_target","phase_status"]
            missing = [k for k in required if not manifest.get(k)]
            if missing:
                fail_record(checks, "manifest:required-fields", ", ".join(missing))
            else:
                pass_record(checks, "manifest:required-fields")
            phases = manifest.get("phase_status", {})
            incomplete = [k for k,v in phases.items() if str(v).lower() not in {"complete","completed","done","pass","passed"}]
            if incomplete:
                fail_record(checks, "manifest:phase-gates", "incomplete: " + ", ".join(incomplete), "error" if args.strict else "warning")
            else:
                pass_record(checks, "manifest:phase-gates")
        except Exception as exc:
            fail_record(checks, "manifest:json", str(exc))

    # Source pack
    source_path = workspace / "source_manifest.json"
    if source_path.exists():
        try:
            src = json.loads(source_path.read_text(encoding="utf-8"))
            sources = src.get("sources", [])
            official = [s for s in sources if s.get("evidence_tier") in {"E0","E1"}]
            if len(official) >= 6:
                pass_record(checks, "sources:official-count", str(len(official)))
            else:
                fail_record(checks, "sources:official-count", f"{len(official)} < 6", "error" if args.strict else "warning")
            types = {str(s.get("source_type", "")).lower() for s in official}
            if any("filing" in t or t in {"10-k","10-q","20-f","annual-report"} for t in types):
                pass_record(checks, "sources:filing")
            else:
                fail_record(checks, "sources:filing", "no official filing source")
            if any("earning" in t or "results" in t for t in types):
                pass_record(checks, "sources:earnings")
            else:
                fail_record(checks, "sources:earnings", "no current earnings source")
            cutoff = parse_datetime(src.get("as_of") or manifest.get("as_of"))
            future = []
            required_fields = ["source_id","source_type","publisher","published_at","retrieved_at","period_scope","evidence_tier","location","claim_or_fact","allowed_use"]
            incomplete_sources = []
            for s in sources:
                miss = [k for k in required_fields if not s.get(k)]
                if miss:
                    incomplete_sources.append(f"{s.get('source_id','UNKNOWN')}:{'/'.join(miss)}")
                try:
                    if parse_datetime(s["published_at"]) > cutoff:
                        future.append(s.get("source_id","UNKNOWN"))
                except Exception:
                    incomplete_sources.append(f"{s.get('source_id','UNKNOWN')}:invalid-date")
            if incomplete_sources:
                fail_record(checks, "sources:required-fields", "; ".join(incomplete_sources[:10]))
            else:
                pass_record(checks, "sources:required-fields")
            if future:
                fail_record(checks, "sources:cutoff", "future sources: " + ", ".join(future))
            else:
                pass_record(checks, "sources:cutoff")
        except Exception as exc:
            fail_record(checks, "sources:json", str(exc))


    # Executable mode and time-boundary validation
    time_validator = Path(__file__).resolve().parent / "validate_time_boundary.py"
    if (workspace / "mode_config.json").exists():
        result = subprocess.run([sys.executable, str(time_validator), "--workspace", str(workspace), "--strict"], capture_output=True, text=True)
        if result.returncode == 0:
            pass_record(checks, "time-boundary:workspace", result.stdout.strip())
        else:
            fail_record(checks, "time-boundary:workspace", (result.stdout + result.stderr).strip())

    # Forward-evidence workspace validator
    forward_validator = Path(__file__).resolve().parent / "validate_forward_evidence_workspace.py"
    if manifest.get("forward_evidence_required", True):
        result = subprocess.run([sys.executable, str(forward_validator), "--workspace", str(workspace), "--strict"], capture_output=True, text=True)
        if result.returncode == 0:
            pass_record(checks, "forward-evidence:workspace", result.stdout.strip())
        else:
            fail_record(checks, "forward-evidence:workspace", (result.stdout + result.stderr).strip())

    # Research-depth and gold-standard parity validator
    research_validator = Path(__file__).resolve().parent / "validate_research_completeness.py"
    if manifest.get("research_completeness_required", True):
        result = subprocess.run([sys.executable, str(research_validator), "--workspace", str(workspace), "--strict"], capture_output=True, text=True)
        if result.returncode == 0:
            pass_record(checks, "research-completeness:workspace", result.stdout.strip())
        else:
            fail_record(checks, "research-completeness:workspace", (result.stdout + result.stderr).strip())

    # Assumption register
    assumption_path = workspace / "assumption_register.csv"
    if assumption_path.exists():
        try:
            with assumption_path.open(encoding="utf-8-sig", newline="") as f:
                reader = csv.DictReader(f)
                fields = set(reader.fieldnames or [])
                required = {"assumption_id","entity","segment","mechanism","metric","period","scenario","value","unit","evidence_tier","source_ids","confidence","breakpoint","next_evidence","owner"}
                missing = sorted(required-fields)
                if missing:
                    fail_record(checks, "assumptions:headers", ", ".join(missing))
                else:
                    pass_record(checks, "assumptions:headers")
                rows = list(reader)
                if rows:
                    pass_record(checks, "assumptions:rows", str(len(rows)))
                else:
                    fail_record(checks, "assumptions:rows", "no assumptions recorded", "error" if args.strict else "warning")
        except Exception as exc:
            fail_record(checks, "assumptions:csv", str(exc))

    # Report
    report_path = workspace / "report.md"
    if report_path.exists():
        text = report_path.read_text(encoding="utf-8")
        for key, aliases in REPORT_SECTION_GROUPS.items():
            if contains_any(text, aliases):
                pass_record(checks, f"report:{key}")
            else:
                fail_record(checks, f"report:{key}", "missing required section")
        if len(text.split()) >= 500 or len(text) >= 5000:
            pass_record(checks, "report:depth", f"{len(text)} chars")
        else:
            fail_record(checks, "report:depth", f"only {len(text)} chars", "error" if args.strict else "warning")

    # Red team
    red_path = workspace / "red_team.md"
    if red_path.exists():
        text = red_path.read_text(encoding="utf-8")
        finding_ids = set(re.findall(r"RT-\d{3}", text))
        table_findings = [line for line in text.splitlines() if line.startswith("|") and "RT-" in line]
        count = max(len(finding_ids), len(table_findings))
        if count >= 5:
            pass_record(checks, "red-team:findings", str(count))
        else:
            fail_record(checks, "red-team:findings", f"{count} < 5", "error" if args.strict else "warning")
        if contains_any(text, ["double count","double-count","双算","重复计算"]):
            pass_record(checks, "red-team:double-count")
        else:
            fail_record(checks, "red-team:double-count", "missing double-count challenge")
        if contains_any(text, ["valuation","估值","terminal","normalization","正常化"]):
            pass_record(checks, "red-team:valuation")
        else:
            fail_record(checks, "red-team:valuation", "missing valuation/normalization challenge")

    # Snapshot
    snap_path = workspace / "forecast_snapshot.json"
    if snap_path.exists():
        try:
            snap = json.loads(snap_path.read_text(encoding="utf-8"))
            required = ["forecast_id","as_of","model_version","source_pack_hash","mechanism_weights","scenario_probabilities","outputs","breakpoints","human_required","confidence_and_limits"]
            missing = [k for k in required if k not in snap]
            if missing:
                fail_record(checks, "snapshot:fields", ", ".join(missing))
            else:
                pass_record(checks, "snapshot:fields")
            weights = snap.get("mechanism_weights", {})
            if weights and abs(sum(float(v) for v in weights.values())-1.0) <= 0.0001:
                pass_record(checks, "snapshot:mechanism-weights")
            else:
                fail_record(checks, "snapshot:mechanism-weights", "weights must sum to 1")
            probs = snap.get("scenario_probabilities", {})
            if probs and abs(sum(float(v) for v in probs.values())-1.0) <= 0.0001:
                pass_record(checks, "snapshot:scenario-probabilities")
            else:
                fail_record(checks, "snapshot:scenario-probabilities", "probabilities must sum to 1")
        except Exception as exc:
            fail_record(checks, "snapshot:json", str(exc))

    # Workbook conceptual sheet validation
    if model_path:
        try:
            names = workbook_sheet_names(model_path)
            for concept, aliases in SHEET_CONCEPTS.items():
                if any(contains_any(name, aliases) for name in names):
                    pass_record(checks, f"workbook:{concept}")
                else:
                    fail_record(checks, f"workbook:{concept}", f"sheets={names}")
        except Exception as exc:
            fail_record(checks, "workbook:read", str(exc))

    errors = [c for c in checks if not c["passed"] and c["severity"] == "error"]
    warnings = [c for c in checks if not c["passed"] and c["severity"] == "warning"]
    passed = not errors
    result = {"workspace": str(workspace), "passed": passed, "strict": args.strict, "errors": len(errors), "warnings": len(warnings), "checks": checks}
    output = workspace / "delivery_validation.json"
    output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if passed else 2


if __name__ == "__main__":
    raise SystemExit(main())
