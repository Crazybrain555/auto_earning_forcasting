import json, subprocess, sys, tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]


def test_mechanism_outcomes_are_a_diagnostic_vector_not_a_threshold_gate():
    with tempfile.TemporaryDirectory() as td:
        w=Path(td)
        pred={'outcomes':[{'outcome_id':'x','required':True,'activation':'active','direction':'up','state':'ramp','timing_period':2,'magnitude_low':8,'magnitude_high':12,'financial_line':'revenue','cash_classification':'operating'}]}
        act={'outcomes':[{'outcome_id':'x','activation':'active','direction':'up','state':'ramp','timing_period':2,'magnitude':10,'financial_line':'revenue','cash_classification':'operating'}]}
        # A diagnostic mismatch must remain visible without being collapsed
        # into PASS/PARTIAL/FAIL by an arbitrary contract threshold.
        act['outcomes'][0]['direction'] = 'down'
        for n,o in [('p',pred),('a',act)]: (w/f'{n}.json').write_text(json.dumps(o))
        r=subprocess.run([sys.executable,str(ROOT/'scripts/score_mechanism_outcomes.py'),'--predictions',str(w/'p.json'),'--actuals',str(w/'a.json'),'--output',str(w/'out.json')],capture_output=True,text=True)
        assert r.returncode==0, r.stdout+r.stderr
        result=json.loads((w/'out.json').read_text())
        assert result['metrics']['direction_accuracy'] == 0.0
        assert result['rows'][0]['direction_correct'] is False
        assert 'right_reason_status' not in result
        assert 'checks' not in result
        assert 'independent reviewer' in result['interpretation']
