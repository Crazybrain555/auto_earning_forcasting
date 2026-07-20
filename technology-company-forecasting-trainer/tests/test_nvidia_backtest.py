import json,subprocess,sys,tempfile,unittest
from pathlib import Path
SK=Path(__file__).resolve().parents[1]
class NvidiaBacktestTest(unittest.TestCase):
    def test_nvidia_gates(self):
        with tempfile.TemporaryDirectory() as td:
            cmd=[sys.executable,str(SK/'scripts/run_nvidia_backtest.py'),'--benchmark',str(SK/'assets/benchmarks/nvidia_benchmark_v72.csv'),'--cases',str(SK/'assets/benchmarks/nvidia_cases_v72.json'),'--output-dir',td,'--name','nvidia']
            r=subprocess.run(cmd,capture_output=True,text=True)
            self.assertEqual(r.returncode,0,r.stdout+r.stderr)
            obj=json.loads((Path(td)/'metrics.json').read_text())
            self.assertTrue(all(obj['gate_results'].values()))
            self.assertLess(obj['metrics']['holdout']['v72']['revenue_mape'],.08)
            self.assertGreaterEqual(obj['metrics']['distribution']['v72']['profit_coverage'],.8)
if __name__=='__main__':unittest.main()
