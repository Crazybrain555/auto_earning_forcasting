"""Materiality must be computed (a perturbation and its measured effect),
never an assigned weight, and material assumptions must be corroborated
across research lanes."""
import csv
import json
import subprocess
import sys
import tempfile
from pathlib import Path

SKILL = Path(__file__).resolve().parents[1]

HEADER = ["assumption_id", "claim", "driver_link", "test_delta", "revenue_impact_pct",
          "profit_impact_pct", "changes_conclusion", "support_status", "source_ids",
          "lanes", "falsification_trigger", "horizon", "scenario", "notes"]

SOURCES = [
    {"source_id": "S1", "source_type": "SEC_filing_10K", "publisher": "Example Corp",
     "location": "https://sec.gov/x", "claim_or_fact": "segment revenue", "evidence_tier": "E0"},
    {"source_id": "S2", "source_type": "earnings_call_transcript", "publisher": "Example Corp",
     "location": "https://example.com/call", "claim_or_fact": "management guidance", "evidence_tier": "E1"},
    {"source_id": "S3", "source_type": "industry_research", "publisher": "TrendForce",
     "location": "https://trendforce.com/x", "claim_or_fact": "shipment data", "evidence_tier": "E3"},
]


def run_case(rows):
    with tempfile.TemporaryDirectory() as td:
        ws = Path(td)
        (ws / "run_manifest.json").write_text(json.dumps({"entity": "TEST", "as_of": "2026-07-18"}), encoding="utf-8")
        (ws / "source_manifest.json").write_text(json.dumps({"sources": SOURCES}), encoding="utf-8")
        with (ws / "material_assumption_support.csv").open("w", encoding="utf-8", newline="") as fh:
            w = csv.writer(fh)
            w.writerow(HEADER)
            w.writerows(rows)
        subprocess.run([sys.executable, str(SKILL / "scripts/validate_delivery.py"),
                        "--workspace", str(ws)], capture_output=True, text=True)
        result = json.loads((ws / "delivery_validation.json").read_text(encoding="utf-8"))
    for c in result["checks"]:
        if c["check"] == "research:material-corroboration":
            return c
    return None


def test_uncomputed_importance_is_rejected():
    """An assumption with no perturbation test cannot claim importance."""
    check = run_case([["A01", "ASP rises", "seg:AI.price", "", "", "", "no", "corroborated", "S1;S2", "", "trigger", "FY+2", "Base", ""]])
    assert check is not None and not check["passed"]
    assert "no computed sensitivity" in check["detail"], check["detail"]


def test_material_assumption_needs_two_lanes():
    """Computed as material (8% revenue) but single lane -> rejected."""
    check = run_case([["A01", "ASP rises 20%", "seg:AI.price", "-5pp ASP", "8.0", "19.0", "no", "corroborated", "S1", "", "trigger", "FY+2", "Base", ""]])
    assert check is not None and not check["passed"]
    assert "needs >=2 research lanes" in check["detail"], check["detail"]


def test_conclusion_flipping_assumption_needs_falsification_trigger():
    check = run_case([["A01", "ramp lands", "seg:AI.volume", "slip 2 quarters", "1.0", "1.0", "yes", "corroborated", "S1;S3", "", "", "FY+2", "Base", ""]])
    assert check is not None and not check["passed"]
    assert "falsification trigger" in check["detail"], check["detail"]


def test_well_supported_material_assumption_passes():
    """Computed material, two lanes with an anchoring one, trigger stated."""
    check = run_case([["A01", "ASP rises 20%", "seg:AI.price", "-5pp ASP", "8.0", "19.0", "no", "corroborated", "S1;S3", "", "contract price falls 10% qoq", "FY+2", "Base", ""]])
    assert check is not None and check["passed"], check["detail"]


def test_immaterial_assumption_is_not_gated():
    """Below the computed floors -> no corroboration burden."""
    check = run_case([["A01", "minor opex line", "opex:misc", "-10%", "0.3", "0.4", "no", "single_lane", "S3", "", "", "FY+1", "Base", ""]])
    assert check is not None and check["passed"], check["detail"]
