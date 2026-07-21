import json,subprocess,sys,unittest
import pytest
from pathlib import Path
pytestmark = pytest.mark.diagnostic_benchmark
SKILL=Path(__file__).resolve().parents[1]
class AMDIntelBacktestTest(unittest.TestCase):
    def test_point_in_time_source_boundary(self):
        pit=[sys.executable,str(SKILL/"scripts/validate_amd_intel_point_in_time.py"),
             "--cases",str(SKILL/"assets/benchmarks/amd_intel_cases_v75.json"),
             "--signals",str(SKILL/"assets/benchmarks/amd_intel_signals_v75.csv"),
             "--query-log",str(SKILL/"assets/benchmarks/amd_intel_query_log_v75.csv")]
        r=subprocess.run(pit,capture_output=True,text=True)
        self.assertEqual(r.returncode,0,r.stdout+r.stderr)
    def test_cutoff_known_financial_vintage(self):
        cases=json.loads((SKILL/"assets/benchmarks/amd_intel_cases_v75.json").read_text())
        c=next(x for x in cases if x["case_id"]=="AMD@FY2017")
        self.assertAlmostEqual(c["base_revenue"],5.329)
        self.assertIn("later recast",c["point_in_time_note"].lower())
if __name__=="__main__":unittest.main()
