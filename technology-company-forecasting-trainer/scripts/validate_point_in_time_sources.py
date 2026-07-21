#!/usr/bin/env python3
from __future__ import annotations
import argparse,csv,json
from datetime import datetime,timezone
from pathlib import Path
def dt(v):
    if len(v)==10:v+='T23:59:59+00:00'
    if v.endswith('Z'):v=v[:-1]+'+00:00'
    x=datetime.fromisoformat(v);return x if x.tzinfo else x.replace(tzinfo=timezone.utc)
def main():
    p=argparse.ArgumentParser();p.add_argument('--cases',required=True);p.add_argument('--signals',required=True);p.add_argument('--query-log');p.add_argument('--independence-map');a=p.parse_args();cases={c['case_id']:c for c in json.loads(Path(a.cases).read_text(encoding='utf-8'))}
    with Path(a.signals).open(encoding='utf-8-sig',newline='') as f:ss=list(csv.DictReader(f));errs=[]
    for s in ss:
        c=cases.get(s['case_id'])
        if not c:errs.append('unknown '+s['case_id']);continue
        if dt(s['published_at'])>dt(c['cutoff']):errs.append('post-cutoff '+s['signal_id'])
        text=' '.join([s.get('source_id',''),s.get('model_impact',''),s.get('limitations','')]).lower()
        for token in c.get('forbidden_future_tokens',[]):
            if token.lower() in text:errs.append('future token '+token+' in '+s['signal_id'])
        role=s.get('evidence_role','').strip().lower();allowed=s['allowed_use'].lower()
        if role in {'failure_boundary','feasibility_bound','technical_bound'} and allowed in {'base_point','base_driver','base_parameter'}:errs.append('boundary-to-base '+s['signal_id'])
        if s['evidence_tier']=='E4' and allowed not in {'monitor','monitor_trigger'}:errs.append('E4 permission '+s['signal_id'])
    if a.query_log:
        with Path(a.query_log).open(encoding='utf-8-sig',newline='') as f:qs=list(csv.DictReader(f))
        for q in qs:
            c=cases.get(q.get('case_id',''))
            if not c:errs.append('unknown query '+q.get('query_id',''));continue
            if dt(q.get('cutoff',''))!=dt(c['cutoff']):errs.append('query cutoff '+q.get('query_id',''))
            if str(q.get('future_outcome_terms_used','')).strip().lower() not in {'','false','0','no','none'}:errs.append('query contamination '+q.get('query_id',''))
    if a.independence_map:
        with Path(a.independence_map).open(encoding='utf-8-sig',newline='') as f:im=list(csv.DictReader(f))
        mapped={r['cluster_id'].strip() for r in im if r.get('cluster_id')};needed={s['independence_cluster'].strip() for s in ss if s.get('independence_cluster')};missing=needed-mapped
        if missing:errs.append('unmapped '+','.join(sorted(missing)))
    if errs:
        print('\n'.join('FAIL: '+e for e in errs));raise SystemExit(2)
    print(f'PASS: {len(ss)} pre-cutoff signals across {len(cases)} cases')
if __name__=='__main__':main()
