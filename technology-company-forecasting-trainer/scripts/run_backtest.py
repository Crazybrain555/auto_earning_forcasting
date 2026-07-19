#!/usr/bin/env python3
"""Run the bundled AI-hardware value-chain backtest using only the standard library."""
from __future__ import annotations
import argparse, csv, json, math
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

WIDTHS = {
    "diversified-wafer-fab-equipment": ([.10,.18,.25],[.04,.07,.10]),
    "process-control-content-intensity": ([.10,.18,.25],[.04,.07,.10]),
    "hybrid-semiconductor-software-ma": ([.12,.25,.35],[.06,.12,.18]),
    "power-cooling-project-backlog": ([.10,.20,.30],[.05,.10,.15]),
    "optics-materials-ma-integration": ([.12,.25,.35],[.06,.12,.18]),
    "networking-customer-concentration": ([.12,.22,.30],[.04,.08,.12]),
    "server-rack-bom-pass-through": ([.12,.25,.35],[.04,.08,.12]),
    "osat-advanced-packaging-utilization": ([.10,.20,.28],[.04,.08,.12]),
    "semiconductor-materials-content-ma": ([.12,.25,.35],[.06,.12,.18]),
    "compute-platform-segments-ma": ([.12,.25,.35],[.06,.12,.18]),
}

def sign(x: float) -> int:
    return 1 if x > 0 else (-1 if x < 0 else 0)

def mean(values):
    values=list(values)
    return sum(values)/len(values) if values else None

def interval_score(actual, low, high, denominator, alpha=.20):
    score=high-low
    if actual < low:
        score += (2/alpha)*(low-actual)
    elif actual > high:
        score += (2/alpha)*(actual-high)
    return score/abs(denominator)

def load(benchmark: Path, cases_path: Path):
    with benchmark.open(encoding='utf-8-sig',newline='') as f:
        rows=list(csv.DictReader(f))
    cases={c['case_id']:c for c in json.loads(cases_path.read_text(encoding='utf-8'))}
    return rows,cases

def calculate(rows,cases):
    by={(r['case_id'],int(r['horizon']),r['metric']):r for r in rows}
    details=[]
    for r in rows:
        case=cases[r['case_id']]; h=int(r['horizon']); idx=h-1
        actual=float(r['actual']); metric=r['metric']
        rw,pb=WIDTHS[case['archetype']]
        out=dict(r)
        for version in ('v5','v6'):
            pred=float(r[version])
            if metric=='revenue':
                lo,hi=pred*(1-rw[idx]),pred*(1+rw[idx])
                point_error=abs(pred-actual)/abs(actual)
                margin_error=None
                denominator=actual
            else:
                rev=by[(r['case_id'],h,'revenue')]
                pred_rev=float(rev[version]); actual_rev=float(rev['actual'])
                lo,hi=pred-pred_rev*pb[idx],pred+pred_rev*pb[idx]
                point_error=None
                margin_error=abs(pred/pred_rev-actual/actual_rev)*100
                denominator=actual_rev
            out[f'{version}_low']=lo; out[f'{version}_high']=hi
            out[f'{version}_hit']=lo<=actual<=hi
            out[f'{version}_point_error']=point_error
            out[f'{version}_margin_error_pp']=margin_error
            out[f'{version}_interval_score']=interval_score(actual,lo,hi,denominator)
            if metric=='profit':
                out[f'{version}_sign_correct']=sign(pred)==sign(actual)
        details.append(out)
    # Direction accuracy by case/version.
    direction={}
    for cid,case in cases.items():
        actual_seq=[float(case['base_revenue'])]+[float(x) for x in case['actual_revenue']]
        for version in ('v5','v6'):
            pred_seq=[float(case['base_revenue'])]+[float(x) for x in case[f'{version}_revenue']]
            direction[(cid,version)]=[
                sign(pred_seq[i+1]-pred_seq[i])==sign(actual_seq[i+1]-actual_seq[i]) for i in range(3)
            ]
    for d in details:
        if d['metric']=='revenue':
            d['v5_direction_correct']=direction[(d['case_id'],'v5')][int(d['horizon'])-1]
            d['v6_direction_correct']=direction[(d['case_id'],'v6')][int(d['horizon'])-1]
    return details

