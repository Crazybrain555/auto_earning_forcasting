import unittest
from pathlib import Path
REF=Path(__file__).resolve().parents[1]/'references'
class CloudModuleTest(unittest.TestCase):
    def test_cloud_rules(self):
        text=(REF/'module-platform-usage-adoption.md').read_text().lower()
        for needle in ['effective price','cost optimization','reported operating margin','normalized operating margin','rpo','human-required','standalone fcf','roic']:
            self.assertIn(needle,text)
    def test_cloud_lens_exists(self):
        text=(REF/'lens-cloud-infrastructure-platform.md').read_text().lower()
        self.assertIn('aws validation findings',text)
        self.assertIn('research-grade',text)
        self.assertIn('screen-grade',text)
if __name__=='__main__':unittest.main()
