#!/usr/bin/env python3
from __future__ import annotations
import argparse,csv,json
from pathlib import Path
def load(p):
    with p.open(encoding='utf-8-sig',newline='') as f:return {r['metric']:float(r['value']) for r in csv.DictReader(f)}
def main():
    p=argparse.ArgumentParser();p.add_argument('--baseline',type=Path,required=True);p.add_argument('--candidate',type=Path,required=True);p.add_argument('--tolerance',type=float,default=0.0);a=p.parse_args()
    b=load(a.baseline);c=load(a.candidate);missing=sorted(set(b)-set(c));extra=sorted(set(c)-set(b));diff={k:c[k]-b[k] for k in b.keys()&c.keys() if abs(c[k]-b[k])>a.tolerance}
    result={'baseline_rows':len(b),'candidate_rows':len(c),'missing':missing,'extra':extra,'differences':diff,'max_abs_difference':max([abs(v) for v in diff.values()] or [0.0]),'passed':not missing and not extra and not diff}
    print(json.dumps(result,ensure_ascii=False,indent=2))
    if not result['passed']:raise SystemExit(2)
if __name__=='__main__':main()
