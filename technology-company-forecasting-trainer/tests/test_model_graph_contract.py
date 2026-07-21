import copy
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from contract_fixtures import valid_model_graph


SKILL = Path(__file__).resolve().parents[1]
VALIDATOR = SKILL / "scripts" / "validate_model_graph.py"


class ModelGraphContractTest(unittest.TestCase):
    def _validate(self, graph: dict) -> dict:
        self.assertTrue(VALIDATOR.exists(), "missing model-graph validator: scripts/validate_model_graph.py")
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "model_graph.json"
            path.write_text(json.dumps(graph), encoding="utf-8")
            result = subprocess.run(
                [sys.executable, str(VALIDATOR), "--graph", str(path), "--strict"],
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

    def test_valid_dimensioned_acyclic_graph_passes(self):
        payload = self._validate(valid_model_graph())
        self.assertTrue(payload["valid"], payload)

    def test_material_main_line_is_not_rejected_by_an_arbitrary_carrier_count(self):
        graph = valid_model_graph()
        # These are distinct material observations feeding the same causal
        # chain.  Review should challenge whether they are genuinely material;
        # a validator must not replace that judgment with a numeric cap.
        extra_carriers = [
            "demand_anchor",
            "capacity_gate",
            "price_signal",
            "inventory_signal",
        ]
        for node_id in extra_carriers:
            graph["nodes"].append({"id": node_id, "kind": "observable", "unit": "unit"})
        # One combined equation makes every named carrier causal without
        # weakening the one-producer invariant.
        graph["equations"].append(
            {
                "id": "eq_material_carriers_to_units",
                "output": "ai_units",
                "operation": "add",
                "inputs": extra_carriers,
            }
        )
        graph["main_line"]["carrier_node_ids"] = extra_carriers
        payload = self._validate(graph)
        self.assertTrue(payload["valid"], payload)

    def test_main_line_cannot_terminate_at_an_untyped_generic_profit_node(self):
        graph = valid_model_graph()
        target_ids = set(graph["main_line"]["target_node_ids"])
        for node in graph["nodes"]:
            if node.get("id") in target_ids:
                node["financial_role"] = "profit"
        payload = self._validate(graph)
        self.assertIn("main_line_financial_chain", self._codes(payload), payload)

    def test_noncontrolling_interest_role_is_explicit_even_when_the_value_is_zero(self):
        graph = valid_model_graph()
        next(node for node in graph["nodes"] if node["id"] == "nci_net_income").pop(
            "financial_role"
        )
        payload = self._validate(graph)
        self.assertIn("main_line_financial_chain", self._codes(payload), payload)

    def test_separately_connected_roles_cannot_fake_one_coherent_profit_chain(self):
        graph = valid_model_graph()
        graph["nodes"].append(
            {
                "id": "orphan_operating_profit",
                "kind": "input",
                "unit": "USD",
                "financial_role": "operating_profit",
            }
        )
        pretax_equation = next(
            equation for equation in graph["equations"] if equation["id"] == "eq_pretax_profit"
        )
        pretax_equation["inputs"][0] = "orphan_operating_profit"
        graph["main_line"]["carrier_node_ids"] = ["orphan_operating_profit"]
        payload = self._validate(graph)
        self.assertIn("main_line_financial_chain", self._codes(payload), payload)

    def test_schema_and_template_name_the_typed_financial_chain(self):
        schema_text = (SKILL / "assets" / "schemas" / "model_graph.schema.json").read_text(
            encoding="utf-8"
        )
        template_text = (SKILL / "assets" / "templates" / "model_graph_template.json").read_text(
            encoding="utf-8"
        )
        for role in (
            "revenue",
            "operating_profit",
            "pretax_profit",
            "tax_expense",
            "gaap_net_income_attributable",
        ):
            self.assertIn(role, schema_text)
            self.assertIn(role, template_text)

    def test_arithmetic_unit_mismatch_is_rejected(self):
        graph = valid_model_graph()
        next(n for n in graph["nodes"] if n["id"] == "ai_revenue")["unit"] = "USD/unit"
        payload = self._validate(graph)
        self.assertIn("unit_mismatch", self._codes(payload), payload)

    def test_cycle_is_rejected(self):
        graph = valid_model_graph()
        graph["equations"][0] = {
            "id": "eq_revenue",
            "output": "ai_revenue",
            "operation": "add",
            "inputs": ["profit", "cash_cost"],
        }
        payload = self._validate(graph)
        self.assertIn("cycle", self._codes(payload), payload)

    def test_each_derived_node_has_one_producer(self):
        graph = valid_model_graph()
        graph["equations"].append(copy.deepcopy(graph["equations"][0]) | {"id": "eq_revenue_2"})
        payload = self._validate(graph)
        self.assertIn("multiple_producers", self._codes(payload), payload)

    def test_partial_or_overlapping_partition_cannot_claim_parent_reconciliation(self):
        graph = valid_model_graph()
        graph["equations"][0]["partition"] = {
            "partition_id": "disclosed-top-customers",
            "dimension": "customer",
            "exhaustive": False,
            "mutually_exclusive": True,
            "reconciles_to_parent": True,
        }

        payload = self._validate(graph)

        self.assertIn("partition", self._codes(payload), payload)

    def test_partial_partition_is_valid_when_used_only_as_a_cross_check(self):
        graph = valid_model_graph()
        graph["equations"][0]["partition"] = {
            "partition_id": "disclosed-top-customers",
            "dimension": "customer",
            "exhaustive": False,
            "mutually_exclusive": True,
            "reconciles_to_parent": False,
        }

        payload = self._validate(graph)

        self.assertTrue(payload["valid"], payload)

    def test_main_line_carriers_reach_profit_or_fcf_and_name_challenges(self):
        cases = {
            "unreachable": (lambda g: g["main_line"].update({"carrier_node_ids": ["competitive_supply"]}), "main_line_unreachable"),
            "not_attributable_net_income": (
                lambda g: g["main_line"].update({"target_node_ids": ["ai_revenue"]}),
                "main_line_financial_chain",
            ),
            "no_falsification": (lambda g: g["main_line"].update({"falsification_ids": []}), "main_line_falsification"),
            "no_competitor_response": (lambda g: g["main_line"].update({"competitor_response_node_ids": []}), "main_line_competitor_response"),
        }
        for name, (mutate, expected_code) in cases.items():
            with self.subTest(name=name):
                graph = valid_model_graph()
                mutate(graph)
                payload = self._validate(graph)
                self.assertIn(expected_code, self._codes(payload), payload)


if __name__ == "__main__":
    unittest.main()
