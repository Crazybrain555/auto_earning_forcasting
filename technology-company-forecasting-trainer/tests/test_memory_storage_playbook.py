import unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
class MemoryStoragePlaybookTest(unittest.TestCase):
    def test_required_bridges(self):
        text=(ROOT/'references/lens-memory-storage.md').read_text(encoding='utf-8').lower()
        for phrase in ['rpo','price-protected','joint-venture','double counting','contract liabilities','buybacks','normalized value']:
            self.assertIn(phrase,text)
        self.assertTrue((ROOT/'assets/templates/memory_storage_assumption_register_template.csv').exists())
if __name__=='__main__':unittest.main()
