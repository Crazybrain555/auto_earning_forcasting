import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


SKILL = Path(__file__).resolve().parents[1]
TRAINER_SKILL = SKILL / "SKILL.md"
LIVE_SKILL = SKILL / "assets" / "live_release" / "SKILL.md"
OUTPUT_CONTRACT = SKILL / "references" / "core-output-and-valuation.md"
INTEGRITY_CONTRACT = SKILL / "references" / "model-mechanical-integrity.md"
METHOD_SYSTEM = SKILL / "assets" / "method_system.json"


class ThreeStatementDecisionMemoContractTest(unittest.TestCase):
    def test_both_skill_profiles_route_to_the_machine_authority(self):
        # Wording belongs in the method references.  Profile entrypoints only
        # need to route to the same machine-readable contract; duplicating each
        # sentence here made punctuation and line wrapping into fake failures.
        for path in (TRAINER_SKILL, LIVE_SKILL):
            text = path.read_text(encoding="utf-8")
            with self.subTest(path=path.name):
                self.assertIn("assets/method_system.json", text)
                self.assertIn("references/research-sop.md", text)
                self.assertIn("references/model-mechanical-integrity.md", text)
                self.assertIn("references/core-output-and-valuation.md", text)

    def test_core_output_contract_requires_period_rows_and_statement_links(self):
        text = OUTPUT_CONTRACT.read_text(encoding="utf-8")
        for phrase in (
            "### Integrated three-statement minimum",
            "P&L link",
            "CFS link",
            "closing balance-sheet amount",
            "CFO + CFI + CFF + FX",
            "ending basic shares",
            "period weighted-average basic/diluted EPS shares",
            "valuation-date fully diluted shares",
            "financing and dilution",
            "human-required",
        ):
            self.assertIn(phrase, text)

    def test_narrow_review_exception_is_materiality_bounded(self):
        text = INTEGRITY_CONTRACT.read_text(encoding="utf-8")
        for phrase in (
            "### Narrow-scope materiality exception",
            "named materiality test",
            "affected statement links",
            "blocked full-company conclusions",
            "does not waive the full schedule",
        ):
            self.assertIn(phrase, text)

    def test_machine_authority_encodes_scope_rolls_and_checks(self):
        payload = json.loads(METHOD_SYSTEM.read_text(encoding="utf-8"))
        contract = payload["mandatory_decision_schedules"]["integrated_three_statement_minimum"]
        self.assertEqual(
            contract["trigger"],
            "full_company_or_three_year_or_longer_forecast_or_valuation",
        )
        self.assertEqual(contract["narrow_review_rule"], "materiality_bounded")
        self.assertEqual(
            set(contract["required_roll_forwards"]),
            {
                "ppe_and_depreciation",
                "operating_working_capital",
                "debt_and_cash",
                "financing_dilution_and_basic_diluted_shares",
            },
        )
        self.assertEqual(
            set(contract["required_checks"]),
            {
                "cfs_to_balance_sheet_cash",
                "assets_equal_liabilities_plus_equity",
                "revenue_to_operating_profit",
                "operating_profit_to_pretax_profit",
                "pretax_tax_nci_to_gaap_attributable_net_income",
                "forecast_period_coverage_across_integrated_snapshot_and_earnings_bridge",
            },
        )

    def test_live_builder_preserves_the_contract(self):
        with tempfile.TemporaryDirectory() as td:
            output = Path(td) / "technology-company-profit-forecasting"
            result = subprocess.run(
                [
                    sys.executable,
                    str(SKILL / "scripts" / "build_live_release.py"),
                    "--trainer-skill-root",
                    str(SKILL),
                    "--output-root",
                    str(output),
                ],
                capture_output=True,
                text=True,
            )
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            live_text = (output / "SKILL.md").read_text(encoding="utf-8")
            output_text = (output / "references" / "core-output-and-valuation.md").read_text(
                encoding="utf-8"
            )
            integrity_text = (output / "references" / "model-mechanical-integrity.md").read_text(
                encoding="utf-8"
            )
        self.assertIn("Minimum integrated three-statement schedule", live_text)
        self.assertIn("### Integrated three-statement minimum", output_text)
        self.assertIn("### Narrow-scope materiality exception", integrity_text)


if __name__ == "__main__":
    unittest.main()
