"""Small, executable fixtures for the v2 causal/value contracts.

These are intentionally economic identities rather than company-specific
examples.  Contract tests mutate one identity at a time, which keeps failures
diagnostic and gives the validators an unambiguous implementation target.
"""

from __future__ import annotations


def valid_model_graph() -> dict:
    """A typed thesis line through the full reported-profit chain."""

    return {
        "schema_version": "2.0",
        "graph_id": "graph://technology/TEST/20260718/v2",
        "as_of": "2026-07-18T00:00:00Z",
        "nodes": [
            {"id": "ai_units", "kind": "input", "unit": "unit"},
            {"id": "ai_asp", "kind": "input", "unit": "USD/unit", "data_series_ids": ["D3", "D4"]},
            {
                "id": "ai_revenue",
                "kind": "derived",
                "unit": "USD",
                "financial_role": "revenue",
            },
            {"id": "cash_cost", "kind": "input", "unit": "USD"},
            {
                "id": "operating_profit",
                "kind": "derived",
                "unit": "USD",
                "financial_role": "operating_profit",
            },
            {"id": "nonoperating_income", "kind": "input", "unit": "USD"},
            {
                "id": "pretax_profit",
                "kind": "derived",
                "unit": "USD",
                "financial_role": "pretax_profit",
            },
            {
                "id": "tax_expense",
                "kind": "input",
                "unit": "USD",
                "financial_role": "tax_expense",
            },
            {
                "id": "nci_net_income",
                "kind": "input",
                "unit": "USD",
                "financial_role": "noncontrolling_interest_net_income",
            },
            {
                "id": "profit",
                "kind": "derived",
                "unit": "USD",
                "financial_role": "gaap_net_income_attributable",
            },
            {
                "id": "asp_break",
                "kind": "falsification",
                "unit": "dimensionless",
            },
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
                "id": "eq_operating_profit",
                "output": "operating_profit",
                "operation": "subtract",
                "inputs": ["ai_revenue", "cash_cost"],
            },
            {
                "id": "eq_pretax_profit",
                "output": "pretax_profit",
                "operation": "add",
                "inputs": ["operating_profit", "nonoperating_income"],
            },
            {
                "id": "eq_profit",
                "output": "profit",
                "operation": "subtract",
                "inputs": ["pretax_profit", "tax_expense", "nci_net_income"],
            },
        ],
        "main_line": {
            "carrier_node_ids": ["ai_units", "ai_asp"],
            "target_node_ids": ["profit"],
            "falsification_ids": ["asp_break"],
            "competitor_response_node_ids": ["competitive_supply"],
        },
    }


