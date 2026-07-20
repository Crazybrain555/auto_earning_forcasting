import unittest
from pathlib import Path
SKILL=Path(__file__).resolve().parents[1]
class UnifiedArchitectureTest(unittest.TestCase):
    def test_single_skill_folder(self):
        # Package layout ships only the trainer; the installed git repo has the
        # trainer next to the built production skill. Nothing else may appear.
        allowed={'technology-company-forecasting-trainer','technology-company-profit-forecasting'}
        skills={p.name for p in SKILL.parent.iterdir() if p.is_dir() and not p.name.startswith('.')}
        self.assertIn('technology-company-forecasting-trainer',skills)
        self.assertTrue(skills<=allowed,skills)
    def test_common_core_and_modules(self):
        required=[
            'core-source-and-evidence.md','core-forecast-workflow.md','core-output-and-valuation.md',
            'historical-training-loop.md','mechanism-router.md','module-unit-volume-price-cost.md',
            'module-capacity-utilization-yield.md','module-orders-backlog-recognition.md',
            'module-platform-usage-adoption.md','module-subscriber-content-economics.md',
            'module-program-stage-conversion.md','module-contracts-jv-capital.md',
            'module-perimeter-and-accounting.md','validated-coverage.md'
        ]
        for f in required:self.assertTrue((SKILL/'references'/f).exists(),f)
    def test_platform_and_content_status(self):
        cloud=(SKILL/'references/module-platform-usage-adoption.md').read_text().lower()
        content=(SKILL/'references/module-subscriber-content-economics.md').read_text().lower()
        self.assertIn('retrospectively validated',cloud);self.assertIn('research-grade',cloud);self.assertIn('human-required',cloud)
        self.assertIn('retrospectively validated',content);self.assertIn('netflix',content);self.assertIn('human-required',content)
        self.assertTrue((SKILL/'references/lens-cloud-infrastructure-platform.md').exists())
        self.assertTrue((SKILL/'references/lens-subscription-content-platform.md').exists())
    def test_no_sector_playbook_directory(self):
        self.assertFalse((SKILL/'references/sector-playbooks').exists())
if __name__=='__main__':unittest.main()
