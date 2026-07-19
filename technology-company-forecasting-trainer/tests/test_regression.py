import subprocess,sys,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
class RegressionTest(unittest.TestCase):
    def test_locked_legacy(self):
        r=subprocess.run([sys.executable,str(ROOT/'scripts/regression_check.py'),'--baseline',str(ROOT/'assets/benchmarks/legacy_v5_forecasts.csv'),'--candidate',str(ROOT/'assets/benchmarks/legacy_v6_regression.csv')],capture_output=True,text=True)
        self.assertEqual(r.returncode,0,r.stdout+r.stderr)
if __name__=='__main__':unittest.main()
