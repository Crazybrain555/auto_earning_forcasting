import copy
import importlib.util
import unittest
from pathlib import Path


SKILL = Path(__file__).resolve().parents[1]
MODULE_PATH = SKILL / "scripts" / "validate_delivery.py"
SPEC = importlib.util.spec_from_file_location("validate_delivery", MODULE_PATH)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
SPEC.loader.exec_module(MODULE)


def four_shocks(prefix: str):
    return [
        {
            "node_id": f"{prefix}_{dimension}",
            "model_cell_or_formula": f"Scenarios!{column}12",
            "dimension": dimension,
            "cohort_id": "enterprise-2026",
            "operation": "set",
            "value": value,
            "unit": unit,
            "effective_period": "FY2028",
            "lag_periods": 1,
        }
        for dimension, column, value, unit in (
            ("cohort_retention", "B", 0.90, "ratio"),
            ("price", "C", 100.0, "USD/account"),
            ("usage_unit_cost", "D", 0.02, "USD/token"),
            ("sales_efficiency", "E", 0.80, "ARR/USD"),
        )
    ]


def scenarios():
    return [
        {"id": "contraction", "role": "alternative", "probability": 0.25, "shocks": four_shocks("contraction")},
        {"id": "central_operating_path", "role": "reference", "probability": 0.50, "shocks": []},
        {"id": "tight_supply", "role": "alternative", "probability": 0.25, "shocks": four_shocks("tight_supply")},
    ]


class RecurringScenarioContractTest(unittest.TestCase):
    def test_selected_operating_dimensions_pass(self):
        self.assertEqual(MODULE.validate_recurring_scenario_dimensions(scenarios()), [])

    def test_company_specific_subset_is_not_forced_into_four_dimensions(self):
        rows = scenarios()
        rows[0]["shocks"] = [{
            **rows[0]["shocks"][0],
            "dimension": "seat_expansion_after_renewal",
        }]
        rows[2]["shocks"] = [{
            **rows[2]["shocks"][0],
            "dimension": "seat_expansion_after_renewal",
        }]
        self.assertEqual(MODULE.validate_recurring_scenario_dimensions(rows), [])

    def test_selected_dimension_must_be_named_and_unique(self):
        rows = copy.deepcopy(scenarios())
        rows[0]["shocks"][0]["dimension"] = ""
        self.assertTrue(MODULE.validate_recurring_scenario_dimensions(rows))

        rows = copy.deepcopy(scenarios())
        rows[0]["shocks"][1]["dimension"] = rows[0]["shocks"][0]["dimension"]
        self.assertTrue(MODULE.validate_recurring_scenario_dimensions(rows))


if __name__ == "__main__":
    unittest.main()
