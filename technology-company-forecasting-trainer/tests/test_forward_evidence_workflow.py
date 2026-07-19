import json,subprocess,sys,tempfile,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3];SKILL=ROOT/'skills/technology-company-forecasting-trainer'
class T(unittest.TestCase):
 def test_files(self):
  for p in ['references/forward-evidence-and-signal-validation.md','assets/templates/forward_signal_card_template.csv','scripts/validate_point_in_time_sources.py']:self.assertTrue((SKILL/p).exists())
 def test_pit(self):
  c=[sys.executable,str(SKILL/'scripts/validate_point_in_time_sources.py'),'--cases',str(SKILL/'assets/benchmarks/forward_evidence_cases_v74.json'),'--signals',str(SKILL/'assets/benchmarks/forward_evidence_signals_v74.csv'),'--query-log',str(SKILL/'assets/benchmarks/forward_evidence_query_log_v74.csv'),'--independence-map',str(SKILL/'assets/benchmarks/forward_evidence_independence_map_v74.csv')];r=subprocess.run(c,capture_output=True,text=True);self.assertEqual(r.returncode,0,r.stdout+r.stderr)
 def test_backtest(self):
  with tempfile.TemporaryDirectory() as td:
   c=[sys.executable,str(SKILL/'scripts/run_forward_evidence_backtest.py'),'--cases',str(SKILL/'assets/benchmarks/forward_evidence_cases_v74.json'),'--output-dir',td];r=subprocess.run(c,capture_output=True,text=True);self.assertEqual(r.returncode,0,r.stdout+r.stderr);m=json.loads((Path(td)/'metrics.json').read_text());self.assertTrue(all(m['gate_results'].values()))
if __name__=='__main__':unittest.main()
