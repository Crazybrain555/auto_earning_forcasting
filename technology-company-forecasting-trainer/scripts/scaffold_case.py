#!/usr/bin/env python3
from __future__ import annotations
import argparse,json
from pathlib import Path

def main():
    p=argparse.ArgumentParser()
    p.add_argument('--output',type=Path,required=True)
    p.add_argument('--entity',required=True)
    p.add_argument('--as-of',required=True)
    p.add_argument('--mechanism',required=True)
    p.add_argument('--lens',action='append',default=[])
    args=p.parse_args()
    root=Path(__file__).resolve().parents[1]
    tpl=json.loads((root/'assets/templates/case_template.json').read_text(encoding='utf-8'))
    tpl['case_id']=f"{args.entity.replace(' ','-')}@{args.as_of}"
    tpl['entity']=args.entity
    tpl['as_of']=args.as_of+'T00:00:00Z' if 'T' not in args.as_of else args.as_of
    tpl['mechanisms']=[{'name':args.mechanism,'weight':1.0,'validation_status':'check validated-coverage.md'}]
    tpl['company_lenses']=args.lens
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(tpl,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(args.output)
if __name__=='__main__':main()
