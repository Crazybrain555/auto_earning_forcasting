#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import datetime as dt
import datetime as dtmod
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
    "buy_discipline": ["recommended buy", "buy price", "买入价", "margin of safety", "安全边际", "买入纪律"],
    "arithmetic_check": ["arithmetic", "consistency check", "一致性检查", "勾稽", "自洽检查"],
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


def workbook_formula_stats(path: Path) -> dict:
    """Count real formulas and cached error values without external deps.

    A 'formula-driven workbook' with zero <f> elements is hardcoded output;
    #REF!/#NAME? cached values mean broken references shipped."""
    formulas = 0
    errors = {"#REF!": 0, "#NAME?": 0, "#DIV/0!": 0, "#VALUE!": 0}
    with zipfile.ZipFile(path) as zf:
        for name in zf.namelist():
            if not name.startswith("xl/worksheets/"):
                continue
            data = zf.read(name)
            formulas += len(re.findall(rb"<f[ >]", data))
            for token in errors:
                errors[token] += data.count(token.encode())
    return {"formulas": formulas, "errors": errors}


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
            # Canonical outputs contract: every horizon must use canonical keys.
            # Dialect keys (revenue_M / revenue_base / revenue_p50 / nested scenario
            # dicts / non_gaap_eps_*) are a delivery failure - downstream consumers
            # (dashboard, scorer, exports) read canonical keys only.
            relaxed_outputs = bool(manifest.get("outputs_canonical_relaxed", False))
            outputs = snap.get("outputs") or {}
            def _num(value):
                return isinstance(value, (int, float)) and not isinstance(value, bool)
            for period_key, needs_range in (("year_1", False), ("year_2", True), ("year_3_distribution", True)):
                out = outputs.get(period_key)
                label = f"snapshot:canonical-{period_key}"
                if not isinstance(out, dict):
                    fail_record(checks, label, "period missing from outputs", "error" if args.strict else "warning")
                    continue
                has_numbers = any(
                    _num(value) or (isinstance(value, dict) and any(_num(x) for x in value.values()))
                    for key, value in out.items() if key not in ("period", "point_evaluable"))
                canonical = _num(out.get("revenue_point")) and (_num(out.get("profit_point")) or _num(out.get("eps_point")))
                if needs_range and canonical:
                    canonical = (_num(out.get("revenue_low")) and _num(out.get("revenue_high")) and
                                 ((_num(out.get("profit_low")) and _num(out.get("profit_high"))) or
                                  (_num(out.get("eps_low")) and _num(out.get("eps_high")))))
                if canonical:
                    pass_record(checks, label)
                elif has_numbers:
                    fail_record(checks, label,
                                "dialect output keys - canonical keys required: revenue_point/low/high plus "
                                "profit_point(/low/high, GAAP net income $M) or eps_point(/low/high); "
                                "point = Base scenario or p50, low/high = Bear~Bull or p10~p90")
                elif relaxed_outputs:
                    pass_record(checks, label)
                else:
                    fail_record(checks, label, "outputs not populated with canonical keys", "error" if args.strict else "warning")
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
        # formula-driven enforcement + broken-reference scan
        try:
            stats = workbook_formula_stats(model_path)
            formula_min = int(manifest.get("workbook_formula_min", 30))
            if stats["formulas"] >= formula_min:
                pass_record(checks, "workbook:formula-driven", f"{stats['formulas']} formulas")
            else:
                fail_record(checks, "workbook:formula-driven",
                            f"only {stats['formulas']} formulas (< {formula_min}) - a hardcoded-values workbook is not a formula-driven model",
                            "error" if args.strict else "warning")
            broken = stats["errors"]["#REF!"] + stats["errors"]["#NAME?"]
            if broken:
                fail_record(checks, "workbook:broken-references", f"#REF!/#NAME? occurrences: {broken}")
            else:
                pass_record(checks, "workbook:broken-references")
            soft = stats["errors"]["#DIV/0!"] + stats["errors"]["#VALUE!"]
            if soft:
                fail_record(checks, "workbook:error-values", f"#DIV/0!/#VALUE! occurrences: {soft}", "warning")
        except Exception as exc:
            fail_record(checks, "workbook:formula-scan", str(exc), "warning")

    # Red-team findings must bind the numbers: open P0/P1 findings are only
    # acceptable when the run's readiness target is capped at screen-grade.
    if red_path.exists():
        open_p1 = []
        for line in red_path.read_text(encoding="utf-8").splitlines():
            if not line.strip().startswith("|") or "RT-" not in line:
                continue
            cells = [c.strip() for c in line.strip().strip("|").split("|")]
            if len(cells) < 3:
                continue
            severity = next((c.upper() for c in cells if c.upper() in {"P0", "P1"}), None)
            status = cells[-1].lower()
            if severity and status not in {"closed", "resolved", "mitigated"}:
                open_p1.append(cells[0])
        if open_p1:
            readiness = str(manifest.get("readiness_target", "")).lower()
            if readiness in {"screen-grade", "not-decision-ready"}:
                pass_record(checks, "red-team:open-findings-capped", ",".join(open_p1))
            else:
                fail_record(checks, "red-team:open-findings-bind",
                            f"open P0/P1 findings {','.join(open_p1)} require resolution or readiness_target capped at screen-grade (current: {readiness or 'unset'})",
                            "error" if args.strict else "warning")

    # Cross-artifact reconciliation: headline snapshot numbers must appear in the report.
    if snap_path.exists() and report_path.exists():
        try:
            snap_obj = json.loads(snap_path.read_text(encoding="utf-8"))
        except Exception:
            snap_obj = {}
        report_text_full = report_path.read_text(encoding="utf-8")
        def number_in_report(value, label):
            if not isinstance(value, (int, float)):
                return
            forms = {f"{value:.2f}", f"{value:.1f}", f"{value:.0f}", f"{int(value):,}"}
            if any(f in report_text_full for f in forms):
                pass_record(checks, f"reconcile:{label}")
            else:
                fail_record(checks, f"reconcile:{label}",
                            f"snapshot {label}={value} does not appear in report.md - artifacts disagree",
                            "error" if args.strict else "warning")
        vs = snap_obj.get("valuation_summary") or {}
        number_in_report((vs.get("fair_value") or {}).get("base"), "fair-value-base")
        y1 = (snap_obj.get("outputs") or {}).get("year_1") or {}
        number_in_report(y1.get("revenue_point"), "fy1-revenue-point")

    # Source date hygiene: every source needs a parseable published_at at or
    # before as_of (end of day). Live runs use as_of = today, so this catches
    # future-dated and undated sourcing there too, not only in training.
    if source_path.exists():
        try:
            cutoff_raw = str(manifest.get("as_of", "")).strip()
            cutoff = None
            if cutoff_raw:
                text = cutoff_raw if len(cutoff_raw) > 10 else cutoff_raw + "T23:59:59+00:00"
                if text.endswith("Z"):
                    text = text[:-1] + "+00:00"
                cutoff = dtmod.datetime.fromisoformat(text)
                if cutoff.tzinfo is None:
                    cutoff = cutoff.replace(tzinfo=dtmod.timezone.utc)
            undated, future = [], []
            for s in json.loads(source_path.read_text(encoding="utf-8")).get("sources", []):
                sid = s.get("source_id", "UNKNOWN")
                raw = str(s.get("published_at", "") or "").strip()
                if not raw:
                    undated.append(sid)
                    continue
                try:
                    text = raw if len(raw) > 10 else raw + "T23:59:59+00:00"
                    if text.endswith("Z"):
                        text = text[:-1] + "+00:00"
                    published = dtmod.datetime.fromisoformat(text)
                    if published.tzinfo is None:
                        published = published.replace(tzinfo=dtmod.timezone.utc)
                except Exception:
                    undated.append(sid)
                    continue
                if cutoff is not None and published > cutoff:
                    future.append(sid)
            if future:
                fail_record(checks, "sources:published-before-as-of",
                            "sources dated after as_of " + cutoff_raw + ": " + ",".join(future[:8]),
                            "error" if args.strict else "warning")
            else:
                pass_record(checks, "sources:published-before-as-of")
            if undated:
                fail_record(checks, "sources:published-at-known",
                            "sources with missing/unparseable published_at: " + ",".join(undated[:8]),
                            "warning")
            else:
                pass_record(checks, "sources:published-at-known")
        except Exception:
            pass

    # Provenance honesty: hashes are either real or explicitly absent - never invented.
    if source_path.exists():
        try:
            fake = []
            for s in json.loads(source_path.read_text(encoding="utf-8")).get("sources", []):
                h = str(s.get("content_hash", "") or "")
                if h and not (re.fullmatch(r"sha256:[0-9a-f]{64}", h) or h.startswith("unhashed:")):
                    fake.append(s.get("source_id", "UNKNOWN"))
            if fake:
                fail_record(checks, "sources:content-hash-honesty",
                            "content_hash must be a real sha256:<64hex> or 'unhashed:<reason>' - fabricated-looking hashes: " + ",".join(fake[:8]),
                            "error" if args.strict else "warning")
            else:
                pass_record(checks, "sources:content-hash-honesty")
        except Exception:
            pass

    # The recommended buy price must be derived in the report, not only asserted in the snapshot.
    if snap_path.exists() and report_path.exists():
        try:
            buy = (json.loads(snap_path.read_text(encoding="utf-8")).get("valuation_summary") or {}).get("recommended_buy_price")
        except Exception:
            buy = None
        if isinstance(buy, (int, float)):
            report_text = report_path.read_text(encoding="utf-8")
            forms = {f"{buy:.2f}", f"{buy:.1f}", f"{buy:.0f}", f"{int(buy):,}"}
            if any(f in report_text for f in forms):
                pass_record(checks, "valuation:buy-price-derived")
            else:
                fail_record(checks, "valuation:buy-price-derived",
                            f"recommended_buy_price {buy} appears in the snapshot but nowhere in report.md - derive it (margin-of-safety logic) in the report",
                            "error" if args.strict else "warning")

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
