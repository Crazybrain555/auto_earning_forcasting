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


def valid_rows():
    return [
        {
            "driver_id": "ai_asp",
            "model_cell_or_formula": "Drivers!F18",
            "monitor_type": "continuous",
            "thesis_link": "main line",
            "series": "contract ASP",
            "source_id": "SRC1",
            "frequency": "quarterly",
            "last_observed_at": "2026-06-30",
            "next_expected_at": "2026-09-30",
            "milestone_date": "",
            "current_value": "48",
            "model_value": "50",
            "unit": "USD/unit",
            "trigger_operator": "below",
            "trigger_value": "42",
            "action_if_breached": "re-underwrite price path",
            "owner": "analyst",
            "status": "active",
        },
        {
            "driver_id": "asp_break",
            "model_cell_or_formula": "Tech_Gates!B12",
            "monitor_type": "milestone",
            "thesis_link": "falsification",
            "series": "contract ASP breach",
            "source_id": "SRC1",
            "frequency": "event_driven",
            "last_observed_at": "2026-06-30",
            "next_expected_at": "2026-08-15",
            "milestone_date": "2026-08-15",
            "current_value": "0",
            "model_value": "0",
            "unit": "dimensionless",
            "trigger_operator": "above",
            "trigger_value": "0",
            "action_if_breached": "invalidate base case",
            "owner": "analyst",
            "status": "active",
        },
        {
            "driver_id": "tech_gate",
            "model_cell_or_formula": "Tech_Gates!H12",
            "monitor_type": "milestone",
            "thesis_link": "technology gate",
            "series": "qualification completion",
            "source_id": "SRC2",
            "frequency": "event_driven",
            "last_observed_at": "2026-06-30",
            "next_expected_at": "2026-10-15",
            "milestone_date": "2026-10-15",
            "current_value": "0",
            "model_value": "1",
            "unit": "binary",
            "trigger_operator": "below",
            "trigger_value": "1",
            "action_if_breached": "delay qualification ramp",
            "owner": "technology analyst",
            "status": "active",
        },
    ]


class MonitoringContractTest(unittest.TestCase):
    def _problems(self, rows):
        return MODULE.validate_monitor_rows(
            rows,
            graph_nodes={"ai_asp": {}, "asp_break": {}, "tech_gate": {}},
            main_line_carriers={"ai_asp"},
            main_line_falsifications={"asp_break"},
            source_ids={"SRC1", "SRC2"},
            material_technology_node_ids={"tech_gate"},
        )[0]

    def test_complete_executable_register_passes(self):
        self.assertEqual(self._problems(valid_rows()), [])

    def test_each_executable_field_is_a_hard_gate(self):
        mutations = {
            "missing_cell": (0, "model_cell_or_formula", ""),
            "invalid_cell": (0, "model_cell_or_formula", "driver formula"),
            "unknown_source": (0, "source_id", "UNKNOWN"),
            "invalid_last_date": (0, "last_observed_at", "soon"),
            "invalid_next_date": (0, "next_expected_at", "later"),
            "blank_current": (0, "current_value", ""),
            "blank_model": (0, "model_value", ""),
            "blank_unit": (0, "unit", ""),
            "invalid_operator": (0, "trigger_operator", "roughly"),
            "blank_threshold": (0, "trigger_value", ""),
            "blank_action": (0, "action_if_breached", ""),
            "blank_owner": (0, "owner", ""),
            "invalid_milestone_date": (1, "milestone_date", "next quarter"),
        }
        for name, (index, field, value) in mutations.items():
            with self.subTest(name=name):
                rows = copy.deepcopy(valid_rows())
                rows[index][field] = value
                self.assertTrue(self._problems(rows), name)

    def test_main_line_falsifier_and_material_technology_gate_must_be_monitored(self):
        for driver_id in ("ai_asp", "asp_break", "tech_gate"):
            with self.subTest(driver_id=driver_id):
                rows = [row for row in valid_rows() if row["driver_id"] != driver_id]
                self.assertTrue(self._problems(rows))


if __name__ == "__main__":
    unittest.main()
