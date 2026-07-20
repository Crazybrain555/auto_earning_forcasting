import json,subprocess,sys,tempfile,unittest
from pathlib import Path
SKILL=Path(__file__).resolve().parents[1]
class MarvellBacktestTest(unittest.TestCase):
 def test_gates(self):
  with tempfile.TemporaryDirectory() as td:
   cmd=[sys.executable,str(SKILL/'scripts/run_marvell_backtest.py'),'--benchmark',str(SKILL/'assets/benchmarks/marvell_benchmark_v63.csv'),'--cases',str(SKILL/'assets/benchmarks/marvell_cases_v63.json'),'--output-dir',td]
   subprocess.run(cmd,check=True,capture_output=True,text=True);m=json.loads((Path(td)/'metrics.json').read_text());self.assertTrue(all(m['gate_results'].values()));self.assertLess(m['metrics']['holdout']['v63']['revenue_mape'],.08);self.assertTrue(m['metrics']['perimeter_break']['v63']['point_metrics_not_gated'])
if __name__=='__main__':unittest.main()
