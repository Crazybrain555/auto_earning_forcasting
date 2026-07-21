import csv,json,subprocess,sys,tempfile,unittest
from pathlib import Path
SKILL=Path(__file__).resolve().parents[1]
class T(unittest.TestCase):
 def test_files(self):
  for p in ['references/forward-evidence-and-signal-validation.md','assets/templates/forward_signal_card_template.csv','scripts/validate_point_in_time_sources.py']:self.assertTrue((SKILL/p).exists())
 def test_pit(self):
  c=[sys.executable,str(SKILL/'scripts/validate_point_in_time_sources.py'),'--cases',str(SKILL/'assets/benchmarks/forward_evidence_cases_v74.json'),'--signals',str(SKILL/'assets/benchmarks/forward_evidence_signals_v74.csv'),'--query-log',str(SKILL/'assets/benchmarks/forward_evidence_query_log_v74.csv'),'--independence-map',str(SKILL/'assets/benchmarks/forward_evidence_independence_map_v74.csv')];r=subprocess.run(c,capture_output=True,text=True);self.assertEqual(r.returncode,0,r.stdout+r.stderr)
 def test_one_direct_base_anchor_is_not_rejected_by_a_source_count(self):
  with tempfile.TemporaryDirectory() as td:
   root=Path(td);cases=root/'cases.json';signals=root/'signals.csv'
   cases.write_text(json.dumps([{'case_id':'ONE','cutoff':'2026-07-18','point_evaluable':[True],'forbidden_future_tokens':[]}]),encoding='utf-8')
   with signals.open('w',encoding='utf-8-sig',newline='') as f:
    w=csv.DictWriter(f,fieldnames=['signal_id','case_id','source_id','published_at','source_family','evidence_tier','evidence_role','independence_cluster','allowed_use','model_impact','limitations'])
    w.writeheader();w.writerow({'signal_id':'ONE-S1','case_id':'ONE','source_id':'FILING','published_at':'2026-07-01','source_family':'official-dialogue','evidence_tier':'E1','evidence_role':'fact_anchor','independence_cluster':'ISSUER','allowed_use':'base_driver','model_impact':'named demand node','limitations':'management scope bounded'})
   r=subprocess.run([sys.executable,str(SKILL/'scripts/validate_point_in_time_sources.py'),'--cases',str(cases),'--signals',str(signals)],capture_output=True,text=True)
   self.assertEqual(r.returncode,0,r.stdout+r.stderr)
 def test_boundary_role_not_family_keyword_controls_base_permission(self):
  with tempfile.TemporaryDirectory() as td:
   root=Path(td);cases=root/'cases.json';signals=root/'signals.csv'
   cases.write_text(json.dumps([{'case_id':'BOUND','cutoff':'2026-07-18','point_evaluable':[True],'forbidden_future_tokens':[]}]),encoding='utf-8')
   with signals.open('w',encoding='utf-8-sig',newline='') as f:
    w=csv.DictWriter(f,fieldnames=['signal_id','case_id','source_id','published_at','source_family','evidence_tier','evidence_role','independence_cluster','allowed_use','model_impact','limitations'])
    w.writeheader();w.writerow({'signal_id':'BOUND-S1','case_id':'BOUND','source_id':'PAPER','published_at':'2026-07-01','source_family':'official-dialogue','evidence_tier':'E2','evidence_role':'failure_boundary','independence_cluster':'LAB','allowed_use':'base_driver','model_impact':'named yield node','limitations':'technical boundary only'})
   r=subprocess.run([sys.executable,str(SKILL/'scripts/validate_point_in_time_sources.py'),'--cases',str(cases),'--signals',str(signals)],capture_output=True,text=True)
   self.assertNotEqual(r.returncode,0,r.stdout+r.stderr)
   self.assertIn('boundary-to-base',r.stdout+r.stderr)
if __name__=='__main__':unittest.main()
