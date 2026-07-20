import subprocess,sys,unittest
from pathlib import Path
SKILL=Path(__file__).resolve().parents[1]
class ScopeTest(unittest.TestCase):
 def test_sandisk(self):subprocess.run([sys.executable,str(SKILL/'scripts/scope_regression_check.py'),'--baseline',str(SKILL/'assets/benchmarks/sandisk_scope_baseline_v61.csv'),'--candidate',str(SKILL/'assets/benchmarks/sandisk_scope_candidate_v63.csv')],check=True,capture_output=True,text=True)
if __name__=='__main__':unittest.main()
