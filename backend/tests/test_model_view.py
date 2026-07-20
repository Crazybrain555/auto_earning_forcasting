from __future__ import annotations

import copy
import json
from pathlib import Path

from backend.app import data, db


def _v2_snapshot() -> dict:
    return {
        "forecast_contract_version": "2.0",
        "schema_version": "2.0",
        "investment_case": {
            "decision_question": "What AI ASP is required for value creation?",
            "variant_view": "The market prices a faster ASP fade than the evidence.",
            "one_line_thesis": "AI ASP persists longer than the market expects.",
            "margin_of_safety_pct": 25.0,
            "main_line_node_ids": ["ai_asp"],
            "falsification_ids": ["asp_break"],
            "permanent_loss_paths": ["A competing architecture removes pricing power."],
        },
        "driver_tree": {
            "main_line_id": "ai-price-duration",
            "thesis_carriers": [
                {"node_id": "ai_asp", "claim": "Contract ASP stays above USD 50/unit."}
            ],
            "segments": [],
        },
        "integrated_model": {"periods": [{"period": "FY2027"}]},
        "value_creation": {
            "wacc": 0.10,
            "periods": [{"period": "FY2027", "roic": 0.20, "reinvestment_rate": 0.40}],
            "fade": {
                "terminal_roic": 0.15,
                "years_to_fade": 10,
                "competitive_response": "New supply compresses excess returns.",
            },
        },
        "valuation": {
            "currency": "USD",
            "dcf": {"enterprise_value": 1000.0},
            "residual_income": {"equity_value": 930.0},
            "enterprise_to_equity": {"equity_value": 910.0},
            "per_share": {"value_per_share": 9.10},
            "terminal": {"wacc": 0.10, "growth_rate": 0.03},
        },
        "market_implied_expectations": {
            "price_as_of": "2026-07-18",
            "observed_price": 7.0,
            "named_driver": "AI ASP",
            "implied_driver_value": 42.0,
            "model_driver_value": 50.0,
            "unit": "USD/unit",
            "falsification_trigger": "Contract ASP falls below USD 42/unit.",
        },
        # Deliberately stale: v2 structured valuation must win in the adapter.
        "valuation_summary": {
            "current_price": 6.5,
            "price_currency": "OLD",
            "price_as_of": "2026-07-01",
            "fair_value": {"bear": 7.0, "base": 6.0, "bull": 12.0},
            "recommended_buy_price": 4.0,
            "action": "watch",
            "one_line_thesis": "stale summary",
        },
        "monitoring": {
            "driver_ids": ["ai_asp", "competitive_supply"],
            "last_updated_at": "2026-07-18T00:00:00Z",
        },
        "breakpoints": ["Gross margin falls below 30%."],
        # A v2 view must never treat this legacy payload as model logic.
        "mechanism_weights": {"unit-volume-price-cost": 1.0},
    }


def _model_graph() -> dict:
    return {
        "schema_version": "2.0",
        "nodes": [
            {"id": "ai_units", "kind": "input", "unit": "unit"},
            {"id": "ai_asp", "kind": "input", "unit": "USD/unit"},
            {"id": "ai_revenue", "kind": "derived", "unit": "USD"},
            {"id": "cash_cost", "kind": "input", "unit": "USD"},
            {"id": "profit", "kind": "derived", "unit": "USD", "financial_role": "profit"},
            {"id": "asp_break", "kind": "falsification", "unit": "dimensionless"},
            {
                "id": "competitive_supply",
                "kind": "competitor_response",
                "unit": "dimensionless",
            },
        ],
        "equations": [
            {
                "id": "eq_revenue",
                "output": "ai_revenue",
                "operation": "multiply",
                "inputs": ["ai_units", "ai_asp"],
            },
            {
                "id": "eq_profit",
                "output": "profit",
                "operation": "subtract",
                "inputs": ["ai_revenue", "cash_cost"],
            },
        ],
        "main_line": {
            "carrier_node_ids": ["ai_asp"],
            "target_node_ids": ["profit"],
            "falsification_ids": ["asp_break"],
            "competitor_response_node_ids": ["competitive_supply"],
        },
    }


def test_v2_model_view_exposes_causal_value_contract_without_mutating_snapshot() -> None:
    snapshot = _v2_snapshot()
    before = copy.deepcopy(snapshot)

    view = data.build_model_view(snapshot, _model_graph())

    assert snapshot == before
    assert view["contract_version"] == "2.0"
    assert view["mode"] == "causal_value_model"
    assert view["legacy"] is False
    assert view["investment_case"]["variant_view"].startswith("The market")
    assert view["main_line"]["id"] == "ai-price-duration"
    assert view["main_line"]["carrier_node_ids"] == ["ai_asp"]
    assert view["main_line"]["target_node_ids"] == ["profit"]
    chain = view["main_line"]["profit_causal_chain"]
    assert [equation["id"] for equation in chain["equations"]] == [
        "eq_revenue",
        "eq_profit",
    ]
    assert {node["id"] for node in chain["nodes"]} == {
        "ai_units",
        "ai_asp",
        "ai_revenue",
        "cash_cost",
        "profit",
    }
    assert view["value_creation"]["periods"][0]["roic"] == 0.20
    assert view["valuation"]["methods"]["dcf"]["enterprise_value"] == 1000.0
    assert view["valuation"]["summary"]["fair_value"]["base"] == 9.10
    assert view["market_implied_expectations"]["named_driver"] == "AI ASP"
    assert view["monitoring"]["driver_ids"] == ["ai_asp", "competitive_supply"]
    assert set(view["falsification"]["ids"]) == {"asp_break"}
    assert any(
        trigger.startswith("Contract ASP falls below")
        for trigger in view["falsification"]["triggers"]
    )
    assert "mechanism_weights" not in json.dumps(view)


