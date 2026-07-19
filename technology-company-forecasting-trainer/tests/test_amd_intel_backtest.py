import json,subprocess,sys,tempfile,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
SKILL=ROOT/"skills/technology-company-forecasting-trainer"
class AMDIntelBacktestTest(unittest.TestCase):
    def test_point_in_time_and_backtest(self):
        pit=[sys.executable,str(SKILL/"scripts/validate_amd_intel_point_in_time.py"),
             "--cases",str(SKILL/"assets/benchmarks/amd_intel_cases_v75.json"),
             "--signals",str(SKILL/"assets/benchmarks/amd_intel_signals_v75.csv"),
             "--query-log",str(SKILL/"assets/benchmarks/amd_intel_query_log_v75.csv")]
        r=subprocess.run(pit,capture_output=True,text=True)
        self.assertEqual(r.returncode,0,r.stdout+r.stderr)
        with tempfile.TemporaryDirectory() as td:
            cmd=[sys.executable,str(SKILL/"scripts/run_amd_intel_backtest.py"),
                 "--cases",str(SKILL/"assets/benchmarks/amd_intel_cases_v75.json"),
                 "--output-dir",td]
            r=subprocess.run(cmd,capture_output=True,text=True)
            self.assertEqual(r.returncode,0,r.stdout+r.stderr)
            m=json.loads((Path(td)/"metrics.json").read_text())
            self.assertTrue(all(m["gate_results"].values()))
            self.assertLess(m["metrics"]["holdout"]["v75"]["revenue_mape"],
                            m["metrics"]["holdout"]["v74"]["revenue_mape"])
    def test_cutoff_known_financial_vintage(self):
        cases=json.loads((SKILL/"assets/benchmarks/amd_intel_cases_v75.json").read_text())
        c=next(x for x in cases if x["case_id"]=="AMD@FY2017")
        self.assertAlmostEqual(c["base_revenue"],5.329)
        self.assertIn("later recast",c["point_in_time_note"].lower())
if __name__=="__main__":unittest.main()
