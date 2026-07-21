#!/usr/bin/env python3
"""Scaffold one historical training/validation case workspace.

Wraps scaffold_historical_delivery.py and stamps round/case
bookkeeping. Roles: development (training group), validation (untouched
until its validation pass), regression (re-run of a previously used case).
"""
from __future__ import annotations
import argparse, json, subprocess, sys
from pathlib import Path

def main():
    p = argparse.ArgumentParser()
    p.add_argument('--workspace', required=True)
    p.add_argument('--entity', required=True)
    p.add_argument('--security', required=True)
    p.add_argument('--as-of', required=True)
    p.add_argument('--round-id', required=True, help='e.g. round-3')
    p.add_argument('--case-id', required=True, help='e.g. MU@2020-01-31')
    p.add_argument('--case-role', choices=['development', 'validation', 'regression'], required=True)
    p.add_argument('--method-commit', default='UNSET', help='git commit of the skills repo used for this run')
    p.add_argument('--forbidden-query-term', action='append', default=[])
    a = p.parse_args()
    scripts = Path(__file__).resolve().parent
    w = Path(a.workspace).resolve()
    cmd = [sys.executable, str(scripts / 'scaffold_historical_delivery.py'), '--workspace', str(w), '--entity', a.entity,
           '--security', a.security, '--as-of', a.as_of, '--mode', 'historical_train',
           '--purpose', 'historical training forecast']
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode:
        print(r.stdout + r.stderr)
        return r.returncode
    as_of = a.as_of if 'T' in a.as_of else a.as_of + 'T23:59:59Z'
    mode = json.loads((w / 'mode_config.json').read_text())
    mode.update({'run_mode': 'historical_train', 'phase': 'forecast', 'as_of': as_of,
                 'enforce_source_cutoff': True, 'actuals_retrieval_allowed': False,
                 'open_web_after_seal_for_actuals': True, 'forbidden_query_terms': a.forbidden_query_term})
    (w / 'mode_config.json').write_text(json.dumps(mode, indent=2) + '\n')
    state = json.loads((w / 'training_state.json').read_text())
    state.update({'round_id': a.round_id, 'case_id': a.case_id, 'case_role': a.case_role,
                  'phase': 'forecast', 'method_commit': a.method_commit})
    (w / 'training_state.json').write_text(json.dumps(state, indent=2) + '\n')
    manifest = json.loads((w / 'run_manifest.json').read_text())
    manifest.update({'run_mode': 'historical_train', 'time_boundary_enforced': True,
                     'training_round_id': a.round_id, 'training_case_role': a.case_role,
                     'method_commit': a.method_commit})
    (w / 'run_manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
    print(json.dumps({'workspace': str(w), 'mode': 'historical_train', 'case_role': a.case_role,
                      'round_id': a.round_id, 'actuals_retrieval_allowed': False}, indent=2))
    return 0

if __name__ == '__main__':
    raise SystemExit(main())
