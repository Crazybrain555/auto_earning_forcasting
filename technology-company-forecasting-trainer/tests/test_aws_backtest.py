import json,subprocess,sys,tempfile,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3];SKILL=ROOT/'skills/technology-company-forecasting-trainer'
class AwsBacktestTest(unittest.TestCase):
    def test_aws_gates(self):
        with tempfile.TemporaryDirectory() as td:
            cmd=[sys.executable,str(SKILL/'scripts/run_aws_backtest.py'),'--benchmark',str(SKILL/'assets/benchmarks/aws_benchmark_v71.csv'),'--cases',str(SKILL/'assets/benchmarks/aws_cases_v71.json'),'--output-dir',td]
            r=subprocess.run(cmd,capture_output=True,text=True)
            self.assertEqual(r.returncode,0,r.stdout+r.stderr)
            obj=json.loads((Path(td)/'metrics.json').read_text())
            self.assertTrue(all(obj['gate_results'].values()))
            self.assertLessEqual(obj['metrics']['holdout']['v71']['revenue_mape'],.08)
            self.assertLessEqual(obj['metrics']['holdout']['v71']['profit_margin_mae_pp'],4)
if __name__=='__main__':unittest.main()
