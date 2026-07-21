import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from contract_fixtures import valid_investment_snapshot


SKILL = Path(__file__).resolve().parents[1]
VALIDATOR = SKILL / "scripts" / "validate_investment_case.py"


class InvestmentValueContractTest(unittest.TestCase):
    def _validate(self, snapshot: dict) -> dict:
        self.assertTrue(VALIDATOR.exists(), "missing investment/value validator: scripts/validate_investment_case.py")
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "forecast_snapshot.json"
            path.write_text(json.dumps(snapshot), encoding="utf-8")
            result = subprocess.run(
                [sys.executable, str(VALIDATOR), "--snapshot", str(path), "--strict"],
                capture_output=True,
                text=True,
            )
        try:
            payload = json.loads(result.stdout)
        except json.JSONDecodeError as exc:
            self.fail(f"validator stdout must be one JSON object: {exc}\n{result.stdout}\n{result.stderr}")
        self.assertEqual(bool(payload.get("valid")), result.returncode == 0, payload)
        self.assertIsInstance(payload.get("errors"), list, payload)
        return payload

    @staticmethod
    def _codes(payload: dict) -> set[str]:
        return {error.get("code") for error in payload["errors"] if isinstance(error, dict)}

    def test_closed_integrated_model_and_value_case_pass(self):
        payload = self._validate(valid_investment_snapshot())
        self.assertTrue(payload["valid"], payload)

    @staticmethod
    def _profit_chain_snapshot() -> dict:
        """Add the wished-for canonical reported-profit chain to the fixture.

        The cash-flow statement starts from consolidated net income.  The
        published point forecast is GAAP net income attributable after the
        explicitly quantified non-controlling-interest claim.
        """

        snapshot = valid_investment_snapshot()
        chains = {
            "FY2027": {
                "operating_costs_and_expenses": 80.0,
                "nonoperating_income_expense_net": -1.0,
                "pretax_profit": 19.0,
                "tax_expense": 5.0,
                "net_income": 14.0,
                "net_income_attributable_to_noncontrolling_interests": 2.0,
                "net_income_attributable": 12.0,
            },
            "FY2028": {
                "operating_costs_and_expenses": 88.0,
                "nonoperating_income_expense_net": -1.0,
                "pretax_profit": 23.0,
                "tax_expense": 6.0,
                "net_income": 17.0,
                "net_income_attributable_to_noncontrolling_interests": 3.0,
                "net_income_attributable": 14.0,
            },
        }
        outputs = {}
        for period_row in snapshot["integrated_model"]["periods"]:
            period = period_row["period"]
            period_row["income_statement"].update(chains[period])
            period_row["cash_flow_statement"]["net_income"] = chains[period]["net_income"]
            income = period_row["income_statement"]
            outputs[period] = {
                "period": period,
                "revenue_point": income["revenue"],
                "operating_profit_point": income["operating_profit"],
                "pretax_profit_point": income["pretax_profit"],
                "tax_expense_point": income["tax_expense"],
                "noncontrolling_interest_net_income_point": income[
                    "net_income_attributable_to_noncontrolling_interests"
                ],
                "net_income_point": income["net_income_attributable"],
                "profit_point": income["net_income_attributable"],
                "point_evaluable": True,
            }
        snapshot["outputs"] = {"year_1": outputs["FY2027"], "year_2": outputs["FY2028"]}
        return snapshot

    def test_canonical_reported_profit_chain_reconciles(self):
        payload = self._validate(self._profit_chain_snapshot())
        self.assertTrue(payload["valid"], payload)

    def test_absurd_pretax_tax_and_attributable_net_income_are_rejected(self):
        mutations = {
            "pretax": (
                lambda s: (
                    s["integrated_model"]["periods"][0]["income_statement"].update(
                        {"pretax_profit": 900.0}
                    ),
                    s["outputs"]["year_1"].update({"pretax_profit_point": 900.0}),
                ),
                "pretax_profit_identity",
            ),
            "tax": (
                lambda s: (
                    s["integrated_model"]["periods"][0]["income_statement"].update(
                        {"tax_expense": 7.0}
                    ),
                    s["outputs"]["year_1"].update({"tax_expense_point": 7.0}),
                ),
                "net_income_identity",
            ),
            "attributable_net_income": (
                lambda s: (
                    s["integrated_model"]["periods"][0]["income_statement"].update(
                        {"net_income_attributable": 99.0}
                    ),
                    s["outputs"]["year_1"].update(
                        {"net_income_point": 99.0, "profit_point": 99.0}
                    ),
                ),
                "attributable_net_income_identity",
            ),
        }
        for name, (mutate, expected_code) in mutations.items():
            with self.subTest(name=name):
                snapshot = self._profit_chain_snapshot()
                mutate(snapshot)
                payload = self._validate(snapshot)
                self.assertIn(expected_code, self._codes(payload), payload)

    def test_noncontrolling_interest_must_be_explicit_even_when_zero(self):
        snapshot = self._profit_chain_snapshot()
        snapshot["integrated_model"]["periods"][0]["income_statement"].pop(
            "net_income_attributable_to_noncontrolling_interests"
        )
        snapshot["outputs"]["year_1"].pop("noncontrolling_interest_net_income_point")
        payload = self._validate(snapshot)
        self.assertIn("attributable_net_income_identity", self._codes(payload), payload)

    def test_every_forecast_output_period_must_have_integrated_statements(self):
        snapshot = self._profit_chain_snapshot()
        snapshot["outputs"]["year_3_distribution"] = {
            **snapshot["outputs"]["year_2"],
            "period": "FY2029",
            "point_evaluable": False,
        }
        payload = self._validate(snapshot)
        self.assertIn("forecast_period_coverage", self._codes(payload), payload)

    def test_snapshot_points_must_reconcile_to_same_period_statements(self):
        snapshot = self._profit_chain_snapshot()
        snapshot["outputs"]["year_2"]["pretax_profit_point"] = 999.0
        payload = self._validate(snapshot)
        self.assertIn("snapshot_statement_link", self._codes(payload), payload)

    def test_three_statements_and_roll_forwards_are_arithmetic_contracts(self):
        mutations = {
            "balance_sheet": (
                lambda s: s["integrated_model"]["periods"][0]["balance_sheet"].update({"assets": 151.0}),
                "balance_sheet",
            ),
            "cash": (
                lambda s: s["integrated_model"]["periods"][0]["roll_forwards"]["cash"].update({"closing": 16.0}),
                "cash_roll_forward",
            ),
            "ppe": (
                lambda s: s["integrated_model"]["periods"][0]["roll_forwards"]["ppe"].update({"closing": 61.0}),
                "ppe_roll_forward",
            ),
            "debt": (
                lambda s: s["integrated_model"]["periods"][0]["roll_forwards"]["debt"].update({"closing": 31.0}),
                "debt_roll_forward",
            ),
            "working_capital": (
                lambda s: s["integrated_model"]["periods"][0]["roll_forwards"]["working_capital"].update({"closing": 22.0}),
                "working_capital_roll_forward",
            ),
        }
        for name, (mutate, expected_code) in mutations.items():
            with self.subTest(name=name):
                snapshot = valid_investment_snapshot()
                mutate(snapshot)
                payload = self._validate(snapshot)
                self.assertIn(expected_code, self._codes(payload), payload)

    def test_normalized_nopat_average_roic_reinvestment_and_growth_must_reconcile(self):
        mutations = {
            "normalized_nopat": ("normalized_nopat", 99.0, "normalized_nopat_identity"),
            "average_capital": ("average_invested_capital", 99.0, "average_invested_capital_identity"),
            "average_roic": ("average_roic", 0.30, "average_roic_identity"),
            "ending_capital": ("ending_invested_capital", 99.0, "invested_capital_roll_forward"),
            "reinvestment_rate": ("reinvestment_rate", 0.20, "reinvestment_rate_identity"),
            "incremental_nopat": ("incremental_nopat", 9.0, "incremental_nopat_identity"),
            "incremental_roic": ("incremental_roic", 0.30, "incremental_roic_identity"),
            "fundamental_growth": ("fundamental_growth", 0.12, "fundamental_growth_identity"),
        }
        for name, (field, value, expected_code) in mutations.items():
            with self.subTest(name=name):
                snapshot = valid_investment_snapshot()
                snapshot["value_creation"]["periods"][0][field] = value
                payload = self._validate(snapshot)
                self.assertIn(expected_code, self._codes(payload), payload)

    def test_invested_capital_continuity_and_causal_fade_schedule_are_required(self):
        mutations = {
            "capital_continuity": (
                lambda s: s["value_creation"]["periods"][1].update({"beginning_invested_capital": 82.0}),
                "invested_capital_continuity",
            ),
            "fade_event": (
                lambda s: s["value_creation"]["fade"]["schedule"][0].update({"erosion_or_renewal_event": ""}),
                "fade_schedule",
            ),
            "fade_driver": (
                lambda s: s["value_creation"]["fade"]["schedule"][0].update({"competitive_or_obsolescence_driver_node_ids": []}),
                "fade_schedule",
            ),
            "fade_terminal_tie": (
                lambda s: s["value_creation"]["fade"]["schedule"][-1].update({"average_roic": 0.18}),
                "fade_schedule",
            ),
        }
        for name, (mutate, expected_code) in mutations.items():
            with self.subTest(name=name):
                snapshot = valid_investment_snapshot()
                mutate(snapshot)
                payload = self._validate(snapshot)
                self.assertIn(expected_code, self._codes(payload), payload)

    def test_dcf_residual_income_bridge_and_reverse_implied_driver_are_required(self):
        mutations = {
            "missing_ri": (
                lambda s: s["valuation"].pop("residual_income"),
                "missing_residual_income",
            ),
            "dcf_math": (
                lambda s: s["valuation"]["dcf"].update({"enterprise_value": 999.0}),
                "dcf_identity",
            ),
            "ri_math": (
                lambda s: s["valuation"]["residual_income"].update({"equity_value": 920.0}),
                "residual_income_identity",
            ),
            "reconciliation": (
                lambda s: s["valuation"]["reconciliation"].update({"difference_pct": 0.50}),
                "valuation_reconciliation",
            ),
            "ev_to_equity": (
                lambda s: s["valuation"]["enterprise_to_equity"].update({"equity_value": 900.0}),
                "ev_to_equity_identity",
            ),
            "per_share": (
                lambda s: s["valuation"]["per_share"].update({"value_per_share": 8.0}),
                "per_share_identity",
            ),
            "reverse_implied": (
                lambda s: s["market_implied_expectations"].update({"named_driver": ""}),
                "reverse_implied_driver",
            ),
        }
        for name, (mutate, expected_code) in mutations.items():
            with self.subTest(name=name):
                snapshot = valid_investment_snapshot()
                mutate(snapshot)
                payload = self._validate(snapshot)
                self.assertIn(expected_code, self._codes(payload), payload)

    def test_terminal_growth_is_economically_and_mathematically_constrained(self):
        cases = {
            "growth_below_wacc": (
                lambda s: s["valuation"]["terminal"].update({"growth_rate": 0.10}),
                "terminal_growth",
            ),
            "growth_from_reinvestment": (
                lambda s: s["valuation"]["terminal"].update({"implied_reinvestment_rate": 0.50}),
                "terminal_reinvestment_identity",
            ),
        }
        for name, (mutate, expected_code) in cases.items():
            with self.subTest(name=name):
                snapshot = valid_investment_snapshot()
                mutate(snapshot)
                payload = self._validate(snapshot)
                self.assertIn(expected_code, self._codes(payload), payload)


if __name__ == "__main__":
    unittest.main()
