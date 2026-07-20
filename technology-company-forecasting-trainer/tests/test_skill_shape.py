import json,re,unittest
from pathlib import Path
SKILL=Path(__file__).resolve().parents[1]
REPO=SKILL.parent
NAME='technology-company-forecasting-trainer'
LIVE_NAME='technology-company-profit-forecasting'
class SkillShapeTest(unittest.TestCase):
    def test_manifests(self):
        if not (REPO/'.claude-plugin/plugin.json').exists():
            self.skipTest('package wrappers absent in installed git-repo layout')
        self.assertEqual(json.loads((REPO/'.codex-plugin/plugin.json').read_text())['name'],NAME)
        self.assertEqual(json.loads((REPO/'.claude-plugin/plugin.json').read_text())['name'],NAME)
    def test_frontmatter(self):
        t=(SKILL/'SKILL.md').read_text();self.assertTrue(t.startswith('---\n'));f=t.split('---',2)[1]
        self.assertRegex(f,r'(?m)^name: technology-company-forecasting-trainer$')
        m=re.search(r'(?m)^description: (.+)$',f);self.assertIsNotNone(m)
        self.assertLessEqual(len(m.group(1)),1024)
        self.assertIn(LIVE_NAME,m.group(1))
    def test_directory_name_matches_frontmatter(self):
        self.assertEqual(SKILL.name,NAME)
    def test_live_template_frontmatter(self):
        t=(SKILL/'assets/live_release/SKILL.md').read_text();f=t.split('---',2)[1]
        self.assertRegex(f,r'(?m)^name: technology-company-profit-forecasting$')
        m=re.search(r'(?m)^description: (.+)$',f);self.assertIsNotNone(m)
        self.assertLessEqual(len(m.group(1)),1024)
        self.assertIn(NAME,m.group(1))
if __name__=='__main__':unittest.main()
