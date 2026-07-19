#!/usr/bin/env python3
from __future__ import annotations
import argparse,csv,json
from datetime import datetime,timezone
from pathlib import Path
OLD_REV=[.10,.18,.25];OLD_PB=[.04,.07,.10]
def sign(x):return 1 if x>0 else (-1 if x<0 else 0)
def mean(v):
    v=[x for x in v if x is not None]
    return sum(v)/len(v) if v else None
def score(a,l,u,d,alpha):
    s=u-l
    if a<l:s+=(2/alpha)*(l-a)
    elif a>u:s+=(2/alpha)*(a-u)
    return s/abs(d)
def load(b,c):
    with b.open(encoding="utf-8-sig",newline="") as f: rows=list(csv.DictReader(f))
    cases={x["case_id"]:x for x in json.loads(c.read_text(encoding="utf-8"))}
    return rows,cases
def truthy(x):return str(x).lower() in ("true","1","yes")
def calc(rows,cases,old,new):
    by={(r["case_id"],int(r["horizon"]),r["metric"]):r for r in rows};out=[];dirs={}
    for cid,c in cases.items():
        actual=[float(c["base_revenue"])]+[float(x) for x in c["actual_revenue"]]
        for v in (old,new):
            pred=[float(c["base_revenue"])]+[float(x) for x in c[f"{v}_revenue"]]
            dirs[(cid,v)]=[sign(pred[i+1]-pred[i])==sign(actual[i+1]-actual[i]) for i in range(3)]
    for r in rows:
        c=cases[r["case_id"]];h=int(r["horizon"]);i=h-1;m=r["metric"];a=float(r["actual"]);z=dict(r)
        alpha=.10 if r["confidence"]=="90%" else .20
        z["point_evaluable"]=truthy(r.get("point_evaluable"))
        for v in (old,new):
            p=float(r[v])
            if v==old:
                if m=="revenue":lo,hi=p*(1-OLD_REV[i]),p*(1+OLD_REV[i])
                else:
                    pr=float(by[(r["case_id"],h,"revenue")][v]);lo,hi=p-pr*OLD_PB[i],p+pr*OLD_PB[i]
            else:
                if m=="revenue":
                    if "v72_revenue_intervals" in c:lo,hi=[float(x) for x in c["v72_revenue_intervals"][i]]
                    else:
                        w=float(c["v72_revenue_half_width"][i]);lo,hi=p*(1-w),p*(1+w)
                else:
                    if "v72_profit_intervals" in c:lo,hi=[float(x) for x in c["v72_profit_intervals"][i]]
                    else:
                        pr=float(by[(r["case_id"],h,"revenue")][v]);b=float(c["v72_profit_margin_band"][i]);lo,hi=p-pr*b,p+pr*b
            if m=="revenue":
                den=a;z[f"{v}_point_error"]=abs(p-a)/abs(a) if z["point_evaluable"] else None;z[f"{v}_margin_error_pp"]=None;z[f"{v}_direction_correct"]=dirs[(r["case_id"],v)][i] if z["point_evaluable"] else None;z[f"{v}_sign_correct"]=None
            else:
                rev=by[(r["case_id"],h,"revenue")];ar=float(rev["actual"]);pr=float(rev[v]);den=ar;z[f"{v}_point_error"]=None;z[f"{v}_margin_error_pp"]=abs(p/pr-a/ar)*100 if z["point_evaluable"] else None;z[f"{v}_direction_correct"]=None;z[f"{v}_sign_correct"]=sign(p)==sign(a) if z["point_evaluable"] else None
            z[f"{v}_low"]=lo;z[f"{v}_high"]=hi;z[f"{v}_hit"]=lo<=a<=hi;z[f"{v}_interval_score"]=score(a,lo,hi,den,alpha)
        out.append(z)
    return out
