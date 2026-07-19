#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
import re
from pathlib import Path

REQUIRED_FILES = [
    "research_coverage_matrix.csv",
    "company_quality_moat_register.csv",
    "technology_commercialization_register.csv",
    "product_customer_driver_schedule.csv",
    "material_assumption_support.csv",
]

REQUIRED_TOPICS = {
    "historical_financials_and_vintage": "critical",
    "current_quarter_and_guidance": "critical",
    "business_segments_products_revenue_units": "critical",
    "customers_channels_and_demand": "critical",
    "competitors_and_market_structure": "high",
    "supply_capacity_delivery_inventory_cost": "critical",
    "technology_roadmap_and_product_stages": "high",
    "papers_standards_patents_failure_boundaries": "high",
    "management_governance_capital_allocation": "high",
    "company_quality_and_moat": "high",
    "balance_sheet_cash_and_economic_capital": "critical",
    "industry_policy_and_macro": "high",
    "news_and_event_timeline": "medium",
    "valuation_and_reverse_implied": "high",
}

QUALITY_DIMENSIONS = {
    "management_execution",
    "governance_and_incentives",
    "capital_allocation_and_mna",
    "rd_productivity_and_cadence",
    "technology_ip_and_standards",
    "customer_stickiness_switching_costs",
    "channel_distribution_advantage_and_risk",
    "cost_scale_manufacturing_or_data_advantage",
    "competitive_response_and_substitution",
    "balance_sheet_and_counterparty_resilience",
}

ALLOWED_COVERAGE_STATUS = {
    "accepted",
    "partial_human_required",
    "searched_no_qualified_source",
    "not_material_with_reason",
    "unavailable_due_to_access_or_compliance",
}

SUBSTANTIAL_DEPTH = {"full_document", "substantial_excerpt"}
UNSUPPORTED = {"analyst_only", "human_required"}


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def truthy(v: object) -> bool:
    return str(v).strip().lower() in {"true", "1", "yes", "y"}


def as_float(v: object, default: float = 0.0) -> float:
    try:
        return float(str(v).strip())
    except Exception:
        return default


def count_words(text: str) -> int:
    return len(re.findall(r"\b\w+\b", text, flags=re.UNICODE))


