import copy
import importlib.util
from pathlib import Path


SKILL = Path(__file__).resolve().parents[1]
MODULE_PATH = SKILL / "scripts" / "validate_delivery.py"
SPEC = importlib.util.spec_from_file_location("delivery_scenario_contract", MODULE_PATH)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
SPEC.loader.exec_module(MODULE)


GRAPH_NODES = {
    "asp": {"id": "asp", "kind": "input", "unit": "USD/unit"},
    "capacity": {"id": "capacity", "kind": "state", "unit": "unit"},
    "revenue": {"id": "revenue", "kind": "derived", "unit": "USD"},
}


def _scenarios() -> list[dict]:
    return [
        {
            "id": "demand_contraction", "role": "alternative", "probability": 0.3,
            "shocks": [{
                "node_id": "asp", "operation": "set", "value": 40,
                "unit": "USD/unit", "model_cell_or_formula": "Drivers!F18",
                "effective_period": "FY2028", "lag_periods": 1,
            }],
        },
        {"id": "central_operating_path", "role": "reference", "probability": 0.4, "shocks": []},
        {
            "id": "supply_tightness", "role": "alternative", "probability": 0.3,
            "shocks": [{
                "node_id": "capacity", "operation": "set", "value": 120,
                "unit": "unit", "model_cell_or_formula": "=Drivers!G20",
                "effective_period": "FY2028Q2", "lag_periods": 0,
            }],
        },
    ]


def _validate(scenarios: list[dict]) -> list[str]:
    validator = getattr(MODULE, "validate_scenario_shocks", None)
    if validator is None:
        return []
    return validator(scenarios, graph_nodes=GRAPH_NODES, forecast_periods={"FY2027", "FY2028"})


def test_generic_scenario_shocks_require_executable_cell_unit_period_and_lag():
    mutations = {
        "unit": "",
        "model_cell_or_formula": "",
        "effective_period": "",
        "lag_periods": -1,
    }
    for field, value in mutations.items():
        scenarios = copy.deepcopy(_scenarios())
        scenarios[0]["shocks"][0][field] = value
        problems = _validate(scenarios)
        assert any(field in item for item in problems), (field, problems)


def test_generic_scenario_shocks_validate_node_unit_and_forecast_period():
    scenarios = _scenarios()
    scenarios[0]["shocks"][0]["unit"] = "USD"
    assert any("unit" in item for item in _validate(scenarios))

    scenarios = _scenarios()
    scenarios[0]["shocks"][0]["node_id"] = "unknown"
    assert any("unknown node" in item for item in _validate(scenarios))

    scenarios = _scenarios()
    scenarios[0]["shocks"][0]["node_id"] = "revenue"
    scenarios[0]["shocks"][0]["unit"] = "USD"
    assert any("derived" in item for item in _validate(scenarios))

    scenarios = _scenarios()
    scenarios[0]["shocks"][0]["effective_period"] = "FY2035"
    assert any("effective_period" in item for item in _validate(scenarios))

    scenarios = _scenarios()
    scenarios[0]["shocks"][0]["effective_period"] = "foo-FY2028-later"
    assert any("effective_period" in item for item in _validate(scenarios))


def test_generic_scenario_shocks_reject_non_integer_lag_and_non_executable_cell():
    scenarios = _scenarios()
    scenarios[0]["shocks"][0]["lag_periods"] = 1.5
    assert any("lag_periods" in item for item in _validate(scenarios))

    scenarios = _scenarios()
    scenarios[0]["shocks"][0]["model_cell_or_formula"] = "some workbook place"
    assert any("model_cell_or_formula" in item for item in _validate(scenarios))


def test_generic_scenario_shock_value_requires_a_finite_authored_json_number():
    for value in (
        "forty narrative units", "40", True, float("nan"), float("inf"), float("-inf")
    ):
        scenarios = copy.deepcopy(_scenarios())
        scenarios[0]["shocks"][0]["value"] = value
        problems = _validate(scenarios)
        assert any(
            "value" in problem and "finite" in problem for problem in problems
        ), (value, problems)


def test_well_formed_generic_scenario_shocks_pass():
    assert _validate(_scenarios()) == []


def test_alternative_role_requires_a_named_causal_shock_but_reference_does_not():
    scenarios = copy.deepcopy(_scenarios())
    scenarios[0]["shocks"] = []
    validate_roles = getattr(MODULE, "validate_scenario_roles", None)
    assert validate_roles is not None
    assert any("alternative" in item and "shock" in item for item in validate_roles(scenarios))

    scenarios = copy.deepcopy(_scenarios())
    scenarios[1]["shocks"] = []
    assert validate_roles(scenarios) == []

    reference_only = [copy.deepcopy(scenarios[1])]
    reference_only[0]["probability"] = 1.0
    assert validate_roles(reference_only) == []


def test_delivery_routes_every_scenario_through_generic_shock_validator():
    text = (SKILL / "scripts/validate_delivery.py").read_text(encoding="utf-8")
    scenario_start = text.index('scenario_path = workspace / "scenario_set.json"')
    block = text[scenario_start:]
    assert "parse_scenario_catalog(" in block
    assert "validate_scenario_shocks(" in block
    assert "graph_nodes=graph_nodes" in block
    assert "forecast_periods=" in block
