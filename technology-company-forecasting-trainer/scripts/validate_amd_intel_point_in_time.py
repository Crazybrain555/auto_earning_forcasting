#!/usr/bin/env python3
from __future__ import annotations
import argparse,csv,json
from datetime import datetime,timezone
from pathlib import Path
def dt(x):
    if len(x)==10:x=x+"T23:59:59+00:00"
    if x.endswith("Z"):x=x[:-1]+"+00:00"
    z=datetime.fromisoformat(x)
    return z if z.tzinfo else z.replace(tzinfo=timezone.utc)
def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--cases",required=True);ap.add_argument("--signals",required=True);ap.add_argument("--query-log",required=True)
    a=ap.parse_args()
    cases={c["case_id"]:c for c in json.loads(Path(a.cases).read_text(encoding="utf-8"))}
    with Path(a.signals).open(encoding="utf-8-sig",newline="") as f:signals=list(csv.DictReader(f))
    with Path(a.query_log).open(encoding="utf-8-sig",newline="") as f:queries=list(csv.DictReader(f))
    errors=[]
    for s in signals:
        c=cases.get(s["case_id"])
        if not c:errors.append("unknown case "+s["case_id"]);continue
        # actual-only sources may post-date cutoff; they are validation-only and cannot alter model.
        if s["allowed_use"]!="actual_only" and dt(s["published_at"])>dt(c["cutoff"]):
            errors.append("post-cutoff model source "+s["signal_id"])
    for q in queries:
        c=cases.get(q["case_id"])
        if not c:errors.append("unknown query case "+q["case_id"]);continue
        if dt(q["cutoff"])!=dt(c["cutoff"]):errors.append("cutoff mismatch "+q["query_id"])
        if q["future_outcome_terms_used"].strip().lower() not in {"false","0","no","none",""}:
            errors.append("future query contamination "+q["query_id"])
    if errors:
        print("\n".join(errors));raise SystemExit(2)
    print(f"PASS: {len(signals)} dated signals across {len(cases)} cases")
if __name__=="__main__":main()
