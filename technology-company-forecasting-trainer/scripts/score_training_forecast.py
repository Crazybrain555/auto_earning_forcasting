#!/usr/bin/env python3
"""Score a SEALED training forecast against externally retrieved actuals.

Integrity rules (see _seal_core): the seal is fully re-verified before and
after scoring (forged seals, tampered files, and files added after sealing
all fail); actuals must come from outside the sealed area; outputs go only
to the seal-exempt evaluation/ subtree; nothing sealed is ever rewritten -
scoring leaves the sealed workspace bit-for-bit intact.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _seal_core as core


def interval_score(actual, low, high, denom, alpha=0.2):
    width = high - low
    if actual < low:
        width += (2 / alpha) * (low - actual)
    elif actual > high:
        width += (2 / alpha) * (actual - high)
    return width / abs(denom)


def output_for(snapshot, period):
    if snapshot.get("historical_forecasts"):
        return next(x for x in snapshot["historical_forecasts"] if x.get("period") == period)
    key = {"FY+1": "year_1", "FY+2": "year_2", "FY+3": "year_3_distribution"}[period]
    return snapshot["outputs"][key]


def val(output, *names):
    for name in names:
        if name in output and output[name] is not None:
            return float(output[name])
    return None


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--workspace", required=True)
    parser.add_argument("--actuals", required=True)
    parser.add_argument("--output", default=None)
    parser.add_argument("--receipt", default=None,
                        help="external seal receipt path (default <round>/seal_receipts/<case>.json)")
    parser.add_argument("--allow-missing-receipt", action="store_true",
                        help="score a pre-receipt legacy workspace; recorded as receipt_verified=legacy_no_receipt")
    args = parser.parse_args()
    workspace = Path(args.workspace).resolve()
    actuals_path = Path(args.actuals).resolve()

    try:
        seal = core.verify_seal(workspace)
        core.assert_outside_sealed_area(workspace, actuals_path)
    except core.SealError as exc:
        raise SystemExit(f"seal verification failed: {exc}")

    # External receipt check: the in-workspace seal alone cannot prove the
    # workspace was not wholly rebuilt after actuals exposure; the receipt was
    # recorded outside the workspace at freeze time and must match exactly.
    receipt_path = Path(args.receipt).resolve() if args.receipt else workspace.parent / "seal_receipts" / f"{workspace.name}.json"
    receipt_verified = "legacy_no_receipt"
    if receipt_path.is_file():
        try:
            receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
        except Exception as exc:
            raise SystemExit(f"seal receipt unreadable: {exc}")
        problems = []
        if receipt.get("pack_hash") != seal["pack_hash"]:
            problems.append("pack_hash mismatch - workspace was resealed or rebuilt after the receipt")
        if receipt.get("sealed_at") != seal.get("sealed_at"):
            problems.append("sealed_at mismatch")
        if receipt.get("recorded_before_actuals") is not True:
            problems.append("recorded_before_actuals is not true")
        if problems:
            raise SystemExit("seal receipt verification failed: " + "; ".join(problems))
        receipt_verified = True
    elif not args.allow_missing_receipt:
        raise SystemExit(
            f"no external seal receipt at {receipt_path} - freeze_training_forecast.py records one "
            "at seal time; for pre-receipt legacy workspaces pass --allow-missing-receipt")

    actuals = json.loads(actuals_path.read_text(encoding="utf-8"))
    if not actuals.get("retrieved_after_seal"):
        raise SystemExit("actuals must be marked retrieved_after_seal")

    snap = json.loads((workspace / "forecast_snapshot.json").read_text(encoding="utf-8"))
    rows = []
    for act in actuals["periods"]:
        period = act["period"]
        o = output_for(snap, period)
        rev, profit = float(act["revenue"]), float(act["profit"])
        rp = val(o, "revenue_point", "revenue", "revenue_base", "revenue_M", "revenue_base_M")
        rl = val(o, "revenue_low", "revenue_bear", "revenue_low_M", "revenue_bear_M")
        rh = val(o, "revenue_high", "revenue_bull", "revenue_high_M", "revenue_bull_M")
        pp = val(o, "profit_point", "net_income", "profit", "profit_base", "net_income_M", "profit_M")
        pl = val(o, "profit_low", "profit_bear", "net_income_bear_M")
        ph = val(o, "profit_high", "profit_bull", "net_income_bull_M")
        point = bool(o.get("point_evaluable", period != "FY+3"))
        alpha = 0.2 if point else 0.1
        rec = {"period": period, "point_evaluable": point, "actual_revenue": rev,
               "forecast_revenue": rp, "actual_profit": profit, "forecast_profit": pp}
        if point:
            rec["revenue_ape"] = abs(rp - rev) / abs(rev)
            rec["profit_margin_error_pp"] = abs(pp / rp - profit / rev) * 100
        if rl is not None and rh is not None:
            rec["revenue_hit"] = rl <= rev <= rh
            rec["revenue_interval_score"] = interval_score(rev, rl, rh, rev, alpha)
        if pl is not None and ph is not None:
            rec["profit_hit"] = pl <= profit <= ph
            rec["profit_interval_score"] = interval_score(profit, pl, ph, rev, alpha)
        rows.append(rec)

    pts = [r for r in rows if r["point_evaluable"]]

    def mean(key):
        values = [r[key] for r in pts if key in r]
        return sum(values) / len(values) if values else None

    metrics = {"revenue_mape": mean("revenue_ape"), "profit_margin_mae_pp": mean("profit_margin_error_pp"),
               "revenue_coverage": mean("revenue_hit"), "profit_coverage": mean("profit_hit"),
               "revenue_interval_score": mean("revenue_interval_score"), "profit_interval_score": mean("profit_interval_score")}
    result = {"case_id": actuals.get("case_id"), "seal_hash": seal["pack_hash"], "hash_verified": True,
              "receipt_verified": receipt_verified,
              "seal_reverified_after_scoring": False, "actuals_retrieved_after_seal": True,
              "scored_at": dt.datetime.now(dt.timezone.utc).isoformat(), "metrics": metrics, "scores": rows}

    out = Path(args.output).resolve() if args.output else workspace / "evaluation" / "evaluation.json"
    try:
        core.assert_outside_sealed_area(workspace, out)
    except core.SealError as exc:
        raise SystemExit(f"refusing to write into the sealed area: {exc}")
    out.parent.mkdir(parents=True, exist_ok=True)

    vault = workspace / "actuals_vault"
    vault.mkdir(exist_ok=True)
    if actuals_path.parent != vault:
        shutil.copy2(actuals_path, vault / "actuals.json")

    out.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")

    try:
        core.verify_seal(workspace)
    except core.SealError as exc:
        raise SystemExit(f"scoring broke the seal - investigate: {exc}")
    result["seal_reverified_after_scoring"] = True
    out.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
