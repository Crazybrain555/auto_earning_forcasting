import copy
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from contract_fixtures import valid_recurring_snapshot


SKILL = Path(__file__).resolve().parents[1]
VALIDATOR = SKILL / "scripts" / "validate_investment_case.py"


class RecurringPlatformContractTest(unittest.TestCase):
    def _validate(self, snapshot: dict) -> dict:
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "forecast_snapshot.json"
            path.write_text(json.dumps(snapshot), encoding="utf-8")
            result = subprocess.run(
                [sys.executable, str(VALIDATOR), "--snapshot", str(path), "--strict"],
                capture_output=True,
                text=True,
            )
        payload = json.loads(result.stdout)
        self.assertEqual(bool(payload.get("valid")), result.returncode == 0, payload)
        return payload

    @staticmethod
    def _codes(payload: dict) -> set[str]:
        return {error.get("code") for error in payload.get("errors", [])}

    def test_complete_recurring_model_passes(self):
        self.assertTrue(self._validate(valid_recurring_snapshot())["valid"])

    def test_recurring_stock_flow_and_unit_cost_identities_are_hard_gates(self):
        mutations = {
            "retained_arr": ("cohort_periods", "retained_arr", 91.0, "recurring_arr_roll"),
            "ending_arr": ("cohort_periods", "ending_arr", 111.0, "recurring_arr_roll"),
            "nrr": ("cohort_periods", "calculated_nrr", 1.20, "recurring_nrr_identity"),
            "recognition": ("cohort_periods", "subscription_revenue", 120.0, "recurring_revenue_identity"),
            "inference": ("cost_periods", "inference_cost", 21.0, "usage_cost_identity"),
            "hosting": ("cost_periods", "hosting_cost", 11.0, "hosting_cost_identity"),
            "support": ("cost_periods", "support_cost", 11.0, "support_cost_identity"),
            "subscription_cogs": ("cost_periods", "subscription_cogs", 46.0, "subscription_cogs_identity"),
            "service_cogs": ("cost_periods", "service_cogs", 31.0, "service_cost_identity"),
        }
        for name, (table, field, value, expected) in mutations.items():
            with self.subTest(name=name):
                snapshot = valid_recurring_snapshot()
                snapshot["recurring_model"][table][0][field] = value
                self.assertIn(expected, self._codes(self._validate(snapshot)))

    def test_nrr_cannot_be_added_again_as_revenue(self):
        snapshot = valid_recurring_snapshot()
        snapshot["recurring_model"]["cohort_periods"][0]["nrr_revenue_addition"] = 5.0
        self.assertIn("recurring_double_count", self._codes(self._validate(snapshot)))

    def test_recurring_statement_roll_forwards_are_hard_gates(self):
        mutations = {
            "deferred": ("deferred_revenue", "closing", 31.0, "deferred_revenue_roll"),
            "receivables": ("accounts_receivable", "closing", 21.0, "receivables_roll"),
            "payables": ("accounts_payable", "closing", 16.0, "payables_roll"),
            "development": ("capitalized_development", "closing", 10.0, "capitalized_development_roll"),
            "shares": ("diluted_shares", "closing", 102.0, "diluted_shares_roll"),
        }
        for name, (roll, field, value, expected) in mutations.items():
            with self.subTest(name=name):
                snapshot = valid_recurring_snapshot()
                snapshot["integrated_model"]["periods"][0]["roll_forwards"][roll][field] = value
                self.assertIn(expected, self._codes(self._validate(snapshot)))

    def test_recurring_model_is_mandatory_when_primitive_is_selected(self):
        snapshot = valid_recurring_snapshot()
        snapshot.pop("recurring_model")
        self.assertIn("missing_recurring_model", self._codes(self._validate(snapshot)))


if __name__ == "__main__":
    unittest.main()
