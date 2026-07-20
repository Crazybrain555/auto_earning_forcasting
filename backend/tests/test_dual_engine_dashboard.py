from __future__ import annotations

import json
import unittest
from pathlib import Path

from pydantic import ValidationError

from backend.app import jobs
from backend.app.main import JobRequest, engines as api_engines


ROOT = Path(__file__).resolve().parents[2]


class LocalDualEngineBackendTests(unittest.TestCase):
    def test_job_request_keeps_local_claude_default(self) -> None:
        request = JobRequest(type="suggest_watch")
        self.assertEqual(request.engine, "claude")

    def test_job_request_accepts_both_local_engines_and_rejects_unknown(self) -> None:
        self.assertEqual(JobRequest(type="suggest_watch", engine="claude").engine, "claude")
        self.assertEqual(JobRequest(type="suggest_watch", engine="codex").engine, "codex")
        with self.assertRaises(ValidationError):
            JobRequest(type="suggest_watch", engine="shell")

    def test_engine_api_exposes_both_available_local_engines(self) -> None:
        self.assertEqual(
            [item["engine"] for item in api_engines()],
            ["claude", "codex"],
        )
        self.assertTrue(all(item["available"] for item in api_engines()))
        self.assertEqual(api_engines(), jobs.engine_status())


class LocalDualEngineFrontendTests(unittest.TestCase):
    def test_frontend_keeps_claude_and_codex_selectable(self) -> None:
        source = (ROOT / "webapp" / "app.js").read_text(encoding="utf-8")
        self.assertNotIn("ACTIVE_ENGINE", source)
        self.assertIn('claude: "Claude Code', source)
        self.assertIn('codex: "Codex CLI', source)
        self.assertIn("p.last = engine", source)
        self.assertIn("availableEngines.map", source)


class CodexOperatingContractTests(unittest.TestCase):
    def test_live_prompt_keeps_project_operating_notes(self) -> None:
        config = json.loads((ROOT / "backend" / "config.json").read_text(encoding="utf-8"))
        prompt = config["prompts"]["live_forecast"]
        self.assertIn("AGENTS.md", prompt)
        self.assertNotIn("CLAUDE.md", prompt)

    def test_project_agents_skills_link_to_current_method_tree(self) -> None:
        skills = ROOT / ".agents" / "skills"
        for name in (
            "technology-company-profit-forecasting",
            "technology-company-forecasting-trainer",
        ):
            link = skills / name
            target = ROOT / "forecasting-skills" / name
            self.assertTrue(link.is_symlink(), f"{link} must be a symlink")
            self.assertEqual(link.resolve(), target.resolve())


if __name__ == "__main__":
    unittest.main()
