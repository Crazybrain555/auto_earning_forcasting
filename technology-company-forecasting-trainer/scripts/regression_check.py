#!/usr/bin/env python3
"""Ensure v6 leaves locked legacy v5/v4 forecasts and intervals unchanged."""
from __future__ import annotations
import argparse, csv, json
from pathlib import Path

def load(path: Path):
    with path.open(encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))

def key(row):
    return (row["案例"], row["目标期"], row["期限"], row["指标"])

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--baseline", type=Path, required=True)
    parser.add_argument("--candidate", type=Path, required=True)
    parser.add_argument("--output", type=Path)
    args=parser.parse_args()
    baseline={key(r):r for r in load(args.baseline)}
    candidate={key(r):r for r in load(args.candidate)}
    missing=sorted(set(baseline)-set(candidate))
    extra=sorted(set(candidate)-set(baseline))
    differences=[]
    for row_key, row in baseline.items():
        if row_key not in candidate:
            continue
        other=candidate[row_key]
        for old_col,new_col in [("v4点预测","v6点预测"),("v4下限","v6下限"),("v4上限","v6上限")]:
            if abs(float(row[old_col])-float(other[new_col])) > 1e-12:
                differences.append({"key":row_key,"field":new_col,"baseline":row[old_col],"candidate":other[new_col]})
    result={"rows":len(baseline),"missing":missing,"extra":extra,"differences":differences,"passed":not missing and not extra and not differences}
    text=json.dumps(result,ensure_ascii=False,indent=2)
    print(text)
    if args.output:
        args.output.parent.mkdir(parents=True,exist_ok=True)
        args.output.write_text(text+"\n",encoding="utf-8")
    if not result["passed"]:
        raise SystemExit(2)

if __name__ == "__main__":
    main()
