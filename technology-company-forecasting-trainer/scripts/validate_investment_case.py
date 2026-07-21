#!/usr/bin/env python3
"""Validate integrated statements, value creation and valuation identities."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from equation_contract import strict_finite_number


def _number(value: object) -> float | None:
    return strict_finite_number(value)


def _close(left: object, right: object, tolerance: float = 1e-6) -> bool:
    a, b = _number(left), _number(right)
    if a is None or b is None:
        return False
    return abs(a - b) <= max(tolerance, tolerance * max(abs(a), abs(b), 1.0))


def _error(errors: list[dict[str, str]], code: str, detail: str) -> None:
    errors.append({"code": code, "detail": detail})


def _required_number(record: dict[str, Any], key: str) -> float | None:
    return _number(record.get(key)) if isinstance(record, dict) else None


def validate(snapshot: dict[str, Any], strict: bool = False) -> dict[str, Any]:
    errors: list[dict[str, str]] = []
    warnings: list[dict[str, str]] = []

    for block in ("investment_case", "integrated_model", "value_creation", "valuation", "market_implied_expectations"):
        if not isinstance(snapshot.get(block), dict):
            _error(errors, f"missing_{block}", f"snapshot.{block} is required")

    investment_case = snapshot.get("investment_case") or {}
    for field in ("decision_question", "variant_view"):
        if not str(investment_case.get(field) or "").strip():
            _error(errors, "investment_case", f"investment_case.{field} must be explicit")
    if not investment_case.get("falsification_ids"):
        _error(errors, "investment_case", "investment_case.falsification_ids is required")

    model = snapshot.get("integrated_model") or {}
    periods = model.get("periods") if isinstance(model, dict) else None
    if not isinstance(periods, list) or not periods:
        _error(errors, "integrated_model", "integrated_model.periods must be populated")
        periods = []
    integrated_by_period: dict[str, dict[str, Any]] = {}
    for index, period in enumerate(periods):
        label = str(period.get("period") or f"period[{index}]") if isinstance(period, dict) else f"period[{index}]"
        if not isinstance(period, dict):
            _error(errors, "integrated_model", f"{label} must be an object")
            continue
        if not str(period.get("period") or "").strip():
            _error(errors, "integrated_model", f"period[{index}] must name its forecast period")
        elif label in integrated_by_period:
            _error(errors, "forecast_period_coverage", f"duplicate integrated-statement period {label}")
        else:
            integrated_by_period[label] = period
        income = period.get("income_statement") or {}
        balance = period.get("balance_sheet") or {}
        cash_flow = period.get("cash_flow_statement") or {}
        rolls = period.get("roll_forwards") or {}

        assets = _required_number(balance, "assets")
        liabilities = _required_number(balance, "liabilities")
        equity = _required_number(balance, "equity")
        if assets is None or liabilities is None or equity is None or not _close(assets, liabilities + equity):
            _error(errors, "balance_sheet", f"{label}: assets must equal liabilities plus equity")

        revenue = _required_number(income, "revenue")
        operating_costs = _required_number(income, "operating_costs_and_expenses")
        op = _required_number(income, "operating_profit")
        if None in (revenue, operating_costs, op) or not _close(op, revenue - operating_costs):
            _error(
                errors,
                "operating_profit_identity",
                f"{label}: operating profit must equal revenue less operating costs and expenses",
            )

        nonoperating = _required_number(income, "nonoperating_income_expense_net")
        pretax = _required_number(income, "pretax_profit")
        if None in (op, nonoperating, pretax) or not _close(pretax, op + nonoperating):
            _error(
                errors,
                "pretax_profit_identity",
                f"{label}: pretax profit must equal operating profit plus signed net non-operating income/expense",
            )

        tax_expense = _required_number(income, "tax_expense")
        consolidated_net_income = _required_number(income, "net_income")
        if None in (pretax, tax_expense, consolidated_net_income) or not _close(
            consolidated_net_income, pretax - tax_expense
        ):
            _error(
                errors,
                "net_income_identity",
                f"{label}: consolidated net income must equal pretax profit less signed tax expense",
            )

        nci_net_income = _required_number(
            income, "net_income_attributable_to_noncontrolling_interests"
        )
        attributable_net_income = _required_number(income, "net_income_attributable")
        if None in (consolidated_net_income, nci_net_income, attributable_net_income) or not _close(
            attributable_net_income, consolidated_net_income - nci_net_income
        ):
            _error(
                errors,
                "attributable_net_income_identity",
                f"{label}: GAAP attributable net income must equal consolidated net income less "
                "net income attributable to non-controlling interests; use explicit zero when none",
            )

        tax = _required_number(income, "tax")
        nopat = _required_number(income, "nopat")
        if op is None or tax is None or nopat is None or not _close(nopat, op - tax):
            _error(errors, "nopat_identity", f"{label}: NOPAT must equal operating profit less operating tax")

        income_net = _required_number(income, "net_income")
        cash_net = _required_number(cash_flow, "net_income")
        if income_net is None or cash_net is None or not _close(income_net, cash_net):
            _error(errors, "statement_link", f"{label}: cash-flow net income must link to the income statement")
        cfo = _required_number(cash_flow, "cash_from_operations")
        capex = _required_number(cash_flow, "capex")
        fcf = _required_number(cash_flow, "free_cash_flow")
        if cfo is None or capex is None or fcf is None or not _close(fcf, cfo - capex):
            _error(errors, "free_cash_flow", f"{label}: FCF must equal CFO less capex")

        cash = rolls.get("cash") or {}
        opening, change, closing = (_required_number(cash, key) for key in ("opening", "net_change", "closing"))
        balance_cash = _required_number(balance, "cash")
        statement_change = _required_number(cash_flow, "net_change_in_cash")
        if None in (opening, change, closing, balance_cash, statement_change) or not (
            _close(closing, opening + change) and _close(closing, balance_cash) and _close(change, statement_change)
        ):
            _error(errors, "cash_roll_forward", f"{label}: opening cash + cash-flow change must equal balance-sheet cash")

        ppe = rolls.get("ppe") or {}
        ppe_values = {key: _required_number(ppe, key) for key in ("opening", "capex", "depreciation", "disposals", "closing")}
        if any(value is None for value in ppe_values.values()) or not _close(
            ppe_values["closing"], ppe_values["opening"] + ppe_values["capex"] - ppe_values["depreciation"] - ppe_values["disposals"]
        ):
            _error(errors, "ppe_roll_forward", f"{label}: PPE roll-forward does not close")

        debt = rolls.get("debt") or {}
        debt_values = {key: _required_number(debt, key) for key in ("opening", "borrowings", "repayments", "closing")}
        if any(value is None for value in debt_values.values()) or not _close(
            debt_values["closing"], debt_values["opening"] + debt_values["borrowings"] - debt_values["repayments"]
        ):
            _error(errors, "debt_roll_forward", f"{label}: debt roll-forward does not close")

        working_capital = rolls.get("working_capital") or {}
        wc_values = {key: _required_number(working_capital, key) for key in ("opening", "change", "closing")}
        if any(value is None for value in wc_values.values()) or not _close(
            wc_values["closing"], wc_values["opening"] + wc_values["change"]
        ):
            _error(errors, "working_capital_roll_forward", f"{label}: working-capital roll-forward does not close")

    # The compact forecast outputs, integrated statements and downstream
    # earnings-power bridge all use these exact period labels.  Do not let a
    # complete FY+1 statement shell hide a missing FY+2/FY+3 profit chain.
    raw_outputs = snapshot.get("outputs")
    output_by_period: dict[str, dict[str, Any]] = {}
    if not isinstance(raw_outputs, dict):
        _error(errors, "forecast_period_coverage", "snapshot.outputs must contain forecast periods")
        raw_outputs = {}
    for horizon, output in raw_outputs.items():
        if not isinstance(output, dict):
            continue
        period_name = str(output.get("period") or "").strip()
        if not period_name:
            continue
        if period_name in output_by_period:
            _error(
                errors,
                "forecast_period_coverage",
                f"duplicate snapshot output period {period_name} ({horizon})",
            )
        else:
            output_by_period[period_name] = output

    output_periods = set(output_by_period)
    integrated_periods = set(integrated_by_period)
    missing_statements = sorted(output_periods - integrated_periods)
    extra_statements = sorted(integrated_periods - output_periods)
    if missing_statements:
        _error(
            errors,
            "forecast_period_coverage",
            "forecast output periods missing integrated statements: " + ", ".join(missing_statements),
        )
    if strict and extra_statements:
        _error(
            errors,
            "forecast_period_coverage",
            "integrated statement periods missing canonical forecast outputs: " + ", ".join(extra_statements),
        )

    statement_to_output = {
        "revenue": "revenue_point",
        "operating_profit": "operating_profit_point",
        "pretax_profit": "pretax_profit_point",
        "tax_expense": "tax_expense_point",
        "net_income_attributable_to_noncontrolling_interests":
            "noncontrolling_interest_net_income_point",
        "net_income_attributable": "net_income_point",
    }
    for period_name in sorted(output_periods & integrated_periods):
        income = integrated_by_period[period_name].get("income_statement") or {}
        output = output_by_period[period_name]
        for statement_field, output_field in statement_to_output.items():
            if not _close(income.get(statement_field), output.get(output_field)):
                _error(
                    errors,
                    "snapshot_statement_link",
                    f"{period_name}: integrated {statement_field} must equal snapshot {output_field}",
                )
        if not _close(income.get("net_income_attributable"), output.get("profit_point")):
            _error(
                errors,
                "snapshot_statement_link",
                f"{period_name}: integrated net_income_attributable must equal snapshot profit_point",
            )

    value_creation = snapshot.get("value_creation") or {}
    wacc = _required_number(value_creation, "wacc")
    vc_periods = value_creation.get("periods") if isinstance(value_creation, dict) else None
    if wacc is None:
        _error(errors, "wacc", "value_creation.wacc is required")
    if not isinstance(vc_periods, list) or not vc_periods:
        _error(errors, "value_creation", "value_creation.periods must be populated")
        vc_periods = []
    previous_ending_capital: float | None = None
    for index, row in enumerate(vc_periods):
        label = str(row.get("period") or f"period[{index}]") if isinstance(row, dict) else f"period[{index}]"
        if not isinstance(row, dict):
            _error(errors, "value_creation", f"{label} must be an object")
            continue
        reported_nopat = _required_number(row, "reported_nopat")
        normalizations = _required_number(row, "after_tax_normalization_adjustments")
        normalized_nopat = _required_number(row, "normalized_nopat")
        if None in (reported_nopat, normalizations, normalized_nopat) or not _close(
            normalized_nopat, reported_nopat + normalizations
        ):
            _error(
                errors,
                "normalized_nopat_identity",
                f"{label}: normalized NOPAT must equal reported NOPAT plus after-tax normalization adjustments",
            )

        beginning_capital = _required_number(row, "beginning_invested_capital")
        ending_capital = _required_number(row, "ending_invested_capital")
        average_capital = _required_number(row, "average_invested_capital")
        if None in (beginning_capital, ending_capital, average_capital) or not _close(
            average_capital, (beginning_capital + ending_capital) / 2
        ):
            _error(
                errors,
                "average_invested_capital_identity",
                f"{label}: average invested capital must equal (beginning + ending invested capital) / 2",
            )
        average_roic = _required_number(row, "average_roic")
        if None in (normalized_nopat, average_capital, average_roic) or not average_capital or not _close(
            average_roic, normalized_nopat / average_capital
        ):
            _error(errors, "average_roic_identity", f"{label}: average ROIC must equal normalized NOPAT / average invested capital")

        reinvestment = _required_number(row, "reinvestment")
        bridge_adjustment = _required_number(row, "invested_capital_bridge_adjustment")
        if None in (beginning_capital, ending_capital, reinvestment, bridge_adjustment) or not _close(
            ending_capital, beginning_capital + reinvestment + bridge_adjustment
        ):
            _error(
                errors,
                "invested_capital_roll_forward",
                f"{label}: ending invested capital must equal beginning capital + reinvestment + bridge adjustment",
            )
        if previous_ending_capital is not None and (
            beginning_capital is None or not _close(beginning_capital, previous_ending_capital)
        ):
            _error(
                errors,
                "invested_capital_continuity",
                f"{label}: beginning invested capital must equal the prior period ending invested capital",
            )
        previous_ending_capital = ending_capital

        reinvestment_rate = _required_number(row, "reinvestment_rate")
        if None in (reinvestment, reinvestment_rate, normalized_nopat) or not normalized_nopat or not _close(
            reinvestment_rate, reinvestment / normalized_nopat
        ):
            _error(errors, "reinvestment_rate_identity", f"{label}: reinvestment rate must equal reinvestment / normalized NOPAT")

        prior_normalized_nopat = _required_number(row, "prior_normalized_nopat")
        incremental_capital = _required_number(row, "incremental_invested_capital")
        incremental_nopat = _required_number(row, "incremental_nopat")
        if None in (normalized_nopat, prior_normalized_nopat, incremental_nopat) or not _close(
            incremental_nopat, normalized_nopat - prior_normalized_nopat
        ):
            _error(
                errors,
                "incremental_nopat_identity",
                f"{label}: incremental NOPAT must equal normalized NOPAT less prior normalized NOPAT",
            )
        incremental_roic = _required_number(row, "incremental_roic")
        if None in (incremental_capital, incremental_nopat, incremental_roic) or not incremental_capital or not _close(
            incremental_roic, incremental_nopat / incremental_capital
        ):
            _error(errors, "incremental_roic_identity", f"{label}: incremental ROIC must equal incremental NOPAT / capital")
        growth = _required_number(row, "fundamental_growth")
        if None in (growth, reinvestment_rate, incremental_roic) or not _close(growth, reinvestment_rate * incremental_roic):
            _error(errors, "fundamental_growth_identity", f"{label}: growth must equal reinvestment rate x incremental ROIC")
        lag = _required_number(row, "incremental_return_lag_periods")
        if lag is None or lag < 0:
            _error(errors, "incremental_return_lag", f"{label}: incremental_return_lag_periods must be a non-negative number")

    fade = value_creation.get("fade") if isinstance(value_creation, dict) else None
    if not isinstance(fade, dict) or _required_number(fade, "terminal_roic") is None or _required_number(fade, "years_to_fade") is None or not str(fade.get("competitive_response") or "").strip():
        _error(errors, "fade", "value creation must state terminal ROIC, fade horizon and competitive response")
    else:
        fade_schedule = fade.get("schedule")
        fade_problems: list[str] = []
        if not isinstance(fade_schedule, list) or not fade_schedule:
            fade_problems.append("schedule must be populated")
            fade_schedule = []
        for index, row in enumerate(fade_schedule):
            label = str(row.get("period") or f"fade[{index}]") if isinstance(row, dict) else f"fade[{index}]"
            if not isinstance(row, dict):
                fade_problems.append(f"{label} must be an object")
                continue
            for field in ("average_roic", "incremental_roic", "reinvestment_rate", "fundamental_growth"):
                if _required_number(row, field) is None:
                    fade_problems.append(f"{label}: missing numeric {field}")
            if not row.get("competitive_or_obsolescence_driver_node_ids"):
                fade_problems.append(f"{label}: missing competition/obsolescence driver node")
            if not str(row.get("erosion_or_renewal_event") or "").strip():
                fade_problems.append(f"{label}: missing erosion or renewal event")
            row_growth = _required_number(row, "fundamental_growth")
            row_reinvestment = _required_number(row, "reinvestment_rate")
            row_incremental_roic = _required_number(row, "incremental_roic")
            if None not in (row_growth, row_reinvestment, row_incremental_roic) and not _close(
                row_growth, row_reinvestment * row_incremental_roic
            ):
                fade_problems.append(f"{label}: growth must equal reinvestment rate x incremental ROIC")
        if fade_schedule and not _close(
            fade_schedule[-1].get("average_roic"), fade.get("terminal_roic")
        ):
            fade_problems.append("last schedule average_roic must equal terminal_roic")
        if fade_problems:
            _error(errors, "fade_schedule", "; ".join(fade_problems[:8]))

    primitive_names = {
        str(item).strip().lower().replace("_", "-")
        for item in (snapshot.get("analysis_primitives") or [])
    }
    recurring_required = bool(primitive_names & {"recurring-contract", "platform-usage"})
    recurring = snapshot.get("recurring_model")
    if recurring_required and not isinstance(recurring, dict):
        _error(errors, "missing_recurring_model", "recurring-contract/platform-usage requires snapshot.recurring_model")
    if recurring_required and isinstance(recurring, dict) and recurring.get("applicable") is not True:
        _error(errors, "recurring_applicability", "selected recurring/platform primitive requires recurring_model.applicable=true")
    if isinstance(recurring, dict) and (recurring_required or recurring.get("applicable") is True):
        cohort_rows = recurring.get("cohort_periods")
        cost_rows = recurring.get("cost_periods")
        if not isinstance(cohort_rows, list) or not cohort_rows:
            _error(errors, "recurring_arr_roll", "recurring_model.cohort_periods must be populated")
            cohort_rows = []
        if not isinstance(cost_rows, list) or not cost_rows:
            _error(errors, "usage_cost_identity", "recurring_model.cost_periods must be populated")
            cost_rows = []

        cohort_periods: set[str] = set()
        revenue_by_period: dict[str, float] = {}
        for index, row in enumerate(cohort_rows):
            label = f"cohort[{index}]"
            if not isinstance(row, dict):
                _error(errors, "recurring_arr_roll", f"{label} must be an object")
                continue
            period = str(row.get("period") or "").strip()
            cohort_id = str(row.get("cohort_id") or "").strip()
            label = f"{period or '?'}:{cohort_id or '?'}"
            if not period or not cohort_id or not str(row.get("customer_group") or "").strip() or not str(row.get("contract_type") or "").strip():
                _error(errors, "recurring_arr_roll", f"{label}: period, cohort_id, customer_group and contract_type are required")
            cohort_periods.add(period)
            values = {key: _required_number(row, key) for key in (
                "beginning_arr", "churned_arr", "retained_arr", "price_expansion_arr",
                "seat_expansion_arr", "usage_or_cross_sell_expansion_arr", "new_logo_arr",
                "ending_arr", "reported_nrr_cross_check", "calculated_nrr", "average_arr",
                "recognition_factor", "subscription_revenue",
            )}
            if any(value is None for value in values.values()):
                _error(errors, "recurring_arr_roll", f"{label}: every ARR/cohort field must be numeric")
                continue
            if not _close(values["retained_arr"], values["beginning_arr"] - values["churned_arr"]):
                _error(errors, "recurring_arr_roll", f"{label}: retained ARR must equal beginning ARR less churn")
            expected_ending = (
                values["retained_arr"] + values["price_expansion_arr"] + values["seat_expansion_arr"]
                + values["usage_or_cross_sell_expansion_arr"] + values["new_logo_arr"]
            )
            if not _close(values["ending_arr"], expected_ending):
                _error(errors, "recurring_arr_roll", f"{label}: ending ARR stock-flow does not close")
            beginning_arr = values["beginning_arr"]
            expected_nrr = None if not beginning_arr else (
                values["retained_arr"] + values["price_expansion_arr"] + values["seat_expansion_arr"]
                + values["usage_or_cross_sell_expansion_arr"]
            ) / beginning_arr
            if expected_nrr is None or not _close(values["calculated_nrr"], expected_nrr):
                _error(errors, "recurring_nrr_identity", f"{label}: NRR must be calculated from retained and expansion ARR")
            if not _close(values["average_arr"], (values["beginning_arr"] + values["ending_arr"]) / 2):
                _error(errors, "recurring_arr_roll", f"{label}: average ARR must equal opening/closing average")
            if not _close(values["subscription_revenue"], values["average_arr"] * values["recognition_factor"]):
                _error(errors, "recurring_revenue_identity", f"{label}: subscription revenue must equal average ARR x recognition factor")
            if any(abs(_number(row.get(field)) or 0.0) > 1e-12 for field in (
                "nrr_revenue_addition", "reported_nrr_revenue", "nrr_incremental_revenue"
            )):
                _error(errors, "recurring_double_count", f"{label}: NRR is a cross-check/decomposition and cannot be added again as revenue")
            revenue_by_period[period] = revenue_by_period.get(period, 0.0) + values["subscription_revenue"]

        cost_periods: set[str] = set()
        cogs_by_period: dict[str, float] = {}
        for index, row in enumerate(cost_rows):
            label = str(row.get("period") or f"cost[{index}]") if isinstance(row, dict) else f"cost[{index}]"
            if not isinstance(row, dict):
                _error(errors, "usage_cost_identity", f"{label} must be an object")
                continue
            period = str(row.get("period") or "").strip()
            cost_periods.add(period)
            values = {key: _required_number(row, key) for key in (
                "usage_units", "inference_unit_cost", "inference_cost", "hosting_capacity_units",
                "hosting_unit_cost", "hosting_cost", "support_load_units", "support_unit_cost",
                "support_cost", "other_subscription_cogs", "subscription_cogs",
                "service_delivery_units", "service_unit_cost", "service_cogs",
            )}
            if any(value is None for value in values.values()):
                _error(errors, "usage_cost_identity", f"{label}: every recurring cost field must be numeric")
                continue
            if not _close(values["inference_cost"], values["usage_units"] * values["inference_unit_cost"]):
                _error(errors, "usage_cost_identity", f"{label}: inference cost must equal usage units x unit cost")
            if not _close(values["hosting_cost"], values["hosting_capacity_units"] * values["hosting_unit_cost"]):
                _error(errors, "hosting_cost_identity", f"{label}: hosting cost must equal capacity units x hosting unit cost")
            if not _close(values["support_cost"], values["support_load_units"] * values["support_unit_cost"]):
                _error(errors, "support_cost_identity", f"{label}: support cost must equal support load x unit support cost")
            if not _close(
                values["subscription_cogs"],
                values["inference_cost"] + values["hosting_cost"] + values["support_cost"] + values["other_subscription_cogs"],
            ):
                _error(errors, "subscription_cogs_identity", f"{label}: subscription COGS components do not sum")
            if not _close(values["service_cogs"], values["service_delivery_units"] * values["service_unit_cost"]):
                _error(errors, "service_cost_identity", f"{label}: service COGS must equal delivery units x unit cost")
            cogs_by_period[period] = cogs_by_period.get(period, 0.0) + values["subscription_cogs"]

        integrated_period_names = {str(row.get("period") or "").strip() for row in periods if isinstance(row, dict)}
        if recurring_required and (cohort_periods != integrated_period_names or cost_periods != integrated_period_names):
            _error(errors, "recurring_period_coverage", "cohort and cost schedules must cover every integrated-model period")

        for index, period_row in enumerate(periods):
            if not isinstance(period_row, dict):
                continue
            label = str(period_row.get("period") or f"period[{index}]")
            income = period_row.get("income_statement") or {}
            balance = period_row.get("balance_sheet") or {}
            cash_flow = period_row.get("cash_flow_statement") or {}
            rolls = period_row.get("roll_forwards") or {}

            if label in revenue_by_period and not _close(income.get("subscription_revenue"), revenue_by_period[label]):
                _error(errors, "recurring_revenue_statement_link", f"{label}: cohort revenue must link to the income statement")
            if label in cogs_by_period and not _close(income.get("subscription_cogs"), cogs_by_period[label]):
                _error(errors, "recurring_cost_statement_link", f"{label}: cost schedule must link to subscription COGS")

            deferred = rolls.get("deferred_revenue") or {}
            deferred_values = {key: _required_number(deferred, key) for key in (
                "opening", "billings", "revenue_recognized", "other_adjustments", "closing"
            )}
            if any(value is None for value in deferred_values.values()) or not _close(
                deferred_values["closing"], deferred_values["opening"] + deferred_values["billings"]
                - deferred_values["revenue_recognized"] + deferred_values["other_adjustments"]
            ) or not _close(deferred_values["closing"], balance.get("deferred_revenue")) or (
                label in revenue_by_period and not _close(deferred_values["revenue_recognized"], revenue_by_period[label])
            ):
                _error(errors, "deferred_revenue_roll", f"{label}: deferred revenue roll-forward or statement link does not close")

            receivables = rolls.get("accounts_receivable") or {}
            ar_values = {key: _required_number(receivables, key) for key in (
                "opening", "credit_billings", "cash_collections", "writeoffs", "other_adjustments", "closing"
            )}
            if any(value is None for value in ar_values.values()) or not _close(
                ar_values["closing"], ar_values["opening"] + ar_values["credit_billings"]
                - ar_values["cash_collections"] - ar_values["writeoffs"] + ar_values["other_adjustments"]
            ) or not _close(ar_values["closing"], balance.get("accounts_receivable")):
                _error(errors, "receivables_roll", f"{label}: receivables roll-forward or balance-sheet link does not close")

            payables = rolls.get("accounts_payable") or {}
            ap_values = {key: _required_number(payables, key) for key in (
                "opening", "purchases_or_accruals", "cash_payments", "other_adjustments", "closing"
            )}
            if any(value is None for value in ap_values.values()) or not _close(
                ap_values["closing"], ap_values["opening"] + ap_values["purchases_or_accruals"]
                - ap_values["cash_payments"] + ap_values["other_adjustments"]
            ) or not _close(ap_values["closing"], balance.get("accounts_payable")):
                _error(errors, "payables_roll", f"{label}: payables roll-forward or balance-sheet link does not close")

            development = rolls.get("capitalized_development") or {}
            dev_values = {key: _required_number(development, key) for key in (
                "opening", "capitalized_spend", "amortization", "impairment", "disposals", "closing"
            )}
            if any(value is None for value in dev_values.values()) or not _close(
                dev_values["closing"], dev_values["opening"] + dev_values["capitalized_spend"]
                - dev_values["amortization"] - dev_values["impairment"] - dev_values["disposals"]
            ) or not _close(dev_values["closing"], balance.get("capitalized_development")) or not _close(
                dev_values["capitalized_spend"], cash_flow.get("capitalized_development_cash")
            ) or not _close(dev_values["amortization"], income.get("capitalized_development_amortization")):
                _error(errors, "capitalized_development_roll", f"{label}: capitalized-development roll-forward or statement links do not close")

            shares = rolls.get("diluted_shares") or {}
            share_values = {key: _required_number(shares, key) for key in (
                "opening", "sbc_and_option_issuance", "buybacks", "other", "closing"
            )}
            if any(value is None for value in share_values.values()) or not _close(
                share_values["closing"], share_values["opening"] + share_values["sbc_and_option_issuance"]
                - share_values["buybacks"] + share_values["other"]
            ) or not _close(share_values["closing"], balance.get("diluted_shares")):
                _error(errors, "diluted_shares_roll", f"{label}: diluted-share roll-forward or balance-sheet link does not close")

            if not _close(
                cash_flow.get("capex"),
                (_required_number(cash_flow, "fixed_capex") or float("nan"))
                + (_required_number(cash_flow, "capitalized_development_cash") or float("nan")),
            ):
                _error(errors, "recurring_capex_link", f"{label}: capex must include fixed capex plus capitalized-development cash")

    valuation = snapshot.get("valuation") or {}
    dcf = valuation.get("dcf") if isinstance(valuation, dict) else None
    if not isinstance(dcf, dict):
        _error(errors, "missing_dcf", "valuation.dcf is required")
        dcf = {}
    explicit = _required_number(dcf, "pv_explicit_free_cash_flow")
    terminal_value = _required_number(dcf, "pv_terminal_value")
    enterprise_value = _required_number(dcf, "enterprise_value")
    if None in (explicit, terminal_value, enterprise_value) or not _close(enterprise_value, explicit + terminal_value):
        _error(errors, "dcf_identity", "DCF enterprise value must equal explicit-period PV plus terminal-value PV")

    residual = valuation.get("residual_income") if isinstance(valuation, dict) else None
    if not isinstance(residual, dict):
        _error(errors, "missing_residual_income", "valuation.residual_income is required as a cross-check")
        residual = {}
    book = _required_number(residual, "current_book_value")
    pv_ri = _required_number(residual, "pv_residual_income")
    ri_equity = _required_number(residual, "equity_value")
    if residual and (None in (book, pv_ri, ri_equity) or not _close(ri_equity, book + pv_ri)):
        _error(errors, "residual_income_identity", "residual-income equity value must equal book value plus PV of residual income")

    reconciliation = valuation.get("reconciliation") or {}
    dcf_equity = _required_number(reconciliation, "dcf_equity_value")
    reconciliation_ri = _required_number(reconciliation, "residual_income_equity_value")
    stated_difference = _required_number(reconciliation, "difference_pct")
    expected_difference = None
    if dcf_equity is not None and reconciliation_ri is not None and dcf_equity:
        expected_difference = abs(reconciliation_ri - dcf_equity) / abs(dcf_equity)
    if expected_difference is None or stated_difference is None or not _close(stated_difference, expected_difference):
        _error(errors, "valuation_reconciliation", "DCF/RI difference_pct must be recalculable from the two equity values")
    elif expected_difference > 0.05 and not str(reconciliation.get("explanation") or "").strip():
        _error(errors, "valuation_reconciliation", "DCF/RI differences above 5% require an explicit reconciliation")

    bridge = valuation.get("enterprise_to_equity") or {}
    bridge_values = {key: _required_number(bridge, key) for key in (
        "enterprise_value", "cash", "non_operating_assets", "debt", "noncontrolling_interest", "other_adjustments", "equity_value"
    )}
    if any(value is None for value in bridge_values.values()) or not _close(
        bridge_values["equity_value"],
        bridge_values["enterprise_value"] + bridge_values["cash"] + bridge_values["non_operating_assets"]
        - bridge_values["debt"] - bridge_values["noncontrolling_interest"] + bridge_values["other_adjustments"],
    ):
        _error(errors, "ev_to_equity_identity", "EV-to-equity bridge does not close")

    per_share = valuation.get("per_share") or {}
    per_share_equity = _required_number(per_share, "equity_value")
    diluted_shares = _required_number(per_share, "diluted_shares")
    value_per_share = _required_number(per_share, "value_per_share")
    if None in (per_share_equity, diluted_shares, value_per_share) or not diluted_shares or not _close(
        value_per_share, per_share_equity / diluted_shares
    ):
        _error(errors, "per_share_identity", "per-share value must equal equity value / diluted shares")

    # The dashboard summary is a projection of an executed valuation, never an
    # independent place to author a fair value.  Cross-file scenario identity
    # is checked by validate_delivery; this standalone validator still binds
    # any published reference value to valuation.per_share.value_per_share.
    summary = snapshot.get("valuation_summary")
    if summary is not None:
        if not isinstance(summary, dict):
            _error(errors, "valuation_summary", "valuation_summary must be an object")
        else:
            fair_values = summary.get("fair_value_by_scenario_id")
            if not isinstance(fair_values, dict):
                _error(
                    errors,
                    "valuation_summary",
                    "valuation_summary.fair_value_by_scenario_id must be an object",
                )
            elif fair_values:
                reference_id = summary.get("reference_scenario_id")
                if not isinstance(reference_id, str) or not reference_id.strip():
                    _error(
                        errors,
                        "valuation_summary",
                        "a published fair value requires reference_scenario_id",
                    )
                elif reference_id not in fair_values:
                    _error(
                        errors,
                        "valuation_summary",
                        "the published reference scenario must have a fair value",
                    )
                elif _number(fair_values.get(reference_id)) is None or not _close(
                    fair_values.get(reference_id), value_per_share
                ):
                    _error(
                        errors,
                        "valuation_summary",
                        "the reference fair value must equal valuation.per_share.value_per_share",
                    )
            elif summary.get("reference_scenario_id") is not None:
                _error(
                    errors,
                    "valuation_summary",
                    "reference_scenario_id must be null when no fair value is published",
                )

    terminal = valuation.get("terminal") or {}
    terminal_wacc = _required_number(terminal, "wacc")
    terminal_growth = _required_number(terminal, "growth_rate")
    terminal_roic = _required_number(terminal, "terminal_roic")
    implied_reinvestment = _required_number(terminal, "implied_reinvestment_rate")
    if None in (terminal_wacc, terminal_growth) or terminal_growth >= terminal_wacc:
        _error(errors, "terminal_growth", "terminal growth must be below the discount rate")
    if None in (terminal_growth, terminal_roic, implied_reinvestment) or not terminal_roic or not _close(
        implied_reinvestment, terminal_growth / terminal_roic
    ):
        _error(errors, "terminal_reinvestment_identity", "terminal reinvestment rate must equal growth / terminal ROIC")

    implied = snapshot.get("market_implied_expectations") or {}
    required_implied = ("price_as_of", "observed_price", "named_driver", "implied_driver_value", "model_driver_value", "unit", "falsification_trigger")
    if any(not str(implied.get(key) if implied.get(key) is not None else "").strip() for key in required_implied):
        _error(errors, "reverse_implied_driver", "market-implied expectations must solve a named operating driver with unit and falsification")

    return {
        "valid": not errors,
        "strict": strict,
        "errors": errors,
        "warnings": warnings,
        "metrics": {"integrated_periods": len(periods), "value_creation_periods": len(vc_periods)},
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate a v2 value-investing forecast snapshot.")
    parser.add_argument("--snapshot", required=True, type=Path)
    parser.add_argument("--strict", action="store_true")
    args = parser.parse_args()
    try:
        payload = json.loads(args.snapshot.read_text(encoding="utf-8"))
        if not isinstance(payload, dict):
            raise ValueError("root must be an object")
        result = validate(payload, strict=args.strict)
    except Exception as exc:
        result = {"valid": False, "strict": args.strict, "errors": [{"code": "invalid_json", "detail": str(exc)}], "warnings": []}
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["valid"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
