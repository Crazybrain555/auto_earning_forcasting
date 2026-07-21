import subprocess,sys,unittest
import pytest
from pathlib import Path
pytestmark = pytest.mark.diagnostic_benchmark
SKILL=Path(__file__).resolve().parents[1]
class ScopeRegressionTest(unittest.TestCase):
    def test_sandisk_zero_delta(self):
        cmd=[sys.executable,str(SKILL/'scripts/scope_regression_check.py'),'--baseline',str(SKILL/'assets/benchmarks/sandisk_scope_baseline_v61.csv'),'--candidate',str(SKILL/'assets/benchmarks/sandisk_scope_candidate_v62.csv')]
        subprocess.run(cmd,check=True,capture_output=True,text=True)
if __name__=='__main__':unittest.main()
