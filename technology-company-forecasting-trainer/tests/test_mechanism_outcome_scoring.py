import json, subprocess, sys, tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]


def test_mechanism_score_requires_right_reason():
    with tempfile.TemporaryDirectory() as td:
        w=Path(td)
        pred={'outcomes':[{'outcome_id':'x','required':True,'activation':'active','direction':'up','state':'ramp','timing_period':2,'magnitude_low':8,'magnitude_high':12,'financial_line':'revenue','cash_classification':'operating'}]}
        act={'outcomes':[{'outcome_id':'x','activation':'active','direction':'up','state':'ramp','timing_period':2,'magnitude':10,'financial_line':'revenue','cash_classification':'operating'}]}
        con={'metrics':{'required_coverage':{'minimum':1},'activation_accuracy':{'minimum':1},'direction_accuracy':{'minimum':1},'state_accuracy':{'minimum':1},'magnitude_band_coverage':{'minimum':1},'financial_line_accuracy':{'minimum':1}}}
        for n,o in [('p',pred),('a',act),('c',con)]: (w/f'{n}.json').write_text(json.dumps(o))
        r=subprocess.run([sys.executable,str(ROOT/'scripts/score_mechanism_outcomes.py'),'--predictions',str(w/'p.json'),'--actuals',str(w/'a.json'),'--contract',str(w/'c.json'),'--output',str(w/'out.json')],capture_output=True,text=True)
        assert r.returncode==0, r.stdout+r.stderr
        assert json.loads((w/'out.json').read_text())['right_reason_status']=='PASS'
