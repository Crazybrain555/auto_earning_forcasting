#!/usr/bin/env python3
from __future__ import annotations
import argparse,json
from datetime import datetime
from pathlib import Path
REQUIRED=['case_id','entity','as_of','currency','fiscal_calendar','horizons','source_ids','assumptions','forecast']

def validate(obj):
    errors=[]
    for k in REQUIRED:
        if k not in obj:errors.append(f'missing required field: {k}')
    if errors:return errors
    try:datetime.fromisoformat(obj['as_of'].replace('Z','+00:00'))
    except Exception:errors.append('as_of must be ISO-8601')
    routes=obj.get('mechanisms') or obj.get('archetypes') or []
    if not routes:errors.append('mechanisms must not be empty (legacy archetypes accepted for benchmark compatibility)')
    total=0.0
    for a in routes:
        if 'name' not in a or 'weight' not in a:errors.append('each mechanism needs name and weight')
        else:total+=float(a['weight'])
    if routes and abs(total-1)>1e-6:errors.append(f'mechanism weights must sum to 1; got {total}')
    if not obj.get('horizons'):errors.append('horizons must not be empty')
    return errors

def main():
    p=argparse.ArgumentParser();p.add_argument('case',type=Path);args=p.parse_args()
    obj=json.loads(args.case.read_text(encoding='utf-8'));errors=validate(obj)
    print(json.dumps({'valid':not errors,'errors':errors},ensure_ascii=False,indent=2))
    if errors:raise SystemExit(2)
if __name__=='__main__':main()