def aggregate(details, split=None, version='v6'):
    subset=[d for d in details if split is None or d['split']==split]
    rev=[d for d in subset if d['metric']=='revenue']; prof=[d for d in subset if d['metric']=='profit']
    return {
        'cases':len({d['case_id'] for d in subset}),
        'revenue_mape':mean(d[f'{version}_point_error'] for d in rev),
        'profit_margin_mae_pp':mean(d[f'{version}_margin_error_pp'] for d in prof),
        'revenue_direction_accuracy':mean(1 if d[f'{version}_direction_correct'] else 0 for d in rev),
        'profit_sign_accuracy':mean(1 if d[f'{version}_sign_correct'] else 0 for d in prof),
        'revenue_coverage':mean(1 if d[f'{version}_hit'] else 0 for d in rev),
        'profit_coverage':mean(1 if d[f'{version}_hit'] else 0 for d in prof),
        'revenue_interval_score':mean(d[f'{version}_interval_score'] for d in rev),
        'profit_interval_score':mean(d[f'{version}_interval_score'] for d in prof),
    }

def main():
    p=argparse.ArgumentParser()
    p.add_argument('--benchmark',type=Path,required=True)
    p.add_argument('--cases',type=Path,required=True)
    p.add_argument('--output-dir',type=Path,required=True)
    args=p.parse_args(); args.output_dir.mkdir(parents=True,exist_ok=True)
    rows,cases=load(args.benchmark,args.cases); details=calculate(rows,cases)
    summary={}
    for split in ('calibration','holdout'):
        summary[split]={v:aggregate(details,split,v) for v in ('v5','v6')}
    summary['all']={v:aggregate(details,None,v) for v in ('v5','v6')}
    h={}
    for horizon in (1,2,3):
        hd=[d for d in details if d['split']=='holdout' and int(d['horizon'])==horizon]
        h[str(horizon)]={v:aggregate(hd,None,v) for v in ('v5','v6')}
    summary['holdout_by_horizon']=h
    old=summary['holdout']['v5']; new=summary['holdout']['v6']
    summary['gate_results']={
        'holdout_revenue_mape_le_10pct':new['revenue_mape']<=.10,
        'holdout_profit_margin_mae_le_5pp':new['profit_margin_mae_pp']<=5,
        'direction_ge_85pct':new['revenue_direction_accuracy']>=.85,
        'profit_sign_ge_90pct':new['profit_sign_accuracy']>=.90,
        'revenue_interval_score_improves_30pct':1-new['revenue_interval_score']/old['revenue_interval_score']>=.30,
        'profit_interval_score_improves_30pct':1-new['profit_interval_score']/old['profit_interval_score']>=.30,
    }
    result={'model_version':'ai-hardware-forecasting-v6.0','benchmark_id':args.benchmark.name,
            'generated_at':datetime.now(timezone.utc).isoformat(),'metrics':summary,
            'gate_results':summary['gate_results'],
            'limitations':['Retrospective point-in-time simulation; not pre-registered live performance.',
                           'Point estimates were constructed from historical source packs and remain vulnerable to hindsight bias.']}
    (args.output_dir/'metrics.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    fields=[]
    for row in details:
        for key in row:
            if key not in fields:
                fields.append(key)
    with (args.output_dir/'detail.csv').open('w',encoding='utf-8-sig',newline='') as f:
        w=csv.DictWriter(f,fieldnames=fields);w.writeheader();w.writerows(details)
    print(json.dumps(result,ensure_ascii=False,indent=2))
    if not all(summary['gate_results'].values()):
        raise SystemExit(2)
if __name__=='__main__': main()