def valid_investment_snapshot() -> dict:
    """A compact integrated model whose accounting/value identities close."""

    return {
        "outputs": {
            "year_1": {
                "period": "FY2027",
                "revenue_point": 100.0,
                "operating_profit_point": 20.0,
                "pretax_profit_point": 19.0,
                "tax_expense_point": 5.0,
                "noncontrolling_interest_net_income_point": 2.0,
                "net_income_point": 12.0,
                "profit_point": 12.0,
                "point_evaluable": True,
            },
            "year_2": {
                "period": "FY2028",
                "revenue_point": 112.0,
                "operating_profit_point": 24.0,
                "pretax_profit_point": 23.0,
                "tax_expense_point": 6.0,
                "noncontrolling_interest_net_income_point": 3.0,
                "net_income_point": 14.0,
                "profit_point": 14.0,
                "point_evaluable": True,
            },
        },
        "persistence_analysis": {
            "mean_reversion": {
                "status": "accepted",
                "object": "normalized_operating_margin",
                "unit": "ratio",
                "reference_class": "same lifecycle, qualification gate, capital intensity and cycle state",
                "reference_class_source_ids": ["SRC0", "SRC5"],
                "target_median": 0.18,
                "target_low": 0.12,
                "target_high": 0.24,
                "sample_selection_limits": "Survivors and firms without comparable qualification gates are excluded.",
                "company_departure": "Customer qualification delays the response from new competitive capacity.",
                "speed_driver_node_ids": ["competitive_supply"],
                "fade_horizon_periods": 5,
                "falsification_node_ids": ["asp_break"],
                "scenario_ids": ["bear", "base", "bull"],
            },
            "cost_behavior": [
                {
                    "cost_line": "cash_operating_cost",
                    "status": "accepted",
                    "materiality": "critical",
                    "activity_driver_node_id": "ai_units",
                    "activity_unit": "unit",
                    "elasticity_up": 0.55,
                    "elasticity_down": 0.25,
                    "adjustment_lag_periods": 2,
                    "committed_resource_floor": 30.0,
                    "floor_unit": "USDm",
                    "exit_or_adjustment_cost": 5.0,
                    "estimation_method": "company history plus named scenario sensitivity",
                    "source_ids": ["SRC0", "SRC5"],
                    "scenario_ids": ["bear", "base", "bull"],
                    "notes": "Down-state cost behavior reflects committed facilities and exit costs.",
                }
            ],
        },
        "investment_case": {
            "decision_question": "What AI ASP is required for value creation?",
            "variant_view": "The market prices a faster ASP fade than the model evidence.",
            "margin_of_safety_pct": 25.0,
            "falsification_ids": ["asp_break"],
        },
        "integrated_model": {
            "periods": [
                {
                    "period": "FY2027",
                    "income_statement": {
                        "revenue": 100.0,
                        "operating_costs_and_expenses": 80.0,
                        "operating_profit": 20.0,
                        "nonoperating_income_expense_net": -1.0,
                        "pretax_profit": 19.0,
                        "tax_expense": 5.0,
                        "tax": 5.0,
                        "nopat": 15.0,
                        "net_income": 14.0,
                        "net_income_attributable_to_noncontrolling_interests": 2.0,
                        "net_income_attributable": 12.0,
                    },
                    "balance_sheet": {
                        "cash": 15.0,
                        "assets": 150.0,
                        "liabilities": 60.0,
                        "equity": 90.0,
                    },
                    "cash_flow_statement": {
                        "net_income": 14.0,
                        "cash_from_operations": 20.0,
                        "capex": 8.0,
                        "free_cash_flow": 12.0,
                        "net_change_in_cash": 5.0,
                    },
                    "roll_forwards": {
                        "cash": {"opening": 10.0, "net_change": 5.0, "closing": 15.0},
                        "ppe": {
                            "opening": 60.0,
                            "capex": 8.0,
                            "depreciation": 6.0,
                            "disposals": 0.0,
                            "closing": 62.0,
                        },
                        "debt": {
                            "opening": 30.0,
                            "borrowings": 4.0,
                            "repayments": 2.0,
                            "closing": 32.0,
                        },
                        "working_capital": {"opening": 20.0, "change": 3.0, "closing": 23.0},
                    },
                },
                {
                    "period": "FY2028",
                    "income_statement": {
                        "revenue": 112.0,
                        "operating_costs_and_expenses": 88.0,
                        "operating_profit": 24.0,
                        "nonoperating_income_expense_net": -1.0,
                        "pretax_profit": 23.0,
                        "tax_expense": 6.0,
                        "tax": 6.0,
                        "nopat": 18.0,
                        "net_income": 17.0,
                        "net_income_attributable_to_noncontrolling_interests": 3.0,
                        "net_income_attributable": 14.0,
                    },
                    "balance_sheet": {
                        "cash": 19.0,
                        "assets": 170.0,
                        "liabilities": 65.0,
                        "equity": 105.0,
                    },
                    "cash_flow_statement": {
                        "net_income": 17.0,
                        "cash_from_operations": 24.0,
                        "capex": 10.0,
                        "free_cash_flow": 14.0,
                        "net_change_in_cash": 4.0,
                    },
                    "roll_forwards": {
                        "cash": {"opening": 15.0, "net_change": 4.0, "closing": 19.0},
                        "ppe": {
                            "opening": 62.0,
                            "capex": 10.0,
                            "depreciation": 7.0,
                            "disposals": 0.0,
                            "closing": 65.0,
                        },
                        "debt": {
                            "opening": 32.0,
                            "borrowings": 2.0,
                            "repayments": 4.0,
                            "closing": 30.0,
                        },
                        "working_capital": {"opening": 23.0, "change": 2.0, "closing": 25.0},
                    },
                },
            ]
        },
        "value_creation": {
            "wacc": 0.10,
            "periods": [
                {
                    "period": "FY2027",
                    "reported_nopat": 14.0,
                    "after_tax_normalization_adjustments": 1.0,
                    "normalized_nopat": 15.0,
                    "beginning_invested_capital": 75.0,
                    "ending_invested_capital": 81.0,
                    "average_invested_capital": 78.0,
                    "average_roic": 15.0 / 78.0,
                    "reinvestment": 6.0,
                    "invested_capital_bridge_adjustment": 0.0,
                    "reinvestment_rate": 0.40,
                    "prior_normalized_nopat": 13.8,
                    "incremental_invested_capital": 6.0,
                    "incremental_nopat": 1.2,
                    "incremental_roic": 0.20,
                    "incremental_return_lag_periods": 1,
                    "fundamental_growth": 0.08,
                },
                {
                    "period": "FY2028",
                    "reported_nopat": 17.0,
                    "after_tax_normalization_adjustments": 1.0,
                    "normalized_nopat": 18.0,
                    "beginning_invested_capital": 81.0,
                    "ending_invested_capital": 90.0,
                    "average_invested_capital": 85.5,
                    "average_roic": 18.0 / 85.5,
                    "reinvestment": 9.0,
                    "invested_capital_bridge_adjustment": 0.0,
                    "reinvestment_rate": 0.50,
                    "prior_normalized_nopat": 15.0,
                    "incremental_invested_capital": 9.0,
                    "incremental_nopat": 3.0,
                    "incremental_roic": 1.0 / 3.0,
                    "incremental_return_lag_periods": 1,
                    "fundamental_growth": 1.0 / 6.0,
                },
            ],
            "fade": {
                "terminal_roic": 0.15,
                "years_to_fade": 10,
                "competitive_response": "New supply compresses excess returns over time.",
                "schedule": [
                    {
                        "period": "FY2029",
                        "average_roic": 0.20,
                        "incremental_roic": 0.25,
                        "reinvestment_rate": 0.40,
                        "fundamental_growth": 0.10,
                        "competitive_or_obsolescence_driver_node_ids": ["competitive_supply"],
                        "erosion_or_renewal_event": "Qualified competitor capacity begins shipping.",
                    },
                    {
                        "period": "Terminal",
                        "average_roic": 0.15,
                        "incremental_roic": 0.15,
                        "reinvestment_rate": 0.20,
                        "fundamental_growth": 0.03,
                        "competitive_or_obsolescence_driver_node_ids": ["competitive_supply"],
                        "erosion_or_renewal_event": "Returns converge to the evidenced steady-state barrier.",
                    },
                ],
            },
        },
        "valuation": {
            "currency": "USD",
            "dcf": {
                "pv_explicit_free_cash_flow": 450.0,
                "pv_terminal_value": 550.0,
                "enterprise_value": 1000.0,
            },
            "residual_income": {
                "current_book_value": 600.0,
                "pv_residual_income": 330.0,
                "equity_value": 930.0,
            },
            "reconciliation": {
                "dcf_equity_value": 910.0,
                "residual_income_equity_value": 930.0,
                "difference_pct": 20.0 / 910.0,
                "explanation": "Residual-income fade is two years slower than the DCF fade.",
            },
            "enterprise_to_equity": {
                "enterprise_value": 1000.0,
                "cash": 50.0,
                "non_operating_assets": 20.0,
                "debt": 150.0,
                "noncontrolling_interest": 10.0,
                "other_adjustments": 0.0,
                "equity_value": 910.0,
            },
            "per_share": {
                "equity_value": 910.0,
                "diluted_shares": 100.0,
                "value_per_share": 9.10,
            },
            "terminal": {
                "wacc": 0.10,
                "growth_rate": 0.03,
                "terminal_roic": 0.15,
                "implied_reinvestment_rate": 0.20,
            },
        },
        "market_implied_expectations": {
            "price_as_of": "2026-07-18",
            "observed_price": 7.0,
            "named_driver": "AI ASP (USD/unit)",
            "implied_driver_value": 42.0,
            "model_driver_value": 50.0,
            "unit": "USD/unit",
            "falsification_trigger": "Contract ASP falls below USD 42/unit.",
        },
    }


