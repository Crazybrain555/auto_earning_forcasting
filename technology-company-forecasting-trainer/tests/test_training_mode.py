import csv,json,subprocess,sys,tempfile,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3];SKILL=ROOT/'skills/technology-company-forecasting-trainer'
class TrainingModeTest(unittest.TestCase):
  def test_cutoff_blocks_used_future_source(self):
    with tempfile.TemporaryDirectory() as td:
      w=Path(td);(w/'mode_config.json').write_text(json.dumps({'run_mode':'historical_train','phase':'forecast','as_of':'2020-01-31T23:59:59Z','actuals_retrieval_allowed':False,'forbidden_query_terms':['fy2021 actual']}))
      (w/'source_manifest.json').write_text(json.dumps({'as_of':'2020-01-31T23:59:59Z','sources':[{'source_id':'FUT','published_at':'2020-02-01T00:00:00Z','source_time_status':'eligible_pre_cutoff','forecast_permission':'eligible'}]}))
      with (w/'assumption_register.csv').open('w',newline='') as f:csv.writer(f).writerows([['source_ids'],['FUT']])
      with (w/'forward_signal_cards.csv').open('w',newline='') as f:csv.writer(f).writerow(['signal_id','source_id','published_at','allowed_use'])
      with (w/'historical_query_log.csv').open('w',newline='') as f:csv.writer(f).writerows([['query_id','cutoff','query_text','future_outcome_terms_used'],['Q1','2020-01-31T23:59:59Z','normal historical query','false']])
      r=subprocess.run([sys.executable,str(SKILL/'scripts/validate_time_boundary.py'),'--workspace',str(w),'--strict'],capture_output=True,text=True)
      self.assertNotEqual(r.returncode,0)
  def test_live_mode_passes_without_historical_gate(self):
    with tempfile.TemporaryDirectory() as td:
      w=Path(td);(w/'mode_config.json').write_text(json.dumps({'run_mode':'live_forecast','phase':'forecast'}))
      r=subprocess.run([sys.executable,str(SKILL/'scripts/validate_time_boundary.py'),'--workspace',str(w),'--strict'],capture_output=True,text=True)
      self.assertEqual(r.returncode,0,r.stdout+r.stderr)
if __name__=='__main__':unittest.main()
