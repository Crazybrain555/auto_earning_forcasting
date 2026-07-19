#!/usr/bin/env python3
from __future__ import annotations
import argparse,hashlib,json
from datetime import datetime,timezone
from pathlib import Path
def digest(path):
    h=hashlib.sha256()
    with path.open('rb') as f:
        for chunk in iter(lambda:f.read(1024*1024),b''):h.update(chunk)
    return h.hexdigest()
def main():
    p=argparse.ArgumentParser();p.add_argument('input_dir',type=Path);p.add_argument('--output',type=Path,required=True);args=p.parse_args();root=args.input_dir.resolve();files=[]
    for path in sorted(p for p in root.rglob('*') if p.is_file() and p.resolve()!=args.output.resolve()):files.append({'path':str(path.relative_to(root)),'sha256':digest(path),'size_bytes':path.stat().st_size})
    pack=hashlib.sha256(json.dumps(files,sort_keys=True,separators=(',',':')).encode()).hexdigest();manifest={'created_at':datetime.now(timezone.utc).isoformat(),'root':str(root),'pack_hash':'sha256:'+pack,'files':files}
    args.output.parent.mkdir(parents=True,exist_ok=True);args.output.write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n',encoding='utf-8');print(manifest['pack_hash'])
if __name__=='__main__':main()
