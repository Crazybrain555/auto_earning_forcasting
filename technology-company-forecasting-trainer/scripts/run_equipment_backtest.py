#!/usr/bin/env python3
from __future__ import annotations
import argparse,csv,json
from pathlib import Path
from datetime import datetime,timezone

from legacy_backtest_diagnostics import write_legacy_backtest_diagnostics

REV61=[.10,.18,.25]; PB61=[.04,.07,.10]
REV62={'wafer-fab-equipment':[.08,.15,.22],'process-control':[.08,.14,.20]}
PB62={'wafer-fab-equipment':[.035,.06,.085],'process-control':[.03,.05,.075]}
def sign(x):return 1 if x>0 else (-1 if x<0 else 0)
def mean(v):v=list(v);return sum(v)/len(v) if v else None
def interval_score(a,l,u,d,alpha=.20):
    s=u-l
    if a<l:s+=(2/alpha)*(l-a)
    elif a>u:s+=(2/alpha)*(a-u)
    return s/abs(d)
def load(benchmark,cases_path):
    with benchmark.open(encoding='utf-8-sig',newline='') as f: rows=list(csv.DictReader(f))
    cases={c['case_id']:c for c in json.loads(cases_path.read_text(encoding='utf-8'))}
    return rows,cases
def calculate(rows,cases):
    by={(r['case_id'],int(r['horizon']),r['metric']):r for r in rows};details=[]
    dirs={}
    for cid,c in cases.items():
        actual=[float(c['base_revenue'])]+[float(x) for x in c['actual_revenue']]
        for version in ('v61','v62'):
            pred=[float(c['base_revenue'])]+[float(x) for x in c[f'{version}_revenue']]
            dirs[(cid,version)]=[sign(pred[i+1]-pred[i])==sign(actual[i+1]-actual[i]) for i in range(3)]
    for r in rows:
        c=cases[r['case_id']];h=int(r['horizon']);i=h-1;a=float(r['actual']);metric=r['metric'];out=dict(r)
        for v in ('v61','v62'):
            p=float(r[v])
            if metric=='revenue':
                hw=(REV61 if v=='v61' else REV62[c['archetype']])[i];lo,hi=p*(1-hw),p*(1+hw);den=a
                out[f'{v}_point_error']=abs(p-a)/abs(a);out[f'{v}_margin_error_pp']=None
                out[f'{v}_direction_correct']=dirs[(r['case_id'],v)][i]
            else:
                rev=by[(r['case_id'],h,'revenue')];pr=float(rev[v]);ar=float(rev['actual'])
                pb=(PB61 if v=='v61' else PB62[c['archetype']])[i];lo,hi=p-pr*pb,p+pr*pb;den=ar
                out[f'{v}_point_error']=None;out[f'{v}_margin_error_pp']=abs(p/pr-a/ar)*100
                out[f'{v}_sign_correct']=sign(p)==sign(a)
            out[f'{v}_low']=lo;out[f'{v}_high']=hi;out[f'{v}_hit']=lo<=a<=hi
            out[f'{v}_interval_score']=interval_score(a,lo,hi,den)
        details.append(out)
    return details
def aggregate(details,split,version):
    ss=[d for d in details if split is None or d['split']==split];rev=[d for d in ss if d['metric']=='revenue'];pro=[d for d in ss if d['metric']=='profit']
    return {'cases':len({d['case_id'] for d in ss}),'revenue_mape':mean(d[f'{version}_point_error'] for d in rev),
    'profit_margin_mae_pp':mean(d[f'{version}_margin_error_pp'] for d in pro),
    'revenue_direction_accuracy':mean(1 if d[f'{version}_direction_correct'] else 0 for d in rev),
    'profit_sign_accuracy':mean(1 if d[f'{version}_sign_correct'] else 0 for d in pro),
    'revenue_coverage':mean(1 if d[f'{version}_hit'] else 0 for d in rev),'profit_coverage':mean(1 if d[f'{version}_hit'] else 0 for d in pro),
    'revenue_interval_score':mean(d[f'{version}_interval_score'] for d in rev),'profit_interval_score':mean(d[f'{version}_interval_score'] for d in pro)}
def main():
    p=argparse.ArgumentParser();p.add_argument('--benchmark',type=Path,required=True);p.add_argument('--cases',type=Path,required=True);p.add_argument('--output-dir',type=Path,required=True);a=p.parse_args();a.output_dir.mkdir(parents=True,exist_ok=True)
    rows,cases=load(a.benchmark,a.cases);details=calculate(rows,cases);metrics={}
    for split in ('calibration','holdout'):metrics[split]={v:aggregate(details,split,v) for v in ('v61','v62')}
    old=metrics['holdout']['v61'];new=metrics['holdout']['v62'];threshold_observations={
    'revenue_mape_le_10pct':new['revenue_mape']<=.10,'profit_margin_mae_le_5pp':new['profit_margin_mae_pp']<=5,
    'direction_ge_85pct':new['revenue_direction_accuracy']>=.85,'profit_sign_ge_90pct':new['profit_sign_accuracy']>=.90,
    'revenue_interval_score_improves_30pct':1-new['revenue_interval_score']/old['revenue_interval_score']>=.30,
    'profit_interval_score_improves_30pct':1-new['profit_interval_score']/old['profit_interval_score']>=.30}
    result={'model_version':'ai-hardware-forecasting-v6.2','generated_at':datetime.now(timezone.utc).isoformat(),'metrics':metrics,
    'limitations':['Retrospective point-in-time simulation, not pre-registered live performance.','Small equipment/process-control sample remains vulnerable to hindsight bias.']}
    write_legacy_backtest_diagnostics(a.output_dir, result, threshold_observations)
    fields=[]
    for d in details:
        for k in d:
            if k not in fields:fields.append(k)
    with (a.output_dir/'detail.csv').open('w',encoding='utf-8-sig',newline='') as f:w=csv.DictWriter(f,fieldnames=fields);w.writeheader();w.writerows(details)
    print(json.dumps(result,ensure_ascii=False,indent=2))
if __name__=='__main__':main()
