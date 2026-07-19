#!/usr/bin/env python3
from __future__ import annotations
import argparse,csv,datetime as dt,json,re
from pathlib import Path

def parse(v):
    v=str(v or '').strip()
    if not v: raise ValueError('missing date')
    if len(v)==10: v += 'T23:59:59Z'
    if v.endswith('Z'): v=v[:-1]+'+00:00'
    x=dt.datetime.fromisoformat(v)
    if x.tzinfo is None:x=x.replace(tzinfo=dt.timezone.utc)
    return x.astimezone(dt.timezone.utc)

def csv_rows(path):
    if not path.exists(): return []
    with path.open(encoding='utf-8-sig',newline='') as f:return list(csv.DictReader(f))

def main():
    p=argparse.ArgumentParser();p.add_argument('--workspace',required=True);p.add_argument('--strict',action='store_true');a=p.parse_args()
    w=Path(a.workspace);checks=[];errors=[];warnings=[]
    def add(name,passed,detail='',severity='error'):
        rec={'check':name,'passed':passed,'detail':detail,'severity':'info' if passed else severity};checks.append(rec)
        if not passed:(errors if severity=='error' else warnings).append(rec)
    mpath=w/'mode_config.json'
    if not mpath.exists():
        add('mode-config',False,'missing mode_config.json');mode={}
    else:
        try:mode=json.loads(mpath.read_text());add('mode-config',True)
        except Exception as e:add('mode-config',False,str(e));mode={}
    run_mode=mode.get('run_mode','live_forecast')
    if run_mode!='historical_train':
        add('mode',True,f'{run_mode}: historical cutoff gate not active')
        result={'workspace':str(w),'run_mode':run_mode,'passed':not errors,'errors':len(errors),'warnings':len(warnings),'checks':checks}
        (w/'time_boundary_validation.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2));return 0 if not errors else 2
    try:cutoff=parse(mode.get('as_of'));add('historical-cutoff',True,cutoff.isoformat())
    except Exception as e:add('historical-cutoff',False,str(e));cutoff=None
    phase=mode.get('phase','forecast');actual_allowed=bool(mode.get('actuals_retrieval_allowed',False))
    if phase in {'forecast','candidate_revision','calibration','untouched_holdout'} and actual_allowed:
        add('actuals-gate',False,f'actuals_retrieval_allowed=true during {phase}')
    else:add('actuals-gate',True,f'phase={phase}, allowed={actual_allowed}')
    forbidden=[str(x).lower() for x in mode.get('forbidden_query_terms',[]) if str(x).strip()]
    assumptions=csv_rows(w/'assumption_register.csv');signals=csv_rows(w/'forward_signal_cards.csv')
    used=set()
    for r in assumptions:
        used.update(x.strip() for x in re.split(r'[;,| ]+',str(r.get('source_ids',''))) if x.strip())
    for r in signals:
        if str(r.get('allowed_use','')).lower() not in {'quarantine','monitor','monitor-only','actual_only'}:
            if r.get('source_id'):used.add(str(r['source_id']).strip())
    srcpath=w/'source_manifest.json'
    sources=[]
    if srcpath.exists():
        try:sources=json.loads(srcpath.read_text()).get('sources',[])
        except Exception as e:add('source-manifest',False,str(e))
    else:add('source-manifest',False,'missing')
    for s in sources:
        sid=str(s.get('source_id','UNKNOWN'));status=str(s.get('source_time_status','')).lower()
        date=s.get('version_at') or s.get('published_at')
        try:future=cutoff is not None and parse(date)>cutoff
        except Exception:
            future=True;status=status or 'quarantined_unknown_date'
        quarantined=status.startswith('quarantined') or str(s.get('forecast_permission','')).lower() in {'quarantine','none','audit-only'}
        if future and (not quarantined or sid in used):add('source-cutoff:'+sid,False,f'date={date}, status={status}, used={sid in used}')
        else:add('source-cutoff:'+sid,True,f'date={date}, status={status or "eligible_pre_cutoff"}')
    for r in signals:
        sid=str(r.get('signal_id','UNKNOWN'))
        try:future=cutoff is not None and parse(r.get('published_at'))>cutoff
        except Exception:future=True
        if future and str(r.get('allowed_use','')).lower() not in {'quarantine','monitor','actual_only'}:add('signal-cutoff:'+sid,False,str(r.get('published_at')))
    for r in csv_rows(w/'historical_query_log.csv'):
        qid=str(r.get('query_id','UNKNOWN'));q=str(r.get('query_text','')).lower()
        flag=str(r.get('future_outcome_terms_used','')).strip().lower()
        if flag not in {'','false','0','no','none'}:add('query-future-flag:'+qid,False,flag)
        bad=[x for x in forbidden if x in q]
        if bad:add('query-forbidden:'+qid,False,','.join(bad))
        try:
            if cutoff is not None and parse(r.get('cutoff'))!=cutoff:add('query-cutoff:'+qid,False,str(r.get('cutoff')))
        except Exception:add('query-cutoff:'+qid,False,'invalid/missing cutoff')
    if phase in {'forecast','candidate_revision','calibration','untouched_holdout'}:
        leaking=[]
        for path in w.rglob('*'):
            if not path.is_file():continue
            n=path.name.lower()
            if any(x in n for x in ['actuals','evaluation','score']) and path.name not in {'training_actuals_template.json'}:
                leaking.append(str(path.relative_to(w)))
        if leaking:add('pre-seal-actual-files',False,', '.join(leaking[:20]))
        else:add('pre-seal-actual-files',True)
    result={'workspace':str(w),'run_mode':run_mode,'phase':phase,'as_of':mode.get('as_of'),'passed':not errors,'errors':len(errors),'warnings':len(warnings),'checks':checks}
    (w/'time_boundary_validation.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(result,ensure_ascii=False,indent=2));return 0 if not errors else 2
if __name__=='__main__':raise SystemExit(main())
