#!/usr/bin/env python3
from __future__ import annotations
import argparse,csv,json
from datetime import datetime,timezone
from pathlib import Path
def dt(v):
    if len(v)==10:v+='T23:59:59+00:00'
    if v.endswith('Z'):v=v[:-1]+'+00:00'
    x=datetime.fromisoformat(v);return x if x.tzinfo else x.replace(tzinfo=timezone.utc)
KNOWN_FAMILIES={'official-dialogue','cross-company-official','industry-research','expert-field','sell-side-research','technical-paper-standard','news-event','official-product','measurement','regulatory','official-transaction','anonymous-channel'}
INDEPENDENT_FAMILIES={'industry-research','expert-field','sell-side-research','technical-paper-standard','news-event','measurement'}

def main():
    p=argparse.ArgumentParser();p.add_argument('--workspace',required=True);p.add_argument('--strict',action='store_true');a=p.parse_args();w=Path(a.workspace);errs=[]
    manifest=json.loads((w/'run_manifest.json').read_text(encoding='utf-8'));cut=dt(manifest['as_of']);minsig=int(manifest.get('forward_evidence_min_signals',6 if a.strict else 3));mincl=int(manifest.get('forward_evidence_min_independent_clusters',2))
    for name in ['forward_signal_cards.csv','historical_query_log.csv','source_independence_map.csv']:
        if not (w/name).exists() or (w/name).stat().st_size==0:errs.append('missing '+name)
    if errs:print('\n'.join(errs));raise SystemExit(2)
    with (w/'forward_signal_cards.csv').open(encoding='utf-8-sig',newline='') as f:ss=list(csv.DictReader(f))
    if len(ss)<minsig:errs.append(f'signals {len(ss)}<{minsig}')
    clusters={s.get('independence_cluster','').strip() for s in ss if s.get('independence_cluster','').strip()};families={s.get('source_family','').strip().lower() for s in ss if s.get('source_family')}
    if len(clusters)<mincl:errs.append(f'clusters {len(clusters)}<{mincl}')
    # Technology-trend lane: papers/standards/patents answer WHICH transition
    # lands and WHEN - the 2-5y question that filings cannot. The taxonomy had
    # this family from the start but nothing required it, so three live runs
    # shipped with zero technical sources. Now it is a gate.
    tech_min=int(manifest.get('technology_trend_min_signals', 2 if a.strict else 1))
    tech_rows=[s for s in ss if s.get('source_family','').strip().lower()=='technical-paper-standard']
    if manifest.get('technology_trend_not_applicable'):
        reason=str(manifest.get('technology_trend_not_applicable')).strip()
        if len(reason)<20:
            errs.append('technology_trend_not_applicable must carry a stated reason (>=20 chars) - an empty technical lane is an argued choice, never an omission')
    elif len(tech_rows)<tech_min:
        errs.append(f'technology-trend signals {len(tech_rows)}<{tech_min} - cite papers/standards/patents (family technical-paper-standard) for the assumed technology transition, or set manifest technology_trend_not_applicable with a reason; see references/technology-trend-evidence.md')
    else:
        for s in tech_rows:
            if not str(s.get('model_driver','')).strip():
                errs.append('technical signal '+s.get('signal_id','UNKNOWN')+' has no model_driver - a paper that does not attach to a driver parameter is decoration')
        if not any(str(s.get('evidence_role','')).strip().lower() in {'failure_boundary','feasibility_bound'} for s in tech_rows):
            errs.append('technology lane has no failure_boundary/feasibility_bound signal - state the technical condition that would falsify the assumed transition')

    if a.strict:
        unknown=sorted(families-KNOWN_FAMILIES)
        if unknown:errs.append('unknown source_family slug(s) '+','.join(unknown)+' - use the controlled vocabulary: '+', '.join(sorted(KNOWN_FAMILIES)))
        if len(families&KNOWN_FAMILIES)<3:errs.append('source family diversity <3 (strict)')
        if not (families&INDEPENDENT_FAMILIES):errs.append('no independent (non-official) evidence family - official sources alone cannot carry the forward layer')
    elif len(families)<2:errs.append('source family diversity <2')
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