def test_v1_model_view_is_read_only_legacy_decomposition_without_weight_values() -> None:
    snapshot = {
        "forecast_id": "fcst://technology/LEGACY/20200101/v1",
        "mechanism_weights": {
            "orders-backlog-recognition": 0.75,
            "capacity-utilization-yield": 0.25,
        },
        "company_lenses": ["lens-equipment-process-control"],
        "outputs": {
            "market_implied": {"implied_revenue": 100.0},
        },
        "valuation_summary": {
            "fair_value": {"bear": 80.0, "base": 100.0, "bull": 125.0},
            "one_line_thesis": "Legacy thesis",
        },
        "breakpoints": ["Backlog conversion falls below 70%."],
    }

    view = data.build_model_view(snapshot)

    assert view["contract_version"] == "legacy-v1"
    assert view["mode"] == "legacy_decomposition"
    assert view["legacy"] is True
    assert view["legacy_decomposition"] == {
        "label": "legacy decomposition metadata",
        "components": [
            "capacity-utilization-yield",
            "orders-backlog-recognition",
        ],
        "company_lenses": ["lens-equipment-process-control"],
    }
    assert view["investment_case"]["one_line_thesis"] == "Legacy thesis"
    assert view["market_implied_expectations"] == {"implied_revenue": 100.0}
    assert view["falsification"]["breakpoints"] == [
        "Backlog conversion falls below 70%."
    ]
    encoded = json.dumps(view)
    assert "mechanism_weights" not in encoded
    assert "0.75" not in encoded
    assert "0.25" not in encoded


def test_case_detail_adds_model_view_but_keeps_raw_snapshot_byte_equivalent(
    monkeypatch, tmp_path: Path
) -> None:
    case_dir = tmp_path / "round-v2" / "TEST@2026-07-18"
    case_dir.mkdir(parents=True)
    snapshot = _v2_snapshot()
    snapshot_text = json.dumps(snapshot, ensure_ascii=False, indent=2) + "\n"
    (case_dir / "run_manifest.json").write_text(
        json.dumps({"entity": "Test Co", "security": "TEST"}), encoding="utf-8"
    )
    (case_dir / "forecast_snapshot.json").write_text(snapshot_text, encoding="utf-8")
    (case_dir / "model_graph.json").write_text(
        json.dumps(_model_graph(), ensure_ascii=False), encoding="utf-8"
    )
    (case_dir / "driver_monitoring.csv").write_text(
        "driver_id,series,frequency,trigger_operator,trigger_value,action_if_breached,status\n"
        "ai_asp,Contract ASP,quarterly,below,42,re-underwrite,active\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(data, "RUNS_ROOT", tmp_path)

    detail = data.case_detail("round-v2", "TEST@2026-07-18")

    assert detail is not None
    assert detail["forecast_snapshot"] == snapshot
    assert "model_view" not in detail["forecast_snapshot"]
    assert (case_dir / "forecast_snapshot.json").read_text(encoding="utf-8") == snapshot_text
    assert detail["model_view"]["main_line"]["target_node_ids"] == ["profit"]
    assert detail["model_view"]["monitoring"]["drivers"][0]["driver_id"] == "ai_asp"


def test_db_ingest_prefers_v2_structured_valuation_and_keeps_v1_compatible(
    monkeypatch, tmp_path: Path
) -> None:
    monkeypatch.setattr(db, "DB_PATH", tmp_path / "forecast.db")
    db.init()
    case = {
        "round_id": "round-v2",
        "case_id": "TEST@2026-07-18",
        "security": "TEST",
        "entity": "Test Co",
    }

    db.ingest_case(case, _v2_snapshot(), {})

    stored = db.history("TEST")[0]["valuation"]
    assert stored["current_price"] == 7.0
    assert stored["price_as_of"] == "2026-07-18"
    assert stored["price_currency"] == "USD"
    assert stored["fair_value"] == {"bear": 7.0, "base": 9.10, "bull": 12.0}
    assert stored["recommended_buy_price"] == 6.825
    assert stored["one_line_thesis"] == "AI ASP persists longer than the market expects."

    legacy = {
        "valuation_summary": {
            "current_price": 40.0,
            "price_currency": "USD",
            "price_as_of": "2020-01-01",
            "fair_value": {"bear": 35.0, "base": 50.0, "bull": 60.0},
            "recommended_buy_price": 38.0,
            "action": "accumulate",
            "one_line_thesis": "Legacy thesis",
        }
    }
    extracted = db.extract_valuation(legacy)
    assert extracted == legacy["valuation_summary"]