def valid_recurring_snapshot() -> dict:
    """A recurring/usage model with cohort, cost and statement rolls."""

    snapshot = valid_investment_snapshot()
    snapshot["analysis_primitives"] = ["recurring-contract", "platform-usage"]
    first = snapshot["integrated_model"]["periods"][0]
    first["income_statement"].update(
        {
            "subscription_revenue": 99.75,
            "subscription_cogs": 45.0,
            "capitalized_development_amortization": 2.0,
        }
    )
    first["balance_sheet"].update(
        {
            "accounts_receivable": 20.0,
            "accounts_payable": 15.0,
            "deferred_revenue": 30.25,
            "capitalized_development": 9.0,
            "diluted_shares": 101.0,
        }
    )
    first["cash_flow_statement"].update(
        {"fixed_capex": 5.0, "capitalized_development_cash": 3.0}
    )
    first["roll_forwards"].update(
        {
            "deferred_revenue": {
                "opening": 20.0,
                "billings": 110.0,
                "revenue_recognized": 99.75,
                "other_adjustments": 0.0,
                "closing": 30.25,
            },
            "accounts_receivable": {
                "opening": 15.0,
                "credit_billings": 110.0,
                "cash_collections": 105.0,
                "writeoffs": 0.0,
                "other_adjustments": 0.0,
                "closing": 20.0,
            },
            "accounts_payable": {
                "opening": 10.0,
                "purchases_or_accruals": 45.0,
                "cash_payments": 40.0,
                "other_adjustments": 0.0,
                "closing": 15.0,
            },
            "capitalized_development": {
                "opening": 8.0,
                "capitalized_spend": 3.0,
                "amortization": 2.0,
                "impairment": 0.0,
                "disposals": 0.0,
                "closing": 9.0,
            },
            "diluted_shares": {
                "opening": 100.0,
                "sbc_and_option_issuance": 2.0,
                "buybacks": 1.0,
                "other": 0.0,
                "closing": 101.0,
            },
        }
    )
    second = snapshot["integrated_model"]["periods"][1]
    second["income_statement"].update(
        {
            "subscription_revenue": 110.25,
            "subscription_cogs": 46.0,
            "capitalized_development_amortization": 2.0,
        }
    )
    second["balance_sheet"].update(
        {
            "accounts_receivable": 22.0,
            "accounts_payable": 16.0,
            "deferred_revenue": 35.0,
            "capitalized_development": 10.0,
            "diluted_shares": 102.0,
        }
    )
    second["cash_flow_statement"].update(
        {"fixed_capex": 7.0, "capitalized_development_cash": 3.0}
    )
    second["roll_forwards"].update(
        {
            "deferred_revenue": {
                "opening": 30.25,
                "billings": 115.0,
                "revenue_recognized": 110.25,
                "other_adjustments": 0.0,
                "closing": 35.0,
            },
            "accounts_receivable": {
                "opening": 20.0,
                "credit_billings": 115.0,
                "cash_collections": 113.0,
                "writeoffs": 0.0,
                "other_adjustments": 0.0,
                "closing": 22.0,
            },
            "accounts_payable": {
                "opening": 15.0,
                "purchases_or_accruals": 46.0,
                "cash_payments": 45.0,
                "other_adjustments": 0.0,
                "closing": 16.0,
            },
            "capitalized_development": {
                "opening": 9.0,
                "capitalized_spend": 3.0,
                "amortization": 2.0,
                "impairment": 0.0,
                "disposals": 0.0,
                "closing": 10.0,
            },
            "diluted_shares": {
                "opening": 101.0,
                "sbc_and_option_issuance": 2.0,
                "buybacks": 1.0,
                "other": 0.0,
                "closing": 102.0,
            },
        }
    )
    snapshot["recurring_model"] = {
        "applicable": True,
        "cohort_periods": [
            {
                "cohort_id": "enterprise-2026",
                "customer_group": "enterprise",
                "contract_type": "subscription-plus-usage",
                "period": "FY2027",
                "beginning_arr": 100.0,
                "churned_arr": 10.0,
                "retained_arr": 90.0,
                "price_expansion_arr": 3.0,
                "seat_expansion_arr": 4.0,
                "usage_or_cross_sell_expansion_arr": 5.0,
                "new_logo_arr": 8.0,
                "ending_arr": 110.0,
                "reported_nrr_cross_check": 1.02,
                "calculated_nrr": 1.02,
                "average_arr": 105.0,
                "recognition_factor": 0.95,
                "subscription_revenue": 99.75,
            },
            {
                "cohort_id": "enterprise-2026",
                "customer_group": "enterprise",
                "contract_type": "subscription-plus-usage",
                "period": "FY2028",
                "beginning_arr": 110.0,
                "churned_arr": 11.0,
                "retained_arr": 99.0,
                "price_expansion_arr": 3.3,
                "seat_expansion_arr": 4.4,
                "usage_or_cross_sell_expansion_arr": 5.5,
                "new_logo_arr": 8.8,
                "ending_arr": 121.0,
                "reported_nrr_cross_check": 1.02,
                "calculated_nrr": 1.02,
                "average_arr": 115.5,
                "recognition_factor": 110.25 / 115.5,
                "subscription_revenue": 110.25,
            },
        ],
        "cost_periods": [
            {
                "period": "FY2027",
                "usage_units": 1000.0,
                "inference_unit_cost": 0.02,
                "inference_cost": 20.0,
                "hosting_capacity_units": 100.0,
                "hosting_unit_cost": 0.10,
                "hosting_cost": 10.0,
                "support_load_units": 50.0,
                "support_unit_cost": 0.20,
                "support_cost": 10.0,
                "other_subscription_cogs": 5.0,
                "subscription_cogs": 45.0,
                "service_delivery_units": 20.0,
                "service_unit_cost": 1.5,
                "service_cogs": 30.0,
            },
            {
                "period": "FY2028",
                "usage_units": 1100.0,
                "inference_unit_cost": 0.019,
                "inference_cost": 20.9,
                "hosting_capacity_units": 105.0,
                "hosting_unit_cost": 0.095,
                "hosting_cost": 9.975,
                "support_load_units": 55.0,
                "support_unit_cost": 0.19,
                "support_cost": 10.45,
                "other_subscription_cogs": 4.675,
                "subscription_cogs": 46.0,
                "service_delivery_units": 22.0,
                "service_unit_cost": 1.5,
                "service_cogs": 33.0,
            },
        ],
    }
    return snapshot
