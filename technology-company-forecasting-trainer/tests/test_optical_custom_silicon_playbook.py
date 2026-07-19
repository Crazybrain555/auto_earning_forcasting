import unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3];SKILL=ROOT/'skills/technology-company-forecasting-trainer'
class OpticalTest(unittest.TestCase):
    def test_rules(self):
        t=((SKILL/'references/lens-networking-optics-custom-silicon.md').read_text()+
           (SKILL/'references/module-program-stage-conversion.md').read_text()+
           (SKILL/'references/module-perimeter-and-accounting.md').read_text()+
           (SKILL/'SKILL.md').read_text()).lower()
        for x in ['pam','coherent','tia','silicon','nre','tape-out','qualification','production award','material revenue','distribution-only','inventory fair-value step-up','gaap operating profit','finished module']:
            self.assertIn(x,t)
if __name__=='__main__':unittest.main()