def resolve_source_path(workspace: Path, location: str) -> Path | None:
    if not location or "://" in location:
        return None
    candidates = [workspace / location, workspace.parent / location, Path(location)]
    for p in candidates:
        if p.exists() and p.is_file():
            return p
    return None


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate research depth and gold-standard analytical coverage.")
    parser.add_argument("--workspace", required=True)
    parser.add_argument("--strict", action="store_true")
    args = parser.parse_args()

    workspace = Path(args.workspace).resolve()
    errors: list[str] = []
    warnings: list[str] = []
    metrics: dict[str, object] = {}

    manifest = {}
    source_manifest = {}
    snapshot = {}
    for name, target in [("run_manifest.json", "manifest"), ("source_manifest.json", "sources"), ("forecast_snapshot.json", "snapshot")]:
        p = workspace / name
        if not p.exists():
            errors.append(f"missing {name}")
            continue
        try:
            obj = json.loads(p.read_text(encoding="utf-8"))
            if target == "manifest": manifest = obj
            elif target == "sources": source_manifest = obj
            else: snapshot = obj
        except Exception as exc:
            errors.append(f"invalid {name}: {exc}")

    for name in REQUIRED_FILES:
        p = workspace / name
        if not p.exists() or p.stat().st_size == 0:
            errors.append(f"missing research artifact {name}")

    # Source-depth validation.
    sources = source_manifest.get("sources", []) if isinstance(source_manifest, dict) else []
    accepted = [s for s in sources if str(s.get("decision_status", "accepted")).lower() not in {"rejected", "not_material"}]
    total_words = 0
    substantial_sources = 0
    substantial_official = 0
    filing_years: set[str] = set()
    dialogue_sources = 0
    product_technical_sources = 0
    management_sources = 0
    missing_depth_fields: list[str] = []

    for s in accepted:
        sid = str(s.get("source_id", "UNKNOWN"))
        depth = str(s.get("document_depth", "")).strip().lower()
        word_count = int(as_float(s.get("word_count"), 0))
        anchor_count = int(as_float(s.get("anchor_count"), 0))
        coverage_topics = s.get("coverage_topics")
        original_available = s.get("original_source_available")

        local = resolve_source_path(workspace, str(s.get("location", "")))
        if local:
            try:
                text = local.read_text(encoding="utf-8", errors="ignore")
                measured = count_words(text)
                word_count = max(word_count, measured)
            except Exception:
                pass

        if not depth or not coverage_topics or anchor_count <= 0 or original_available in {None, ""}:
            missing_depth_fields.append(sid)
        total_words += max(0, word_count)
        if depth in SUBSTANTIAL_DEPTH and word_count >= 400 and anchor_count >= 3:
            substantial_sources += 1
            if str(s.get("evidence_tier", "")) in {"E0", "E1"}:
                substantial_official += 1
        stype = str(s.get("source_type", "")).lower()
        if depth in SUBSTANTIAL_DEPTH and ("filing" in stype or "annual" in stype or stype in {"10-k", "20-f"}):
            period = str(s.get("period_scope", "")).strip()
            if period:
                filing_years.add(period)
        if depth in SUBSTANTIAL_DEPTH and any(k in stype for k in ["call", "dialogue", "investor", "transcript", "conference", "q&a"]):
            dialogue_sources += 1
        topics = str(coverage_topics or "").lower()
        if any(k in topics for k in ["product", "technology", "patent", "standard", "roadmap"]):
            product_technical_sources += 1
        if any(k in topics for k in ["management", "governance", "capital allocation", "incentive"]):
            management_sources += 1

    metrics.update({
        "accepted_sources": len(accepted),
        "accepted_source_words": total_words,
        "substantial_sources": substantial_sources,
        "substantial_official_sources": substantial_official,
        "historical_filing_periods": len(filing_years),
        "substantial_dialogue_sources": dialogue_sources,
        "product_technical_sources": product_technical_sources,
        "management_governance_sources": management_sources,
    })

    if missing_depth_fields:
        errors.append("source depth metadata missing for: " + ", ".join(missing_depth_fields[:12]))
    if len(filing_years) < 3:
        errors.append(f"substantial historical filing coverage {len(filing_years)} < 3 periods")
    if substantial_official < 5:
        errors.append(f"substantial official sources {substantial_official} < 5")
    if substantial_sources < 8:
        errors.append(f"full/substantial accepted sources {substantial_sources} < 8")
    if total_words < 12000:
        errors.append(f"accepted research corpus {total_words} words < 12000 minimum")
    if dialogue_sources < 1:
        errors.append("no substantial formal investor-dialogue/transcript source")
    if product_technical_sources < 2:
        errors.append(f"product/technology source coverage {product_technical_sources} < 2")
    if management_sources < 1:
        errors.append("no management/governance/capital-allocation source coverage")

    # Research coverage matrix.
    coverage_rows: list[dict[str, str]] = []
    coverage_path = workspace / "research_coverage_matrix.csv"
    if coverage_path.exists():
        try:
            coverage_rows = read_csv(coverage_path)
            by_topic = {r.get("topic", ""): r for r in coverage_rows}
            missing_topics = sorted(set(REQUIRED_TOPICS) - set(by_topic))
            if missing_topics:
                errors.append("research topics missing: " + ", ".join(missing_topics))
            for topic, materiality in REQUIRED_TOPICS.items():
                r = by_topic.get(topic)
                if not r:
                    continue
                status = str(r.get("status", "")).strip().lower()
                depth = str(r.get("depth", "")).strip().lower()
                if status not in ALLOWED_COVERAGE_STATUS:
                    errors.append(f"research topic unfinished {topic}: {status or 'blank'}")
                if materiality == "critical" and status not in {"accepted", "partial_human_required"}:
                    errors.append(f"critical research topic not covered {topic}: {status}")
                if materiality == "critical" and depth in {"", "limited", "summary_only"}:
                    errors.append(f"critical research topic lacks depth {topic}: {depth or 'blank'}")
                if status != "accepted" and not str(r.get("unresolved_questions", "")).strip():
                    errors.append(f"research topic lacks unresolved-question record {topic}")
                if not str(r.get("model_link", "")).strip():
                    errors.append(f"research topic lacks model link {topic}")
        except Exception as exc:
            errors.append(f"invalid research_coverage_matrix.csv: {exc}")

    # Company quality / moat.
    quality_path = workspace / "company_quality_moat_register.csv"
    if quality_path.exists():
        try:
            rows = read_csv(quality_path)
            by_dim = {r.get("dimension", ""): r for r in rows}
            missing = sorted(QUALITY_DIMENSIONS - set(by_dim))
            if missing:
                errors.append("company-quality dimensions missing: " + ", ".join(missing))
            substantive = 0
            for dim in QUALITY_DIMENSIONS:
                r = by_dim.get(dim)
                if not r:
                    continue
                status = str(r.get("status", "")).lower()
                if status in {"accepted", "partial_human_required"} and str(r.get("claim", "")).strip() and str(r.get("forecast_permission", "")).strip():
                    substantive += 1
            metrics["substantive_company_quality_dimensions"] = substantive
            if substantive < 7:
                errors.append(f"substantive company-quality/moat dimensions {substantive} < 7")
        except Exception as exc:
            errors.append(f"invalid company_quality_moat_register.csv: {exc}")

    # Technology commercialization.
    tech_path = workspace / "technology_commercialization_register.csv"
    if tech_path.exists():
        try:
            rows = read_csv(tech_path)
            material = [r for r in rows if str(r.get("materiality", "")).lower() in {"critical", "high"}]
            complete = [r for r in material if str(r.get("current_stage", "")).lower() not in {"", "pending", "unknown"}
                        and str(r.get("competitor_route", "")).strip()
                        and str(r.get("technical_bottleneck", "")).strip()
                        and str(r.get("allowed_model_use", "")).strip()]
            metrics["material_technology_rows"] = len(material)
            metrics["complete_technology_rows"] = len(complete)
            if len(material) < 2:
                errors.append(f"material technology/product rows {len(material)} < 2")
            if len(complete) < 2:
                errors.append(f"complete technology-commercialization rows {len(complete)} < 2")
        except Exception as exc:
            errors.append(f"invalid technology_commercialization_register.csv: {exc}")

    # Product/customer schedule.
    driver_path = workspace / "product_customer_driver_schedule.csv"
    critical_driver_human_required = False
    if driver_path.exists():
        try:
            rows = read_csv(driver_path)
            material = [r for r in rows if str(r.get("materiality", "")).lower() in {"critical", "high"}]
            modeled = [r for r in material if str(r.get("schedule_status", "")).lower() == "modeled"]
            critical_driver_human_required = any(
                str(r.get("materiality", "")).lower() == "critical" and
                (truthy(r.get("human_required")) or str(r.get("schedule_status", "")).lower() != "modeled")
                for r in rows
            )
            metrics["material_product_customer_rows"] = len(material)
            metrics["modeled_product_customer_rows"] = len(modeled)
            if not material:
                errors.append("no material product/customer driver rows")
            if not modeled:
                errors.append("no material product/customer driver schedule is modeled")
            for r in modeled:
                required = ["revenue_unit", "payer_or_customer", "volume_usage_or_deployment_driver", "price_arpu_or_asp", "mix_share_or_attach", "cost_and_capacity_constraint", "evidence_source_ids", "consolidation_link"]
                miss = [k for k in required if not str(r.get(k, "")).strip()]
                if miss:
                    errors.append(f"modeled driver {r.get('segment_or_product','UNKNOWN')} missing " + "/".join(miss))
        except Exception as exc:
            errors.append(f"invalid product_customer_driver_schedule.csv: {exc}")

    # Material assumption support.
    support_path = workspace / "material_assumption_support.csv"
    unsupported_weight = 0.0
    total_weight = 0.0
    if support_path.exists():
        try:
            rows = read_csv(support_path)
            for r in rows:
                w = max(0.0, as_float(r.get("materiality_weight"), 0))
                total_weight += w
                status = str(r.get("support_status", "")).strip().lower()
                clusters = int(as_float(r.get("evidence_cluster_count"), 0))
                if status in UNSUPPORTED:
                    unsupported_weight += w
                sensitivity = str(r.get("sensitivity_to_output", "")).lower()
                scenario = str(r.get("scenario", "")).lower()
                horizon = str(r.get("horizon", "")).lower()
                if sensitivity == "high" and scenario == "base" and clusters == 0 and any(x in horizon for x in ["fy+2", "fy+3", "year_2", "year_3"]):
                    errors.append(f"high-sensitivity unsupported Base assumption {r.get('assumption_id','UNKNOWN')}")
            ratio = unsupported_weight / total_weight if total_weight > 0 else 1.0
            metrics["material_assumption_weight"] = total_weight
            metrics["unsupported_materiality_ratio"] = ratio
            if total_weight < 0.95 or total_weight > 1.05:
                errors.append(f"materiality weights must sum to ~1.0, got {total_weight:.3f}")
            if ratio > 0.35:
                errors.append(f"unsupported materiality ratio {ratio:.1%} > 35%")
        except Exception as exc:
            errors.append(f"invalid material_assumption_support.csv: {exc}")

    # Mechanism-specific readiness and horizon contract.
    selected = manifest.get("selected_mechanisms", []) if isinstance(manifest, dict) else []
    selected_text = " ".join(str(x).lower() for x in selected)
    readiness = str(manifest.get("readiness_result") or manifest.get("readiness_target") or "").lower()
    horizon_contracts = snapshot.get("horizon_contracts", {}) if isinstance(snapshot, dict) else {}
    channel_mechanism = any(k in selected_text for k in ["cycle", "channel", "unit-volume", "unit_volume"])
    if channel_mechanism and critical_driver_human_required:
        fy2 = str(horizon_contracts.get("FY+2") or horizon_contracts.get("year_2") or "").lower()
        fy3 = str(horizon_contracts.get("FY+3") or horizon_contracts.get("year_3") or "").lower()
        if "distribution" not in fy2 or "distribution" not in fy3:
            errors.append("critical channel/driver data are Human-required, so FY+2 and FY+3 must be distribution/scenario contracts")
        if readiness in {"screen-grade", "research-grade", "decision-grade", "decision-support"}:
            errors.append(f"research gaps cap readiness below {readiness}; use hypothesis-grade or not-model-ready")

    # Report parity sections.
    report_path = workspace / "report.md"
    if report_path.exists():
        text = report_path.read_text(encoding="utf-8").lower()
        parity_sections = {
            "technology_ip_roadmap": ["technology", "patent", "standard", "roadmap", "技术", "专利"],
            "company_quality_moat": ["company quality", "moat", "competitive advantage", "护城河", "公司质量"],
            "management_capital_allocation": ["management", "governance", "capital allocation", "管理层", "资本配置"],
        }
        for key, aliases in parity_sections.items():
            if not any(a in text for a in aliases):
                errors.append(f"report missing gold-parity section {key}")

    passed = not errors
    result = {
        "workspace": str(workspace),
        "passed": passed,
        "strict": args.strict,
        "errors": errors,
        "warnings": warnings,
        "metrics": metrics,
        "research_sufficiency": "pass" if passed else "research-pack-insufficient",
        "process_integrity_note": "This validator is separate from formula/cutoff integrity.",
    }
    (workspace / "research_completeness.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if passed else 2


if __name__ == "__main__":
    raise SystemExit(main())
