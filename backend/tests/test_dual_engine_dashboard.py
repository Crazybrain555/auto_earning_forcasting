from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

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

    def test_engine_status_does_not_advertise_a_missing_executable(self) -> None:
        with patch("shutil.which", side_effect=lambda name: None if name == "claude" else f"/bin/{name}"):
            status = {item["engine"]: item for item in jobs.engine_status()}
        self.assertFalse(status["claude"]["available"])
        self.assertTrue(status["codex"]["available"])
        self.assertIn("not installed", status["claude"]["note"])

    def test_engine_status_flags_a_missing_claude_login_on_linux_runners(self) -> None:
        with patch("shutil.which", side_effect=lambda name: f"/bin/{name}"), \
                patch.object(jobs.sys, "platform", "linux"), \
                patch.object(jobs.Path, "home", return_value=Path("/nonexistent-runner-home")):
            status = {item["engine"]: item for item in jobs.engine_status()}
        self.assertFalse(status["claude"]["available"])
        self.assertIn("not logged in", status["claude"]["note"])
        self.assertTrue(status["codex"]["available"])

    def test_engine_status_accepts_an_operator_token_file_as_login(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            home = Path(temp)
            (home / ".claude").mkdir()
            (home / ".claude" / "oauth-token").write_text("sk-test-token\n", encoding="utf-8")
            with patch("shutil.which", side_effect=lambda name: f"/bin/{name}"), \
                    patch.object(jobs.sys, "platform", "linux"), \
                    patch.object(jobs.Path, "home", return_value=home):
                status = {item["engine"]: item for item in jobs.engine_status()}
        self.assertTrue(status["claude"]["available"])


class LocalDualEngineFrontendTests(unittest.TestCase):
    def test_frontend_keeps_claude_and_codex_selectable(self) -> None:
        source = (ROOT / "webapp" / "app.js").read_text(encoding="utf-8")
        self.assertNotIn("ACTIVE_ENGINE", source)
        self.assertIn('claude: "Claude Code', source)
        self.assertIn('codex: "Codex CLI', source)
        self.assertIn("p.last = engine", source)
        self.assertIn("availableEngines.map", source)

    def test_frontend_describes_live_snapshots_and_case_selected_training(self) -> None:
        source = (ROOT / "webapp" / "app.js").read_text(encoding="utf-8")
        self.assertIn("当前证据持续进入直到发布冻结", source)
        self.assertIn("skillMap.stages.map", source)
        self.assertNotIn("const PIPE_SVG", source)
        self.assertIn("每组至少 1 个案例", source)
        self.assertNotIn("决策问题与时点边界", source)
        self.assertNotIn("as_of 锁定", source)
        self.assertNotIn("2+2 shape is fixed", source)
        self.assertNotIn("每组固定 2 只", source)


class CodexOperatingContractTests(unittest.TestCase):
    def test_live_prompt_keeps_project_operating_notes(self) -> None:
        config = json.loads((ROOT / "backend" / "config.json").read_text(encoding="utf-8"))
        prompt = config["prompts"]["live_forecast"]
        self.assertIn("AGENTS.md", prompt)
        self.assertNotIn("CLAUDE.md", prompt)

    def test_live_prompt_treats_as_of_as_snapshot_metadata_not_a_cutoff(self) -> None:
        config = json.loads((ROOT / "backend" / "config.json").read_text(encoding="utf-8"))
        prompt = config["prompts"]["live_forecast"]
        self.assertIn("current evidence through bundle freeze", prompt)
        self.assertIn("snapshot metadata", prompt)
        self.assertNotIn("with as_of={as_of}", prompt)
        self.assertNotIn("at least 6 SignalCards", prompt)

    def test_training_prompts_select_cases_by_failure_mode_not_a_fixed_quota(self) -> None:
        config = json.loads((ROOT / "backend" / "config.json").read_text(encoding="utf-8"))
        planner = config["prompts"]["plan_round"]
        runner = config["prompts"]["training_round"]
        self.assertIn("case-selected", planner)
        self.assertIn("at least one development", planner)
        self.assertIn("independent validation", planner)
        self.assertIn("optional cross-fold diagnostic", runner)
        self.assertIn("aggregate score", runner)
        self.assertIn("build_skill_system.py", runner)
        self.assertNotIn("four companies", planner)
        self.assertNotIn("two unused pairs", planner)
        self.assertNotIn("On failure run the swap fold", runner)

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
