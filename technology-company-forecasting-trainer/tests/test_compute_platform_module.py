import unittest
from pathlib import Path
REF=Path(__file__).resolve().parents[1]/'references'
class ComputePlatformModuleTest(unittest.TestCase):
    def test_channel_supply_regime_rules(self):
        t=(REF/'lens-compute-platforms.md').read_text().lower()
        for x in ['sell-in','sell-through','channel inventory','purchase obligations','distribution-only','regime break','mellanox','arm']:
            self.assertIn(x,t)
if __name__=='__main__':unittest.main()
