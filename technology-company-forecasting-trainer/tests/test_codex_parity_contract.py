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
            SKILL/'assets/examples/sandisk_v73/Sandisk_SNDK_v7.3_五年财务模型.xlsx',
            SKILL/'assets/examples/sandisk_v73/Sandisk_SNDK_v7.3_模型报告.md',
        ]
        for path in required:
            self.assertTrue(path.exists(), str(path))
            self.assertGreater(path.stat().st_size, 0, str(path))

    def test_mandatory_language(self):
        text=(SKILL/'SKILL.md').read_text(encoding='utf-8').lower()
        for phrase in ['mandatory full-model execution contract','validate_delivery.py --strict','validate_research_completeness.py','formula-driven','red team','run_manifest.json','company quality','patents'] :
            self.assertIn(phrase.lower(),text)
        prompt=(SKILL/'agents/openai.yaml').read_text(encoding='utf-8').lower()
        for phrase in ['initialize the run workspace','formula-driven xlsx','strict delivery validator','immutable snapshot']:
            self.assertIn(phrase,prompt)

    def test_memory_channel_and_effective_cost(self):
        text=(SKILL/'references/lens-memory-storage.md').read_text(encoding='utf-8').lower()
        for phrase in ['sell-in','sell-through','effective cost per bit','technical cost per bit']:
            self.assertIn(phrase,text)

if __name__=='__main__':
    unittest.main()
