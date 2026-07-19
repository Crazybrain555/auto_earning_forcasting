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
    p=argparse.ArgumentParser();p.add_argument('--workspace',required=True);p.add_argument('--strict',action='store_true');a=p.parse_args();w=Path(a.workspace);errs=[]
    manifest=json.loads((w/'run_manifest.json').read_text(encoding='utf-8'));cut=dt(manifest['as_of']);minsig=int(manifest.get('forward_evidence_min_signals',3));mincl=int(manifest.get('forward_evidence_min_independent_clusters',2))
    for name in ['forward_signal_cards.csv','historical_query_log.csv','source_independence_map.csv']:
        if not (w/name).exists() or (w/name).stat().st_size==0:errs.append('missing '+name)
    if errs:print('\n'.join(errs));raise SystemExit(2)
    with (w/'forward_signal_cards.csv').open(encoding='utf-8-sig',newline='') as f:ss=list(csv.DictReader(f))
    if len(ss)<minsig:errs.append(f'signals {len(ss)}<{minsig}')
    clusters={s.get('independence_cluster','').strip() for s in ss if s.get('independence_cluster','').strip()};families={s.get('source_family','').strip().lower() for s in ss if s.get('source_family')}
    if len(clusters)<mincl:errs.append(f'clusters {len(clusters)}<{mincl}')
    if len(families)<2:errs.append('source family diversity <2')
    base=[s for s in ss if s.get('allowed_use','').lower() in {'base_point','base_driver'}]
    direct={'official-dialogue','cross-company-official','industry-research','official-product','measurement','regulatory','official-transaction'}
    bclusters={s.get('independence_cluster','').strip() for s in base if s.get('independence_cluster')}
    if base and (len(bclusters)<2 or not any(s.get('source_family','').lower() in direct for s in base)):errs.append('Base permission gate failed')
    for s in ss:
        sid=s.get('signal_id','UNKNOWN');fam=s.get('source_family','').lower();allowed=s.get('allowed_use','').lower();tier=s.get('evidence_tier','').upper()
        try:
            if dt(s.get('published_at',''))>cut:errs.append('future signal '+sid)
        except:errs.append('invalid date '+sid)
        if ('technical' in fam or 'paper' in fam or 'standard' in fam) and allowed in {'base_point','base_driver'}:errs.append('technical-to-base '+sid)
        if tier=='E4' and allowed not in {'monitor','monitor_trigger'}:errs.append('E4 permission '+sid)
    with (w/'historical_query_log.csv').open(encoding='utf-8-sig',newline='') as f:qs=list(csv.DictReader(f))
    if len(qs)<3:errs.append('query log <3')
    for q in qs:
        if str(q.get('future_outcome_terms_used','')).strip().lower() not in {'','false','0','no','none'}:errs.append('query contamination '+q.get('query_id',''))
        try:
            if dt(q.get('cutoff',''))!=cut:errs.append('query cutoff '+q.get('query_id',''))
        except:errs.append('invalid query cutoff '+q.get('query_id',''))
    with (w/'source_independence_map.csv').open(encoding='utf-8-sig',newline='') as f:im=list(csv.DictReader(f))
    mapped={r.get('cluster_id','').strip() for r in im if r.get('cluster_id')};missing=clusters-mapped
    if missing:errs.append('unmapped clusters '+','.join(sorted(missing)))
    report=(w/'report.md').read_text(encoding='utf-8').lower() if (w/'report.md').exists() else ''
    if not any(x in report for x in ['forward evidence','前瞻证据','研究综合']):errs.append('report lacks forward evidence section')
    red=(w/'red_team.md').read_text(encoding='utf-8').lower() if (w/'red_team.md').exists() else ''
    if not any(x in red for x in ['source independence','independence cluster','来源独立','来源簇','重复引用']):errs.append('red team lacks source independence')
    if errs:
        print('\n'.join('FAIL: '+e for e in errs));raise SystemExit(2)
    print(f'PASS: forward evidence workspace signals={len(ss)} clusters={len(clusters)} families={len(families)}')
if __name__=='__main__':main()
