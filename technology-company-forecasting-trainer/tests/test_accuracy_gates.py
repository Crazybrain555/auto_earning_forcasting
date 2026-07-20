"""The accuracy gates aim at the three scored metrics. Round-1 measured
FY+1/2/3 revenue APE of ~6/10/19% with 50% interval coverage, and >90% of the
worst profit misses came from margin and below-the-line, not revenue."""
import json
import subprocess
import sys
import tempfile
from pathlib import Path

SKILL = Path(__file__).resolve().parents[1]

BASE_SNAPSHOT = {
    "historical_base": {"trailing_organic_growth_pct": 20.0},
    "error_budget": {h: {"expected_revenue_error_pct": 6, "expected_margin_error_pp": 2,
                         "dominant_risk": "margin", "why": "spread"}
                     for h in ("year_1", "year_2", "year_3_distribution")},
    "outputs": {
        "year_1": {"revenue_point": 1000.0},
        "year_2": {"revenue_point": 1300.0, "revenue_low": 1150.0, "revenue_high": 1450.0},
        "year_3_distribution": {"revenue_point": 1600.0, "revenue_low": 1280.0, "revenue_high": 1920.0},
    },
}
FULL_REPORT = ("# R\n\nTax rate normalized; no valuation allowance. Interest income modeled, no FX exposure. "
               "No impairment or restructuring. Share count flat, no buyback.\n")


def run(snapshot, report=FULL_REPORT, manifest=None):
    with tempfile.TemporaryDirectory() as td:
        ws = Path(td)
        (ws / "run_manifest.json").write_text(json.dumps(manifest or {"entity": "T", "as_of": "2026-07-18"}), encoding="utf-8")
        (ws / "forecast_snapshot.json").write_text(json.dumps(snapshot), encoding="utf-8")
        (ws / "report.md").write_text(report, encoding="utf-8")
        subprocess.run([sys.executable, str(SKILL / "scripts/validate_delivery.py"), "--workspace", str(ws)],
                       capture_output=True, text=True)
        result = json.loads((ws / "delivery_validation.json").read_text(encoding="utf-8"))
    return {c["check"]: c for c in result["checks"]}


def test_narrow_intervals_are_rejected():
    """+/-4% at FY+2 claims precision the method has never demonstrated."""
    snap = json.loads(json.dumps(BASE_SNAPSHOT))
    snap["outputs"]["year_2"].update({"revenue_low": 1250.0, "revenue_high": 1350.0})
    c = run(snap)["accuracy:interval-width"]
    assert not c["passed"] and "floor 11%" in c["detail"], c["detail"]


def test_honest_intervals_pass():
    assert run(BASE_SNAPSHOT)["accuracy:interval-width"]["passed"]


def test_unexplained_deceleration_is_rejected():
    """FY+2 implied growth 30% vs trailing 20% is fine; below trailing needs a reason."""
    snap = json.loads(json.dumps(BASE_SNAPSHOT))
    snap["outputs"]["year_2"]["revenue_point"] = 1050.0   # +5% vs trailing 20%
    snap["outputs"]["year_2"].update({"revenue_low": 900.0, "revenue_high": 1200.0})
    c = run(snap)["accuracy:deceleration-argued"]
    assert not c["passed"] and "no deceleration_reason" in c["detail"], c["detail"]


def test_argued_deceleration_passes():
    snap = json.loads(json.dumps(BASE_SNAPSHOT))
    snap["outputs"]["year_2"]["revenue_point"] = 1050.0
    snap["outputs"]["year_2"].update({"revenue_low": 900.0, "revenue_high": 1200.0})
    snap["deceleration_reason"] = "Two large programs end-of-life in FY+2; replacement ramps only in FY+3."
    assert run(snap)["accuracy:deceleration-argued"]["passed"]


def test_missing_error_budget_is_rejected():
    snap = json.loads(json.dumps(BASE_SNAPSHOT))
    del snap["error_budget"]
    c = run(snap)["accuracy:error-budget"]
    assert not c["passed"] and "error_budget missing" in c["detail"]


def test_below_the_line_silence_is_rejected():
    """The largest round-1 margin error was an unconsidered DTA release."""
    c = run(BASE_SNAPSHOT, report="# R\n\nRevenue grows. Margins expand.\n")["accuracy:below-the-line-screen"]
    assert not c["passed"]
    for topic in ("tax", "one_offs", "share_count"):
        assert topic in c["detail"], c["detail"]


def test_full_below_the_line_screen_passes():
    assert run(BASE_SNAPSHOT)["accuracy:below-the-line-screen"]["passed"]
