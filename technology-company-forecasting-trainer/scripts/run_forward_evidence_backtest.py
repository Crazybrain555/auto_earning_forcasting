#!/usr/bin/env python3
from __future__ import annotations
import argparse,csv,json
from pathlib import Path

from legacy_backtest_diagnostics import write_legacy_backtest_diagnostics

def sign(x): return 1 if x>0 else (-1 if x<0 else 0)
def mean(v):
    v=[x for x in v if x is not None]
    return sum(v)/len(v) if v else None
def score(a,lo,hi,den,alpha):
    s=hi-lo
    if a<lo:s+=(2/alpha)*(lo-a)
    elif a>hi:s+=(2/alpha)*(a-hi)
    return s/abs(den)
def main():
    p=argparse.ArgumentParser();p.add_argument('--cases',required=True);p.add_argument('--output-dir',required=True);a=p.parse_args()
    cases=json.loads(Path(a.cases).read_text(encoding='utf-8'));out=Path(a.output_dir);out.mkdir(parents=True,exist_ok=True);rows=[]
    for c in cases:
        actual_seq=[c['base_revenue']]+c['actual_revenue'];off_seq=[c['base_revenue']]+c['official_revenue'];enh_seq=[c['base_revenue']]+c['enhanced_revenue']
        for i,t in enumerate(c['targets']):
            alpha=.10 if c['confidence'][i]=='90%' else .20
            if 'official_revenue_intervals' in c:
                ori=c['official_revenue_intervals'][i];eri=c['enhanced_revenue_intervals'][i];opi=c['official_profit_intervals'][i];epi=c['enhanced_profit_intervals'][i]
            else:
                orv=c['official_revenue'][i];erv=c['enhanced_revenue'][i]
                ori=[orv*(1-c['official_revenue_half_width'][i]),orv*(1+c['official_revenue_half_width'][i])];eri=[erv*(1-c['enhanced_revenue_half_width'][i]),erv*(1+c['enhanced_revenue_half_width'][i])]
                op=c['official_profit'][i];ep=c['enhanced_profit'][i]
                opi=[op-orv*c['official_profit_margin_band'][i],op+orv*c['official_profit_margin_band'][i]];epi=[ep-erv*c['enhanced_profit_margin_band'][i],ep+erv*c['enhanced_profit_margin_band'][i]]
            for metric,actual,off,enh,oi,ei in [('revenue',c['actual_revenue'][i],c['official_revenue'][i],c['enhanced_revenue'][i],ori,eri),('profit',c['actual_profit'][i],c['official_profit'][i],c['enhanced_profit'][i],opi,epi)]:
                pe=c['point_evaluable'][i];r={'split':c['split'],'evaluation_contract':c['evaluation_contract'],'case_id':c['case_id'],'cutoff':c['cutoff'],'target':t,'horizon':i+1,'metric':metric,'unit':c['unit'],'actual':actual,'official':off,'enhanced':enh,'official_low':oi[0],'official_high':oi[1],'enhanced_low':ei[0],'enhanced_high':ei[1],'official_hit':oi[0]<=actual<=oi[1],'enhanced_hit':ei[0]<=actual<=ei[1],'official_interval_score':score(actual,oi[0],oi[1],c['actual_revenue'][i] if metric=='profit' else actual,alpha),'enhanced_interval_score':score(actual,ei[0],ei[1],c['actual_revenue'][i] if metric=='profit' else actual,alpha),'confidence':c['confidence'][i],'point_evaluable':pe,'human_required':c['human_required'],'source_ids':c['source_ids'],'point_in_time_note':c['point_in_time_note']}
                if metric=='revenue':
                    r['official_point_error']=abs(off-actual)/abs(actual) if pe else None;r['enhanced_point_error']=abs(enh-actual)/abs(actual) if pe else None;r['official_margin_error_pp']=r['enhanced_margin_error_pp']=None;r['official_direction_correct']=sign(off_seq[i+1]-off_seq[i])==sign(actual_seq[i+1]-actual_seq[i]) if pe else None;r['enhanced_direction_correct']=sign(enh_seq[i+1]-enh_seq[i])==sign(actual_seq[i+1]-actual_seq[i]) if pe else None;r['official_sign_correct']=r['enhanced_sign_correct']=None
                else:
                    r['official_point_error']=r['enhanced_point_error']=None;r['official_margin_error_pp']=abs(off/c['official_revenue'][i]-actual/c['actual_revenue'][i])*100 if pe else None;r['enhanced_margin_error_pp']=abs(enh/c['enhanced_revenue'][i]-actual/c['actual_revenue'][i])*100 if pe else None;r['official_sign_correct']=sign(off)==sign(actual) if pe else None;r['enhanced_sign_correct']=sign(enh)==sign(actual) if pe else None;r['official_direction_correct']=r['enhanced_direction_correct']=None
                rows.append(r)
    def met(split,v,point=True):
        ss=[r for r in rows if r['split']==split and (r['point_evaluable'] or not point)];rev=[r for r in ss if r['metric']=='revenue'];pr=[r for r in ss if r['metric']=='profit'];pre='official' if v=='official' else 'enhanced'
        return {'cases':len({r['case_id'] for r in ss}),'revenue_mape':mean([r[f'{pre}_point_error'] for r in rev]),'profit_margin_mae_pp':mean([r[f'{pre}_margin_error_pp'] for r in pr]),'revenue_direction_accuracy':mean([1 if r[f'{pre}_direction_correct'] else 0 for r in rev if r[f'{pre}_direction_correct'] is not None]),'profit_sign_accuracy':mean([1 if r[f'{pre}_sign_correct'] else 0 for r in pr if r[f'{pre}_sign_correct'] is not None]),'revenue_coverage':mean([1 if r[f'{pre}_hit'] else 0 for r in rev]),'profit_coverage':mean([1 if r[f'{pre}_hit'] else 0 for r in pr]),'revenue_interval_score':mean([r[f'{pre}_interval_score'] for r in rev]),'profit_interval_score':mean([r[f'{pre}_interval_score'] for r in pr])}
    result={'metrics':{s:{v:met(s,v,s!='perimeter-break') for v in ['official','enhanced']} for s in ['calibration','holdout','perimeter-break']}}
    h0=result['metrics']['holdout']['official'];h1=result['metrics']['holdout']['enhanced'];p1=result['metrics']['perimeter-break']['enhanced']
    threshold_observations={'holdout_revenue_mape_not_worse':h1['revenue_mape']<=h0['revenue_mape'],'holdout_profit_margin_not_worse':h1['profit_margin_mae_pp']<=h0['profit_margin_mae_pp'],'holdout_revenue_interval_not_worse':h1['revenue_interval_score']<=h0['revenue_interval_score'],'holdout_profit_interval_not_worse':h1['profit_interval_score']<=h0['profit_interval_score'],'perimeter_revenue_coverage':p1['revenue_coverage']>=.8,'perimeter_profit_coverage':p1['profit_coverage']>=.8}
    with (out/'detail.csv').open('w',encoding='utf-8-sig',newline='') as f:w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
    write_legacy_backtest_diagnostics(out, result, threshold_observations)
    print(json.dumps(result,ensure_ascii=False,indent=2))
if __name__=='__main__':main()
