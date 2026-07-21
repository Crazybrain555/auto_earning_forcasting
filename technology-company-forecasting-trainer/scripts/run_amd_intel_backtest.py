#!/usr/bin/env python3
from __future__ import annotations
import argparse,csv,json
from pathlib import Path

from legacy_backtest_diagnostics import write_legacy_backtest_diagnostics

def sign(x): return 1 if x>0 else (-1 if x<0 else 0)
def mean(values):
    vals=[v for v in values if v is not None]
    return sum(vals)/len(vals) if vals else None
def interval_score(a,lo,hi,den,alpha):
    s=hi-lo
    if a<lo: s+=(2/alpha)*(lo-a)
    elif a>hi: s+=(2/alpha)*(a-hi)
    return s/abs(den)

def calculate(cases):
    rows=[]
    for c in cases:
        actual_seq=[c["base_revenue"]]+c["actual_revenue"]
        old_seq=[c["base_revenue"]]+c["v74_revenue"]
        new_seq=[c["base_revenue"]]+c["v75_revenue"]
        for i,target in enumerate(c["targets"]):
            alpha=.10 if c["confidence"][i]=="90%" else .20
            for metric,actual,old,new in [
                ("revenue",c["actual_revenue"][i],c["v74_revenue"][i],c["v75_revenue"][i]),
                ("profit",c["actual_profit"][i],c["v74_profit"][i],c["v75_profit"][i]),
            ]:
                rec={
                    "case_id":c["case_id"],"company":c["company"],"mechanism":c["mechanism"],
                    "split":c["split"],"evaluation_contract":c["evaluation_contract"],
                    "cutoff":c["cutoff"],"target":target,"horizon":i+1,"metric":metric,
                    "unit":"USD bn","actual":actual,"point_evaluable":c["point_evaluable"][i],
                    "confidence":c["confidence"][i],"regime":c["regime"],
                    "human_required":c["human_required"],"source_ids":c["source_ids"],
                    "point_in_time_note":c["point_in_time_note"],
                }
                for version,pred,rev,pb in [
                    ("v74",old,c["v74_revenue"][i],c["v74_profit_margin_band"][i]),
                    ("v75",new,c["v75_revenue"][i],c["v75_profit_margin_band"][i]),
                ]:
                    if metric=="revenue":
                        hw=(c["v74_revenue_half_width"] if version=="v74" else c["v75_revenue_half_width"])[i]
                        lo,hi=pred*(1-hw),pred*(1+hw);den=actual
                        point=abs(pred-actual)/abs(actual) if c["point_evaluable"][i] else None
                        margin=None
                        seq=old_seq if version=="v74" else new_seq
                        direction=(sign(seq[i+1]-seq[i])==sign(actual_seq[i+1]-actual_seq[i])) if c["point_evaluable"][i] else None
                        sign_ok=None
                    else:
                        lo,hi=pred-rev*pb,pred+rev*pb;den=c["actual_revenue"][i]
                        point=None
                        margin=abs(pred/rev-actual/c["actual_revenue"][i])*100 if c["point_evaluable"][i] else None
                        direction=None
                        sign_ok=(sign(pred)==sign(actual)) if c["point_evaluable"][i] else None
                    rec[f"{version}"]=pred;rec[f"{version}_low"]=lo;rec[f"{version}_high"]=hi
                    rec[f"{version}_hit"]=lo<=actual<=hi
                    rec[f"{version}_interval_score"]=interval_score(actual,lo,hi,den,alpha)
                    rec[f"{version}_point_error"]=point
                    rec[f"{version}_margin_error_pp"]=margin
                    rec[f"{version}_direction_correct"]=direction
                    rec[f"{version}_sign_correct"]=sign_ok
                rows.append(rec)
    return rows

def aggregate(rows,split,version):
    selected=[r for r in rows if r["split"]==split and r["point_evaluable"]]
    rev=[r for r in selected if r["metric"]=="revenue"]
    prof=[r for r in selected if r["metric"]=="profit"]
    return {
        "cases":len({r["case_id"] for r in selected}),
        "revenue_mape":mean(r[f"{version}_point_error"] for r in rev),
        "profit_margin_mae_pp":mean(r[f"{version}_margin_error_pp"] for r in prof),
        "revenue_direction_accuracy":mean(1 if r[f"{version}_direction_correct"] else 0 for r in rev),
        "profit_sign_accuracy":mean(1 if r[f"{version}_sign_correct"] else 0 for r in prof),
        "revenue_coverage":mean(1 if r[f"{version}_hit"] else 0 for r in rev),
        "profit_coverage":mean(1 if r[f"{version}_hit"] else 0 for r in prof),
        "revenue_interval_score":mean(r[f"{version}_interval_score"] for r in rev),
        "profit_interval_score":mean(r[f"{version}_interval_score"] for r in prof),
    }

def by_case(rows):
    out=[]
    for cid in sorted({r["case_id"] for r in rows if r["split"]=="holdout"}):
        rr=[r for r in rows if r["case_id"]==cid and r["point_evaluable"]]
        rev=[r for r in rr if r["metric"]=="revenue"];p=[r for r in rr if r["metric"]=="profit"]
        out.append({
            "case_id":cid,
            "v74_revenue_mape":mean(r["v74_point_error"] for r in rev),
            "v75_revenue_mape":mean(r["v75_point_error"] for r in rev),
            "v74_profit_margin_mae_pp":mean(r["v74_margin_error_pp"] for r in p),
            "v75_profit_margin_mae_pp":mean(r["v75_margin_error_pp"] for r in p),
        })
    return out

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--cases",type=Path,required=True)
    ap.add_argument("--output-dir",type=Path,required=True)
    args=ap.parse_args();args.output_dir.mkdir(parents=True,exist_ok=True)
    cases=json.loads(args.cases.read_text(encoding="utf-8"))
    rows=calculate(cases)
    metrics={s:{v:aggregate(rows,s,v) for v in ("v74","v75")} for s in ("calibration","holdout")}
    bc=by_case(rows);old=metrics["holdout"]["v74"];new=metrics["holdout"]["v75"]
    threshold_observations={
        "holdout_revenue_improves":new["revenue_mape"]<old["revenue_mape"],
        "holdout_profit_improves":new["profit_margin_mae_pp"]<old["profit_margin_mae_pp"],
        "revenue_coverage_ge_80pct":new["revenue_coverage"]>=.80,
        "profit_coverage_ge_80pct":new["profit_coverage"]>=.80,
        "all_holdout_cases_revenue_improve":all(x["v75_revenue_mape"]<x["v74_revenue_mape"] for x in bc),
        "all_holdout_cases_profit_improve":all(x["v75_profit_margin_mae_pp"]<x["v74_profit_margin_mae_pp"] for x in bc),
    }
    result={"model_version":"technology-company-forecasting-v7.5","metrics":metrics,"by_case":bc}
    write_legacy_backtest_diagnostics(args.output_dir, result, threshold_observations)
    fields=[]
    for r in rows:
        for k in r:
            if k not in fields:fields.append(k)
    with (args.output_dir/"detail.csv").open("w",encoding="utf-8-sig",newline="") as f:
        w=csv.DictWriter(f,fieldnames=fields);w.writeheader();w.writerows(rows)
    print(json.dumps(result,ensure_ascii=False,indent=2))
if __name__=="__main__": main()
