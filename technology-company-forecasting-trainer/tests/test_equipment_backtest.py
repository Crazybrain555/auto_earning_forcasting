import json,subprocess,sys,tempfile,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3];SKILL=ROOT/'skills/technology-company-forecasting-trainer'
class EquipmentBacktestTest(unittest.TestCase):
    def test_gates(self):
        with tempfile.TemporaryDirectory() as td:
            cmd=[sys.executable,str(SKILL/'scripts/run_equipment_backtest.py'),'--benchmark',str(SKILL/'assets/benchmarks/equipment_benchmark_v62.csv'),'--cases',str(SKILL/'assets/benchmarks/equipment_cases_v62.json'),'--output-dir',td]
            subprocess.run(cmd,check=True,capture_output=True,text=True)
            m=json.loads((Path(td)/'metrics.json').read_text())
            self.assertTrue(all(m['gate_results'].values()))
            self.assertLess(m['metrics']['holdout']['v62']['revenue_mape'],.10)
            self.assertLess(m['metrics']['holdout']['v62']['profit_margin_mae_pp'],5)
if __name__=='__main__':unittest.main()
