import hashlib,json,subprocess,sys,tempfile,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3];SKILL=ROOT/'skills/technology-company-forecasting-trainer'
class TrainingScoreTest(unittest.TestCase):
  def test_sealed_score(self):
    with tempfile.TemporaryDirectory() as td:
      w=Path(td);snap={'outputs':{'year_1':{'revenue_point':100,'revenue_low':90,'revenue_high':110,'profit_point':10,'profit_low':5,'profit_high':15,'point_evaluable':True},'year_2':{'revenue_point':120,'revenue_low':100,'revenue_high':140,'profit_point':12,'profit_low':4,'profit_high':20,'point_evaluable':True},'year_3_distribution':{'revenue_point':130,'revenue_low':80,'revenue_high':180,'profit_point':13,'profit_low':-20,'profit_high':40,'point_evaluable':False}}}
      (w/'forecast_snapshot.json').write_text(json.dumps(snap));h=hashlib.sha256((w/'forecast_snapshot.json').read_bytes()).hexdigest();(w/'forecast_seal.json').write_text(json.dumps({'pack_hash':'sha256:test','files':[{'path':'forecast_snapshot.json','sha256':h}]}))
      actual={'case_id':'T','retrieved_after_seal':True,'retrieved_at':'2026-01-01T00:00:00Z','periods':[{'period':'FY+1','revenue':105,'profit':11},{'period':'FY+2','revenue':118,'profit':10},{'period':'FY+3','revenue':70,'profit':-10}]};ap=w/'actuals.json';ap.write_text(json.dumps(actual))
      r=subprocess.run([sys.executable,str(SKILL/'scripts/score_training_forecast.py'),'--workspace',str(w),'--actuals',str(ap)],capture_output=True,text=True)
      self.assertEqual(r.returncode,0,r.stdout+r.stderr);self.assertTrue(json.loads((w/'evaluation.json').read_text())['hash_verified'])
if __name__=='__main__':unittest.main()
