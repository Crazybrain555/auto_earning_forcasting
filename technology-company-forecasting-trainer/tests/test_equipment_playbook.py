import unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3];SKILL=ROOT/'skills/technology-company-forecasting-trainer'
class EquipmentPlaybookTest(unittest.TestCase):
    def test_wfe_and_process_control_rules(self):
        t=(SKILL/'references/lens-equipment-process-control.md').read_text().lower()
        m=(SKILL/'references/module-orders-backlog-recognition.md').read_text().lower()
        for needle in ['contract service','spares','upgrades','reliant','dram','nand','acceptance']:
            self.assertIn(needle,t+m)
        for needle in ['technology-development','capacity spend','wafer inspection','patterning','installed base']:
            self.assertIn(needle,t)
    def test_human_required(self):
        t=(SKILL/'SKILL.md').read_text().lower();self.assertIn('human-required',t);self.assertIn('non-target',t)
if __name__=='__main__':unittest.main()
