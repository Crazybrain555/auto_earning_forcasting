import json,subprocess,sys,tempfile,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
class BacktestTest(unittest.TestCase):
    def test_gates(self):
        with tempfile.TemporaryDirectory() as td:
            r=subprocess.run([sys.executable,str(ROOT/'scripts/run_backtest.py'),'--benchmark',str(ROOT/'assets/benchmarks/new_value_chain_benchmark.csv'),'--cases',str(ROOT/'assets/benchmarks/new_cases.json'),'--output-dir',td],capture_output=True,text=True)
            self.assertEqual(r.returncode,0,r.stdout+r.stderr)
            data=json.loads((Path(td)/'metrics.json').read_text())
            self.assertTrue(all(data['gate_results'].values()))
if __name__=='__main__':unittest.main()
