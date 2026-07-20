import unittest
from pathlib import Path
REF=Path(__file__).resolve().parents[1]/'references'
class SubscriptionContentModuleTest(unittest.TestCase):
    def test_required_bridges(self):
        t=(REF/'module-subscriber-content-economics.md').read_text().lower()
        for x in ['grossadds','voluntarychurn','cash content investment','content amortization','exogenous pull-forward','human-required']:
            self.assertIn(x,t)
        self.assertTrue((REF/'lens-subscription-content-platform.md').exists())
if __name__=='__main__':unittest.main()