def agg(d,split,v,point_only=True):
    ss=[x for x in d if x["split"]==split and ((x["point_evaluable"] and point_only) or (not point_only and not x["point_evaluable"]))]
    rev=[x for x in ss if x["metric"]=="revenue"];pro=[x for x in ss if x["metric"]=="profit"]
    return {"cases":len({x["case_id"] for x in ss}),"revenue_mape":mean(x[f"{v}_point_error"] for x in rev),"profit_margin_mae_pp":mean(x[f"{v}_margin_error_pp"] for x in pro),"revenue_direction_accuracy":mean(1 if x[f"{v}_direction_correct"] else 0 for x in rev if x[f"{v}_direction_correct"] is not None),"profit_sign_accuracy":mean(1 if x[f"{v}_sign_correct"] else 0 for x in pro if x[f"{v}_sign_correct"] is not None),"revenue_coverage":mean(1 if x[f"{v}_hit"] else 0 for x in rev),"profit_coverage":mean(1 if x[f"{v}_hit"] else 0 for x in pro),"revenue_interval_score":mean(x[f"{v}_interval_score"] for x in rev),"profit_interval_score":mean(x[f"{v}_interval_score"] for x in pro)}
def distribution(d,v):
    ss=[x for x in d if not x["point_evaluable"]];rev=[x for x in ss if x["metric"]=="revenue"];pro=[x for x in ss if x["metric"]=="profit"]
    return {"cases":len({x["case_id"] for x in ss}),"revenue_coverage":mean(1 if x[f"{v}_hit"] else 0 for x in rev),"profit_coverage":mean(1 if x[f"{v}_hit"] else 0 for x in pro),"revenue_interval_score":mean(x[f"{v}_interval_score"] for x in rev),"profit_interval_score":mean(x[f"{v}_interval_score"] for x in pro)}
def main():
    p=argparse.ArgumentParser();p.add_argument("--benchmark",type=Path,required=True);p.add_argument("--cases",type=Path,required=True);p.add_argument("--output-dir",type=Path,required=True);p.add_argument("--old",default="v71");p.add_argument("--new",default="v72");p.add_argument("--name",required=True);a=p.parse_args();a.output_dir.mkdir(parents=True,exist_ok=True)
    rows,cases=load(a.benchmark,a.cases);d=calc(rows,cases,a.old,a.new)
    metrics={"calibration":{v:agg(d,"calibration",v) for v in (a.old,a.new)},"holdout":{v:agg(d,"holdout",v) for v in (a.old,a.new)},"distribution":{v:distribution(d,v) for v in (a.old,a.new)}}
    old,new=metrics["holdout"][a.old],metrics["holdout"][a.new];dist=metrics["distribution"][a.new]
    gates={"revenue_mape_le_8pct":new["revenue_mape"]<=.08,"profit_margin_mae_le_5pp":new["profit_margin_mae_pp"]<=5,"revenue_direction_ge_80pct":new["revenue_direction_accuracy"]>=.80,"profit_sign_ge_90pct":new["profit_sign_accuracy"]>=.90,"revenue_coverage_ge_80pct":new["revenue_coverage"]>=.80,"profit_coverage_ge_80pct":new["profit_coverage"]>=.80,"revenue_interval_score_improves_30pct":1-new["revenue_interval_score"]/old["revenue_interval_score"]>=.30,"profit_interval_score_improves_30pct":1-new["profit_interval_score"]/old["profit_interval_score"]>=.30,"distribution_revenue_coverage_ge_80pct":dist["revenue_coverage"]>=.80,"distribution_profit_coverage_ge_80pct":dist["profit_coverage"]>=.80,"human_required_present":any(c.get("human_required") for c in cases.values())}
    result={"model_version":"technology-company-forecasting-v7.2","benchmark":a.name,"generated_at":datetime.now(timezone.utc).isoformat(),"metrics":metrics,"gate_results":gates,"limitations":["Retrospective point-in-time simulation, not pre-registered live performance.","Small company-specific sample.","Point metrics exclude horizons classified as exogenous, perimeter-break, or regime-tail distribution contracts."]}
    (a.output_dir/"metrics.json").write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    fields=[]
    for x in d:
        for k in x:
            if k not in fields:fields.append(k)
    with (a.output_dir/"detail.csv").open("w",encoding="utf-8-sig",newline="") as f:w=csv.DictWriter(f,fieldnames=fields);w.writeheader();w.writerows(d)
    print(json.dumps(result,ensure_ascii=False,indent=2))
    if not all(gates.values()):raise SystemExit(2)
if __name__=="__main__":main()
