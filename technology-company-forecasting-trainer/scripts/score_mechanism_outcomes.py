#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path


def load(path: str) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--predictions", required=True)
    ap.add_argument("--actuals", required=True)
    ap.add_argument(
        "--contract",
        required=False,
        help="Deprecated compatibility input; thresholds never decide method quality.",
    )
    ap.add_argument("--output", required=True)
    args = ap.parse_args()

    pred_obj, act_obj = load(args.predictions), load(args.actuals)
    preds = {r["outcome_id"]: r for r in pred_obj.get("outcomes", [])}
    acts = {r["outcome_id"]: r for r in act_obj.get("outcomes", [])}
    rows = []
    for oid, p in preds.items():
        a = acts.get(oid)
        row = {"outcome_id": oid, "matched": a is not None, "required": bool(p.get("required", True))}
        if a is not None:
            for field in ["activation", "direction", "state", "cash_classification", "financial_line"]:
                if p.get(field) is not None and a.get(field) is not None:
                    row[field + "_correct"] = p[field] == a[field]
            if p.get("timing_period") is not None and a.get("timing_period") is not None:
                row["timing_error_periods"] = abs(float(p["timing_period"]) - float(a["timing_period"]))
            if p.get("magnitude_low") is not None and p.get("magnitude_high") is not None and a.get("magnitude") is not None:
                row["magnitude_band_hit"] = float(p["magnitude_low"]) <= float(a["magnitude"]) <= float(p["magnitude_high"])
        rows.append(row)

    required = [r for r in rows if r["required"]]
    matched_required = [r for r in required if r["matched"]]

    def accuracy(field: str):
        vals = [bool(r[field]) for r in matched_required if field in r]
        return sum(vals) / len(vals) if vals else None

    timing = [float(r["timing_error_periods"]) for r in matched_required if "timing_error_periods" in r]
    metrics = {
        "required_coverage": len(matched_required) / len(required) if required else 1.0,
        "activation_accuracy": accuracy("activation_correct"),
        "direction_accuracy": accuracy("direction_correct"),
        "state_accuracy": accuracy("state_correct"),
        "cash_classification_accuracy": accuracy("cash_classification_correct"),
        "financial_line_accuracy": accuracy("financial_line_correct"),
        "magnitude_band_coverage": accuracy("magnitude_band_hit"),
        "mean_abs_timing_error_periods": sum(timing) / len(timing) if timing else None,
    }

    result = {
        "protocol_version": "3.0",
        "interpretation": (
            "diagnostic_vector_only; an independent reviewer attributes each miss and "
            "decides whether the mechanism moved for the right reason"
        ),
        "metrics": metrics,
        "rows": rows,
    }
    Path(args.output).write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
