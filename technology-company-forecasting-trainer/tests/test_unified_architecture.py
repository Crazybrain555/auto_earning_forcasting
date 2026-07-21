import importlib.util
import json
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


SKILL = Path(__file__).resolve().parents[1]
SYSTEM_ROOT = SKILL.parent
CAPABILITY_SKILLS = {
    "company-evidence-research",
    "company-operating-modeling",
    "company-financial-forecasting",
}
COORDINATOR_SKILLS = {
    "technology-company-forecasting-trainer",
    "technology-company-profit-forecasting",
}
GENERAL_CORE = {
    "analysis-kernel.md",
    "accounting-diagnosis.md",
    "equation-primitives.md",
    "industry-economics-and-cycle.md",
    "technology-commercialization-and-ip.md",
    "valuation-and-market-expectations.md",
    "multi-skill-system-architecture.md",
    "methodological-foundations.md",
}
LIVE_PRODUCTION_CORE = GENERAL_CORE - {
    "multi-skill-system-architecture.md",
    "methodological-foundations.md",
}


class UnifiedArchitectureTest(unittest.TestCase):
    def test_two_coordinators_and_three_capability_skills(self):
        # Split only at independently trainable handoffs.  Industry lenses and
        # every method reference must not grow into separate skills.
        skills = {
            path.parent.name
            for path in SYSTEM_ROOT.glob("*/SKILL.md")
            if not path.parent.name.startswith(".")
        }
        self.assertEqual(skills, COORDINATOR_SKILLS | CAPABILITY_SKILLS)

    def test_capability_frontmatter_and_profiles_match_manifest(self):
        manifest = json.loads(
            (SKILL / "assets/skill_system/manifest.json").read_text(encoding="utf-8")
        )
        capabilities = manifest["capabilities"]
        self.assertEqual(set(capabilities), CAPABILITY_SKILLS)
        for name, contract in capabilities.items():
            with self.subTest(skill=name):
                source = SKILL / "assets/skill_system/skills" / name
                generated = SYSTEM_ROOT / name
                self.assertTrue((source / "SKILL.md").is_file())
                self.assertTrue((generated / "SKILL.md").is_file())
                frontmatter = (source / "SKILL.md").read_text(encoding="utf-8").split("---", 2)[1]
                self.assertRegex(frontmatter, rf"(?m)^name: {re.escape(name)}$")
                profile = json.loads((source / "assets/capability.json").read_text(encoding="utf-8"))
                self.assertEqual(profile["capability_id"], contract["capability_id"])
                self.assertEqual(profile["input_bundle_kinds"], contract["input_bundle_kinds"])
                self.assertEqual(profile["output_bundle_kind"], contract["output_bundle_kind"])
                self.assertEqual(profile["schema_version"], "forecast-capability-profile/v2")
                self.assertNotIn("allowed_modes", profile)
                self.assertNotIn("forbidden_inputs_by_mode", profile)
                self.assertEqual(
                    set(profile["forbidden_inputs"]),
                    {
                        "unaccepted_orchestrator_bundle",
                        "unrestricted_source_access",
                        "raw_actuals_channel",
                    },
                )

    def test_stage_ownership_is_total_unique_and_not_a_second_order(self):
        manifest = json.loads(
            (SKILL / "assets/skill_system/manifest.json").read_text(encoding="utf-8")
        )
        method = json.loads((SKILL / "assets/method_system.json").read_text(encoding="utf-8"))
        stage_ids = {stage["id"] for stage in method["stages"]}
        owners = manifest["stage_owners"]
        self.assertEqual(set(owners), stage_ids)
        self.assertTrue(all(isinstance(owner, str) and owner for owner in owners.values()))
        self.assertEqual(
            set(owners.values()),
            COORDINATOR_SKILLS - {"technology-company-forecasting-trainer"} | CAPABILITY_SKILLS,
        )
        self.assertNotIn("stage_order", manifest)
        self.assertNotIn("canonical_flow", manifest)

    def test_shared_contracts_are_not_an_invokable_skill(self):
        contracts = SYSTEM_ROOT / "forecasting-system-contracts"
        self.assertTrue((contracts / "protocol_manifest.json").is_file())
        self.assertTrue((contracts / "schemas/capability_handoff.schema.json").is_file())
        self.assertFalse((contracts / "SKILL.md").exists())

    def test_general_causal_value_core_is_present(self):
        for name in GENERAL_CORE:
            with self.subTest(reference=name):
                self.assertTrue((SKILL / "references" / name).is_file(), name)
        self.assertTrue((SKILL / "assets" / "method_system.json").is_file(), "assets/method_system.json")
        self.assertTrue((SKILL / "references" / "research-sop.md").is_file())
        self.assertTrue((SKILL / "assets" / "profile.json").is_file())

        # Equation primitives remain composable; sector labels are not the
        # organizing spine of the method.
        for name in (
            "driver-tree-modeling.md",
            "mechanism-router.md",
            "module-unit-volume-price-cost.md",
            "module-capacity-utilization-yield.md",
            "module-orders-backlog-recognition.md",
            "module-platform-usage-adoption.md",
            "module-recurring-contract-revenue.md",
            "module-perimeter-and-accounting.md",
        ):
            self.assertTrue((SKILL / "references" / name).is_file(), name)

    def test_live_required_manifest_routes_to_general_core_not_lenses(self):
        module_path = SKILL / "scripts" / "package_self_test.py"
        spec = importlib.util.spec_from_file_location("forecast_package_self_test", module_path)
        self.assertIsNotNone(spec and spec.loader)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        live_required = set(module.LIVE_REQUIRED)
        for name in LIVE_PRODUCTION_CORE:
            self.assertIn(f"references/{name}", live_required)
        for trainer_only in GENERAL_CORE - LIVE_PRODUCTION_CORE:
            self.assertNotIn(f"references/{trainer_only}", live_required)
        self.assertIn("assets/method_system.json", live_required)
        self.assertFalse(
            any(path.startswith("references/lens-") for path in live_required),
            "industry lenses are optional calibration packs, not live-kernel requirements",
        )

    def test_live_build_succeeds_when_sector_calibration_files_are_absent(self):
        # This is the structural proof of demotion: a general live skill can be
        # built without any lens file.  Historical/optional lens files may stay
        # in the canonical repository for backward-compatible calibration.
        with tempfile.TemporaryDirectory() as td:
            temp = Path(td)
            scratch = temp / "trainer"
            out = temp / "live"
            shutil.copytree(SKILL, scratch, ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
            for path in (scratch / "references").glob("lens-*.md"):
                path.unlink()
            result = subprocess.run(
                [
                    sys.executable,
                    str(scratch / "scripts" / "build_live_release.py"),
                    "--trainer-skill-root",
                    str(scratch),
                    "--output-root",
                    str(out),
                ],
                capture_output=True,
                text=True,
            )
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_no_sector_playbook_directory(self):
        self.assertFalse((SKILL / "references/sector-playbooks").exists())

    def test_one_canonical_stage_registry_is_used_by_manifest(self):
        method = json.loads((SKILL / "assets/method_system.json").read_text(encoding="utf-8"))
        manifest = json.loads(
            (SKILL / "assets/templates/run_manifest_template.json").read_text(encoding="utf-8")
        )
        stage_ids = [stage["id"] for stage in method["stages"]]
        self.assertEqual(list(manifest["phase_status"]), stage_ids)

    def test_production_method_and_training_improvement_overlay_have_one_way_ownership(self):
        method = json.loads((SKILL / "assets/method_system.json").read_text(encoding="utf-8"))
        overlay = json.loads((SKILL / "assets/training_method_overlay.json").read_text(encoding="utf-8"))
        self.assertNotIn("improvement_objective", method)
        self.assertEqual(method["stages"][-1]["id"], "publish_monitor_version")
        self.assertNotIn("predictive_discipline", method["assurance_philosophy"]["orthogonal_angles"])
        self.assertEqual(overlay["applies_to_profile"], "trainer")
        self.assertTrue(overlay["improvement_objective"]["not_a_scalar_optimization"])
        self.assertIn("predictive_discipline", overlay["assurance_additions"]["orthogonal_angles"])


if __name__ == "__main__":
    unittest.main()
