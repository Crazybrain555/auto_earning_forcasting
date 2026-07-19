#!/usr/bin/env python3
from __future__ import annotations
import argparse,datetime as dt,hashlib,json,subprocess,sys
from pathlib import Path

def digest(p):
    h=hashlib.sha256()
    with p.open('rb') as f:
        for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
    return h.hexdigest()

def run(cmd):
    r=subprocess.run(cmd,capture_output=True,text=True)
    if r.returncode:print(r.stdout+r.stderr);raise SystemExit(r.returncode)

def main():
    p=argparse.ArgumentParser();p.add_argument('--workspace',required=True);a=p.parse_args();w=Path(a.workspace).resolve();s=Path(__file__).resolve().parent
    if (w/'forecast_seal.json').exists():raise SystemExit('forecast already sealed')
    run([sys.executable,str(s/'validate_time_boundary.py'),'--workspace',str(w),'--strict'])
    run([sys.executable,str(s/'validate_research_completeness.py'),'--workspace',str(w),'--strict'])
    run([sys.executable,str(s/'validate_delivery.py'),'--workspace',str(w),'--strict'])
    now=dt.datetime.now(dt.timezone.utc).isoformat()
    mode=json.loads((w/'mode_config.json').read_text());mode.update({'phase':'sealed','actuals_retrieval_allowed':True});(w/'mode_config.json').write_text(json.dumps(mode,indent=2)+'\n')
    state=json.loads((w/'training_state.json').read_text());state.update({'phase':'sealed','forecast_sealed_at':now});(w/'training_state.json').write_text(json.dumps(state,indent=2)+'\n')
    snap=json.loads((w/'forecast_snapshot.json').read_text());snap['forecast_sealed_before_actuals']=True;snap['run_mode']='historical_train';(w/'forecast_snapshot.json').write_text(json.dumps(snap,indent=2)+'\n')
    records=[]
    for x in sorted(w.rglob('*')):
        if not x.is_file() or x.name=='forecast_seal.json':continue
        if any(part.lower() in {'evaluation','actuals_vault'} for part in x.relative_to(w).parts):continue
        records.append({'path':x.relative_to(w).as_posix(),'sha256':digest(x),'size_bytes':x.stat().st_size})
    pack=hashlib.sha256(json.dumps(records,sort_keys=True,separators=(',',':')).encode()).hexdigest()
    seal={'sealed_at':now,'status':'sealed_before_actuals','pack_hash':'sha256:'+pack,'files':records}
    (w/'forecast_seal.json').write_text(json.dumps(seal,indent=2)+'\n')
    state['forecast_seal_hash']=seal['pack_hash'];(w/'training_state.json').write_text(json.dumps(state,indent=2)+'\n')
    # Rebuild seal because training_state now contains the seal hash: keep a separate immutable root over all other files.
    records=[]
    for x in sorted(w.rglob('*')):
        if not x.is_file() or x.name=='forecast_seal.json':continue
        if any(part.lower() in {'evaluation','actuals_vault'} for part in x.relative_to(w).parts):continue
        records.append({'path':x.relative_to(w).as_posix(),'sha256':digest(x),'size_bytes':x.stat().st_size})
    pack=hashlib.sha256(json.dumps(records,sort_keys=True,separators=(',',':')).encode()).hexdigest();seal['pack_hash']='sha256:'+pack;seal['files']=records
    (w/'forecast_seal.json').write_text(json.dumps(seal,indent=2)+'\n')
    print(json.dumps(seal,indent=2));return 0
if __name__=='__main__':raise SystemExit(main())
