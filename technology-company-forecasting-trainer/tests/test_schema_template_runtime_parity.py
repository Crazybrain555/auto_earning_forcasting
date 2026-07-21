import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


SKILL = Path(__file__).resolve().parents[1]
TEMPLATES = SKILL / "assets" / "templates"
SCHEMAS = SKILL / "assets" / "schemas"


class SchemaTemplateRuntimeParityTest(unittest.TestCase):
    PAIRS = {
        "run_manifest": ("run_manifest_template.json", "run_manifest.schema.json"),
        "forecast_snapshot": ("forecast_snapshot_template.json", "forecast_snapshot.schema.json"),
        "model_graph": ("model_graph_template.json", "model_graph.schema.json"),
    }

    def _load_pairs(self):
        loaded = {}
        for artifact, (template_name, schema_name) in self.PAIRS.items():
            template_path = TEMPLATES / template_name
            schema_path = SCHEMAS / schema_name
            self.assertTrue(template_path.is_file(), f"missing active template {template_name}")
            self.assertTrue(schema_path.is_file(), f"missing active schema {schema_name}")
            loaded[artifact] = (
                json.loads(template_path.read_text(encoding="utf-8")),
                json.loads(schema_path.read_text(encoding="utf-8")),
            )
        return loaded

    def test_schema_properties_and_templates_have_identical_top_level_contracts(self):
        for artifact, (template, schema) in self._load_pairs().items():
            with self.subTest(artifact=artifact):
                properties = set((schema.get("properties") or {}).keys())
                required = set(schema.get("required") or [])
                self.assertEqual(set(template.keys()), properties)
                self.assertTrue(required <= set(template.keys()), (artifact, required - set(template.keys())))

    def test_snapshot_and_graph_publish_the_new_auditable_blocks(self):
        snapshot = json.loads((TEMPLATES / "forecast_snapshot_template.json").read_text(encoding="utf-8"))
        self.assertTrue(
            {
                "investment_case",
                "integrated_model",
                "value_creation",
                "valuation",
                "market_implied_expectations",
            }
            <= set(snapshot)
        )
        graph = json.loads((TEMPLATES / "model_graph_template.json").read_text(encoding="utf-8"))
        self.assertTrue({"schema_version", "nodes", "equations", "main_line"} <= set(graph))

        snapshot_schema_text = (SCHEMAS / "forecast_snapshot.schema.json").read_text(
            encoding="utf-8"
        )
        for field in (
            "operating_costs_and_expenses",
            "nonoperating_income_expense_net",
            "pretax_profit",
            "tax_expense",
            "net_income_attributable_to_noncontrolling_interests",
            "net_income_attributable",
            "noncontrolling_interest_net_income_point",
        ):
            self.assertIn(field, snapshot_schema_text)

    def test_scaffold_runtime_uses_the_same_top_level_contract(self):
        pairs = self._load_pairs()
        with tempfile.TemporaryDirectory() as td:
            workspace = Path(td) / "run"
            result = subprocess.run(
                [
                    sys.executable,
                    str(SKILL / "scripts" / "scaffold_delivery.py"),
                    "--workspace",
                    str(workspace),
                    "--entity",
                    "TEST",
                    "--security",
                    "TEST",
                    "--as-of",
                    "2026-07-18",
                    "--mode",
                    "historical_train",
                ],
                capture_output=True,
                text=True,
            )
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            for artifact, (template, _schema) in pairs.items():
                with self.subTest(artifact=artifact):
                    runtime = json.loads((workspace / f"{artifact}.json").read_text(encoding="utf-8"))
                    self.assertEqual(set(runtime), set(template))

    def test_shared_runtime_profile_owns_contract_validator_packaging(self):
        profile = json.loads((SKILL / "assets" / "profile.json").read_text(encoding="utf-8"))
        runtime_scripts = set(profile["runtime_scripts"])
        self.assertTrue(
            {
                "validate_model_graph.py",
                "validate_investment_case.py",
                "equation_contract.py",
                "provenance_contract.py",
            }
            <= runtime_scripts
        )
        for name in runtime_scripts:
            self.assertTrue((SKILL / "scripts" / name).is_file(), name)


if __name__ == "__main__":
    unittest.main()
