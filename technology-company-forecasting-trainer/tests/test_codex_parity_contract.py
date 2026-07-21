import json
import unittest
from pathlib import Path

SKILL=Path(__file__).resolve().parents[1]

class CodexParityContractTest(unittest.TestCase):
    def test_required_files(self):
        required=[
            SKILL/'references/codex-parity-execution.md',
            SKILL/'references/full-company-delivery-contract.md',
            SKILL/'references/gold-standard-example.md',
            SKILL/'references/research-completeness-and-company-quality.md',
            SKILL/'scripts/scaffold_delivery.py',
            SKILL/'scripts/validate_research_completeness.py',
            SKILL/'scripts/validate_delivery.py',
            SKILL/'assets/templates/run_manifest_template.json',
            SKILL/'assets/templates/delivery_quality_rubric.json',
            SKILL/'assets/templates/red_team_template.md',
        ]
        for path in required:
            self.assertTrue(path.exists(), str(path))
            self.assertGreater(path.stat().st_size, 0, str(path))

    def test_mandatory_language(self):
        # Parity is a shared executable contract, not a phrase-presence score.
        text=(SKILL/'SKILL.md').read_text(encoding='utf-8')
        self.assertIn('assets/method_system.json', text)
        self.assertIn('references/research-sop.md', text)
        method=json.loads((SKILL/'assets/method_system.json').read_text(encoding='utf-8'))
        overlay=json.loads((SKILL/'assets/training_method_overlay.json').read_text(encoding='utf-8'))
        self.assertNotIn('improvement_objective', method)
        self.assertTrue(overlay['improvement_objective']['not_a_scalar_optimization'])
        self.assertEqual(
            method['construction_philosophy']['canonical_sop'],
            'references/research-sop.md',
        )
        self.assertEqual(
            method['assurance_philosophy']['tests_are'],
            'orthogonal_views_not_a_completeness_score',
        )

if __name__=='__main__':
    unittest.main()
