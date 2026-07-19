import json,subprocess,sys,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
class SchemaTest(unittest.TestCase):
    def test_case_template(self):
        r=subprocess.run([sys.executable,str(ROOT/'scripts/validate_case.py'),str(ROOT/'assets/templates/case_template.json')])
        self.assertEqual(r.returncode,0)
if __name__=='__main__':unittest.main()
