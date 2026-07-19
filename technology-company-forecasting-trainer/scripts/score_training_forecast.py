#!/usr/bin/env python3
from __future__ import annotations
import argparse,datetime as dt,hashlib,json,math
from pathlib import Path

def digest(p):
    h=hashlib.sha256();h.update(p.read_bytes());return h.hexdigest()
def interval_score(a,lo,hi,den,alpha=.2):
    s=hi-lo
    if a<lo:s+=(2/alpha)*(lo-a)
    elif a>hi:s+=(2/alpha)*(a-hi)
    return s/abs(den)
def output_for(snapshot,period):
    if snapshot.get('historical_forecasts'):
        return next(x for x in snapshot['historical_forecasts'] if x.get('period')==period)
    key={'FY+1':'year_1','FY+2':'year_2','FY+3':'year_3_distribution'}[period]
    return snapshot['outputs'][key]
def val(o,*names):
    for n in names:
        if n in o and o[n] is not None:return float(o[n])
    return None
def main():
    p=argparse.ArgumentParser();p.add_argument('--workspace',required=True);p.add_argument('--actuals',required=True);p.add_argument('--output',default=None);a=p.parse_args();w=Path(a.workspace);seal=json.loads((w/'forecast_seal.json').read_text())
    changed=[]
    for r in seal['files']:
        x=w/r['path']
        if not x.exists() or digest(x)!=r['sha256']:changed.append(r['path'])
    if changed:raise SystemExit('sealed files changed: '+','.join(changed))
    actuals=json.loads(Path(a.actuals).read_text());
    if not actuals.get('retrieved_after_seal'):raise SystemExit('actuals must be marked retrieved_after_seal')
    snap=json.loads((w/'forecast_snapshot.json').read_text());rows=[]
    for act in actuals['periods']:
        period=act['period'];o=output_for(snap,period);rev=float(act['revenue']);profit=float(act['profit'])
        rp=val(o,'revenue_point','revenue');rl=val(o,'revenue_low');rh=val(o,'revenue_high');pp=val(o,'profit_point','net_income','profit');pl=val(o,'profit_low');ph=val(o,'profit_high')
        point=bool(o.get('point_evaluable',period!='FY+3'));alpha=.2 if point else .1
        rec={'period':period,'point_evaluable':point,'actual_revenue':rev,'forecast_revenue':rp,'actual_profit':profit,'forecast_profit':pp}
        if point:
            rec['revenue_ape']=abs(rp-rev)/abs(rev);rec['profit_margin_error_pp']=abs(pp/rp-profit/rev)*100
        if rl is not None and rh is not None:
            rec['revenue_hit']=rl<=rev<=rh;rec['revenue_interval_score']=interval_score(rev,rl,rh,rev,alpha)
        if pl is not None and ph is not None:
            rec['profit_hit']=pl<=profit<=ph;rec['profit_interval_score']=interval_score(profit,pl,ph,rev,alpha)
        rows.append(rec)
    pts=[r for r in rows if r['point_evaluable']]
    def mean(k):
        v=[r[k] for r in pts if k in r];return sum(v)/len(v) if v else None
    metrics={'revenue_mape':mean('revenue_ape'),'profit_margin_mae_pp':mean('profit_margin_error_pp'),'revenue_coverage':mean('revenue_hit'),'profit_coverage':mean('profit_hit'),'revenue_interval_score':mean('revenue_interval_score'),'profit_interval_score':mean('profit_interval_score')}
    result={'case_id':actuals.get('case_id'),'seal_hash':seal['pack_hash'],'hash_verified':True,'actuals_retrieved_after_seal':True,'metrics':metrics,'scores':rows}
    out=Path(a.output) if a.output else w/'evaluation.json';out.parent.mkdir(parents=True,exist_ok=True);out.write_text(json.dumps(result,indent=2)+'\n')
    state_path=w/'training_state.json'
    if state_path.exists():
        state=json.loads(state_path.read_text());state.update({'phase':'evaluate','actuals_retrieved_at':actuals.get('retrieved_at') or dt.datetime.now(dt.timezone.utc).isoformat(),'evaluation_path':str(out)});state_path.write_text(json.dumps(state,indent=2)+'\n')
    print(json.dumps(result,indent=2));return 0
if __name__=='__main__':raise SystemExit(main())
