import importlib.util
import unittest
from pathlib import Path


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "validate_delivery.py"
TEMPLATE = (
    Path(__file__).resolve().parents[1]
    / "assets"
    / "templates"
    / "historical_segment_bridge_template.csv"
)
SPEC = importlib.util.spec_from_file_location("validate_delivery_historical_contract", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
SPEC.loader.exec_module(MODULE)


KEY_FIELDS = (
    "revenue",
    "cost",
    "gross_profit",
    "operating_profit",
    "gaap_net_income_attributable",
)


def _consolidated(period: str, revenue: float, *, period_type: str = "annual") -> dict[str, str]:
    cost = revenue * 0.6
    gross_profit = revenue - cost
    operating_profit = revenue * 0.2
    net_income = revenue * 0.12
    return {
        "period": period,
        "period_type": period_type,
        "row_type": "consolidated",
        "reported_segment": "Total",
        "normalized_segment": "Total",
        "actual_or_forecast": "actual",
        "revenue": str(revenue),
        "cost": str(cost),
        "gross_profit": str(gross_profit),
        "operating_profit": str(operating_profit),
        "gaap_net_income_attributable": str(net_income),
        "currency": "USD",
        "scope_basis": "continuing operations; consolidated attributable basis",
        "comparability_status": "comparable",
        "data_status": "reported",
        "latest_actual": "false",
        "perimeter_bridge": "none_no_change",
        "accounting_bridge": "none_no_change",
        "source_ids": "SRC-FILING",
        "partition_id": "reported-segments",
        "partition_dimension": "reported_operating_segment",
        "partition_exhaustive": "true",
        "partition_mutually_exclusive": "true",
        "check_to_consolidated": "0",
        "segment_reconciliation_status": "reconciled",
        "status": "accepted",
        "missing_disclosure_reason": "",
        "notes": "",
    }


def _segment(period: str, revenue: float, *, period_type: str = "annual") -> dict[str, str]:
    return {
        "period": period,
        "period_type": period_type,
        "row_type": "segment",
        "reported_segment": "Operating segment",
        "normalized_segment": "Operating segment",
        "actual_or_forecast": "actual",
        "revenue": str(revenue),
        "currency": "USD",
        "scope_basis": "continuing operations; reported segment basis",
        "comparability_status": "comparable",
        "data_status": "reported",
        "latest_actual": "false",
        "perimeter_bridge": "none_no_change",
        "accounting_bridge": "none_no_change",
        "source_ids": "SRC-FILING",
        "partition_id": "reported-segments",
        "partition_dimension": "reported_operating_segment",
        "status": "accepted",
        "missing_disclosure_reason": "",
        "notes": "segment cost and profit are not separately disclosed",
    }


def _valid_rows() -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for period, revenue in (("FY2023", 80.0), ("FY2024", 90.0), ("FY2025", 100.0)):
        rows.extend((_consolidated(period, revenue), _segment(period, revenue)))
    interim = _consolidated("H1-2026", 55.0, period_type="interim")
    interim["latest_actual"] = "true"
    rows.extend((interim, _segment("H1-2026", 55.0, period_type="interim")))

    forecast = _consolidated("FY2026E", 115.0, period_type="first_forecast")
    forecast.update(
        {
            "actual_or_forecast": "forecast",
            "data_status": "derived",
            "latest_actual": "false",
            "bridge_from_period": "H1-2026",
            "revenue_bridge_delta": "60",
            "cost_bridge_delta": "36",
            "gross_profit_bridge_delta": "24",
            "operating_profit_bridge_delta": "12",
            "gaap_net_income_attributable_bridge_delta": "7.2",
            "forecast_bridge": "H2 volume, price and cost nodes bridge the latest interim to FY2026E",
            "driver_node_ids": "units;asp;unit_cost",
            "segment_reconciliation_status": "not_applicable",
        }
    )
    rows.append(forecast)
    return rows


def _validate(rows: list[dict[str, str]], readiness: str = "research-grade") -> list[str]:
    validator = getattr(MODULE, "validate_historical_segment_bridge_rows", None)
    if validator is None:
        return []
    return validator(
        rows,
        strict=True,
        readiness_target=readiness,
        graph_node_ids={"units", "asp", "unit_cost"},
    )


class HistoricalBaseContractTest(unittest.TestCase):
    def test_template_declares_generic_partition_member_id(self):
        header = TEMPLATE.read_text(encoding="utf-8-sig").splitlines()[0].split(",")

        self.assertIn("partition_member_id", header)

    def test_three_empty_rows_are_not_a_historical_base(self):
        rows = [
            {
                "period": period,
                "reported_segment": "Total",
                "normalized_segment": "Total",
                "actual_or_forecast": "actual",
                "source_ids": "SRC-FILING",
                "status": "accepted",
            }
            for period in ("FY2023", "FY2024", "FY2025")
        ]

        problems = _validate(rows)

        self.assertTrue(problems, "legacy three-row empty shell was incorrectly accepted")
        self.assertTrue(any("numeric" in problem or "period_type" in problem for problem in problems))

    def test_complete_comparable_history_interim_segments_and_forecast_bridge_pass(self):
        self.assertEqual(_validate(_valid_rows()), [])

    def test_latest_interim_can_be_typed_unavailable_only_with_readiness_cap(self):
        rows = _valid_rows()
        rows = [row for row in rows if row["period"] != "H1-2026"]
        unavailable = _consolidated("LATEST-INTERIM", 0.0, period_type="interim")
        for field in KEY_FIELDS:
            unavailable[field] = ""
        unavailable.update(
            {
                "data_status": "disclosure_limited",
                "comparability_status": "disclosure_limited",
                "segment_reconciliation_status": "disclosure_limited",
                "latest_actual": "false",
                "missing_disclosure_reason": "Issuer has not published an interim report after FY2025.",
            }
        )
        rows.append(unavailable)
        forecast = next(row for row in rows if row["period_type"] == "first_forecast")
        forecast["bridge_from_period"] = "FY2025"
        latest_annual = next(row for row in rows if row["period"] == "FY2025" and row["row_type"] == "consolidated")
        latest_annual["latest_actual"] = "true"
        forecast.update(
            {
                "revenue_bridge_delta": "15",
                "cost_bridge_delta": "9",
                "gross_profit_bridge_delta": "6",
                "operating_profit_bridge_delta": "3",
                "gaap_net_income_attributable_bridge_delta": "1.8",
            }
        )

        self.assertEqual(_validate(rows, readiness="screen-grade"), [])
        research_grade_problems = _validate(rows, readiness="research-grade")
        self.assertTrue(any("readiness" in problem for problem in research_grade_problems))

    def test_interim_not_yet_due_is_explicit_not_applicable_without_false_readiness_penalty(self):
        rows = _valid_rows()
        rows = [row for row in rows if row["period"] != "H1-2026"]
        no_interim_due = _consolidated("LATEST-INTERIM", 0.0, period_type="interim")
        for field in KEY_FIELDS:
            no_interim_due[field] = ""
        no_interim_due.update(
            {
                "data_status": "not_applicable",
                "comparability_status": "not_applicable",
                "segment_reconciliation_status": "not_applicable",
                "latest_actual": "false",
                "missing_disclosure_reason": "No interim period has ended since the latest annual filing.",
            }
        )
        rows.append(no_interim_due)
        forecast = next(row for row in rows if row["period_type"] == "first_forecast")
        forecast["bridge_from_period"] = "FY2025"
        latest_annual = next(row for row in rows if row["period"] == "FY2025" and row["row_type"] == "consolidated")
        latest_annual["latest_actual"] = "true"
        forecast.update(
            {
                "revenue_bridge_delta": "15",
                "cost_bridge_delta": "9",
                "gross_profit_bridge_delta": "6",
                "operating_profit_bridge_delta": "3",
                "gaap_net_income_attributable_bridge_delta": "1.8",
            }
        )

        self.assertEqual(_validate(rows, readiness="research-grade"), [])

    def test_segment_sum_must_reconcile_to_consolidated(self):
        rows = _valid_rows()
        next(row for row in rows if row["period"] == "FY2024" and row["row_type"] == "segment")["revenue"] = "40"

        problems = _validate(rows)

        self.assertTrue(any("segment revenue" in problem for problem in problems))

    def test_not_applicable_cannot_bypass_numeric_segment_reconciliation(self):
        rows = _valid_rows()
        consolidated = next(
            row for row in rows
            if row["period"] == "FY2024" and row["row_type"] == "consolidated"
        )
        consolidated.update(
            {
                "segment_reconciliation_status": "not_applicable",
                "missing_disclosure_reason": "Segment reconciliation marked not applicable.",
            }
        )
        next(
            row for row in rows
            if row["period"] == "FY2024" and row["row_type"] == "segment"
        )["revenue"] = "1"

        problems = _validate(rows)

        self.assertTrue(
            any(
                "not_applicable" in problem
                and "numeric segment/elimination" in problem
                for problem in problems
            ),
            problems,
        )

    def test_component_row_label_cannot_hide_it_from_not_applicable_guard(self):
        rows = _valid_rows()
        consolidated = next(
            row for row in rows
            if row["period"] == "FY2024" and row["row_type"] == "consolidated"
        )
        consolidated.update(
            {
                "segment_reconciliation_status": "not_applicable",
                "missing_disclosure_reason": "Segment reconciliation marked not applicable.",
            }
        )
        segment = next(
            row for row in rows
            if row["period"] == "FY2024" and row["row_type"] == "segment"
        )
        segment.update({"actual_or_forecast": "forecast", "revenue": "1"})

        problems = _validate(rows)

        self.assertTrue(
            any("not_applicable" in problem for problem in problems),
            problems,
        )

    def test_consolidated_data_status_cannot_hide_partition_rows(self):
        rows = _valid_rows()
        consolidated = next(
            row for row in rows
            if row["period"] == "FY2024" and row["row_type"] == "consolidated"
        )
        consolidated.update(
            {
                "data_status": "disclosure_limited",
                "segment_reconciliation_status": "not_applicable",
                "missing_disclosure_reason": "Some consolidated detail is disclosure limited.",
            }
        )
        next(
            row for row in rows
            if row["period"] == "FY2024" and row["row_type"] == "segment"
        )["revenue"] = "1"

        problems = _validate(rows, readiness="screen-grade")

        self.assertTrue(
            any("not_applicable" in problem for problem in problems),
            problems,
        )

    def test_partition_period_relabel_cannot_create_a_false_no_rows_exception(self):
        rows = _valid_rows()
        consolidated = next(
            row for row in rows
            if row["period"] == "FY2024" and row["row_type"] == "consolidated"
        )
        consolidated.update(
            {
                "segment_reconciliation_status": "not_applicable",
                "missing_disclosure_reason": "Segment reconciliation marked not applicable.",
            }
        )
        segment = next(
            row for row in rows
            if row["period"] == "FY2024" and row["row_type"] == "segment"
        )
        segment.update({"period": "FY2024-SEGMENTS", "revenue": "1"})

        problems = _validate(rows)

        self.assertTrue(
            any("no consolidated actual parent" in problem for problem in problems),
            problems,
        )

    def test_first_forecast_segment_requires_a_unique_consolidated_parent(self):
        rows = _valid_rows()
        orphan = _segment("FY2027E", 12, period_type="first_forecast")
        orphan.update(
            {
                "actual_or_forecast": "forecast",
                "data_status": "derived",
                "source_ids": "SRC-MODEL",
            }
        )
        rows.append(orphan)

        problems = _validate(rows)

        self.assertTrue(
            any("no consolidated actual parent" in problem for problem in problems),
            problems,
        )

    def test_substantive_rows_reject_unsupported_period_state_pairs(self):
        unsupported = (
            ("annual", "forecast"),
            ("interim", "forecast"),
            ("first_forecast", "actual"),
        )
        for row_type in ("segment", "elimination"):
            for period_type, state in unsupported:
                with self.subTest(
                    row_type=row_type,
                    period_type=period_type,
                    actual_or_forecast=state,
                ):
                    rows = _valid_rows()
                    period = f"UNSUPPORTED-{row_type}-{period_type}-{state}"
                    parent = _consolidated(period, 100, period_type=period_type)
                    parent["actual_or_forecast"] = state
                    member = _segment(period, 100, period_type=period_type)
                    member.update(
                        {
                            "row_type": row_type,
                            "reported_segment": (
                                "Unsupported segment"
                                if row_type == "segment"
                                else "Unsupported elimination"
                            ),
                            "normalized_segment": (
                                "Unsupported segment"
                                if row_type == "segment"
                                else "Unsupported elimination"
                            ),
                            "actual_or_forecast": state,
                        }
                    )
                    rows.extend((parent, member))

                    problems = _validate(rows)

                    for expected_row_type in ("consolidated", row_type):
                        self.assertTrue(
                            any(
                                f"{period}:{expected_row_type}: "
                                "period_type/actual_or_forecast combination" in problem
                                for problem in problems
                            ),
                            problems,
                        )

    def test_first_forecast_full_partition_remains_valid(self):
        rows = _valid_rows()
        forecast = next(
            row for row in rows
            if row["period"] == "FY2026E" and row["row_type"] == "consolidated"
        )
        forecast["segment_reconciliation_status"] = "reconciled"
        member = _segment("FY2026E", 115, period_type="first_forecast")
        member.update(
            {
                "actual_or_forecast": "forecast",
                "data_status": "derived",
                "source_ids": "SRC-MODEL",
            }
        )
        rows.append(member)

        self.assertEqual(_validate(rows), [])

    def test_segment_requires_an_explicit_member_identity(self):
        rows = _valid_rows()
        segment = next(
            row for row in rows
            if row["period"] == "FY2024" and row["row_type"] == "segment"
        )
        segment.update({"reported_segment": "", "normalized_segment": ""})

        problems = _validate(rows)

        self.assertTrue(
            any("explicit member identity" in problem for problem in problems),
            problems,
        )

    def test_elimination_requires_an_explicit_member_identity(self):
        rows = _valid_rows()
        elimination = _segment("FY2024", 0)
        elimination.update(
            {
                "row_type": "elimination",
                "reported_segment": "",
                "normalized_segment": "",
            }
        )
        rows.append(elimination)

        problems = _validate(rows)

        self.assertTrue(
            any("explicit member identity" in problem for problem in problems),
            problems,
        )

    def test_member_identity_rejects_placeholder_aliases(self):
        for row_type in ("segment", "elimination"):
            for placeholder in ("TBD", "PENDING", "REPLACE", "unknown", "none"):
                with self.subTest(row_type=row_type, placeholder=placeholder):
                    rows = _valid_rows()
                    member = _segment("FY2024", 0 if row_type == "elimination" else 90)
                    member.update(
                        {
                            "row_type": row_type,
                            "reported_segment": placeholder,
                            "normalized_segment": placeholder,
                        }
                    )
                    if row_type == "segment":
                        rows = [
                            row for row in rows
                            if not (
                                row["period"] == "FY2024"
                                and row["row_type"] == "segment"
                            )
                        ]
                    rows.append(member)

                    problems = _validate(rows)

                    self.assertTrue(
                        any("explicit member identity" in problem for problem in problems),
                        problems,
                    )

    def test_named_zero_elimination_with_a_unique_parent_remains_valid(self):
        rows = _valid_rows()
        elimination = _segment("FY2024", 0)
        elimination.update(
            {
                "row_type": "elimination",
                "reported_segment": "Intersegment eliminations",
                "normalized_segment": "Intersegment eliminations",
            }
        )
        rows.append(elimination)

        self.assertEqual(_validate(rows), [])

    def test_single_segment_status_recomputes_the_disclosed_member(self):
        rows = _valid_rows()
        consolidated = next(
            row for row in rows
            if row["period"] == "FY2024" and row["row_type"] == "consolidated"
        )
        consolidated["segment_reconciliation_status"] = "single_segment"
        next(
            row for row in rows
            if row["period"] == "FY2024" and row["row_type"] == "segment"
        )["revenue"] = "1"

        problems = _validate(rows)

        self.assertTrue(any("single-segment partition" in problem for problem in problems), problems)
        self.assertTrue(any("member sum" in problem for problem in problems), problems)

    def test_single_segment_cannot_hide_a_second_member_in_another_partition(self):
        rows = _valid_rows()
        consolidated = next(
            row for row in rows
            if row["period"] == "FY2024" and row["row_type"] == "consolidated"
        )
        consolidated["segment_reconciliation_status"] = "single_segment"
        hidden = _segment("FY2024", 10)
        hidden.update(
            {
                "reported_segment": "Second disclosed segment",
                "normalized_segment": "Second disclosed segment",
                "partition_id": "hidden-partition",
                "partition_exhaustive": "false",
                "partition_mutually_exclusive": "false",
            }
        )
        rows.append(hidden)

        problems = _validate(rows)

        self.assertTrue(
            any("exactly one disclosed segment member" in problem for problem in problems),
            problems,
        )

    def test_partition_does_not_receive_a_fixed_one_percent_allowance(self):
        rows = _valid_rows()
        consolidated = next(
            row for row in rows
            if row["period"] == "FY2024" and row["row_type"] == "consolidated"
        )
        consolidated["check_to_consolidated"] = "-0.5"
        next(
            row for row in rows
            if row["period"] == "FY2024" and row["row_type"] == "segment"
        )["revenue"] = "89.5"

        problems = _validate(rows)

        self.assertTrue(any("member sum" in problem for problem in problems), problems)

    def test_not_applicable_is_a_narrow_no_partition_rows_exception(self):
        rows = [
            row for row in _valid_rows()
            if not (row["period"] == "FY2024" and row["row_type"] == "segment")
        ]
        consolidated = next(
            row for row in rows
            if row["period"] == "FY2024" and row["row_type"] == "consolidated"
        )
        consolidated.update(
            {
                "partition_id": "",
                "partition_dimension": "",
                "partition_exhaustive": "",
                "partition_mutually_exclusive": "",
                "check_to_consolidated": "",
                "segment_reconciliation_status": "not_applicable",
                "missing_disclosure_reason": "Issuer reports no segment or elimination partition rows.",
            }
        )

        self.assertEqual(_validate(rows), [])

    def test_non_exhaustive_top_customer_view_remains_a_limited_cross_check(self):
        rows = _valid_rows()
        consolidated = next(
            row for row in rows
            if row["period"] == "FY2024" and row["row_type"] == "consolidated"
        )
        consolidated.update(
            {
                "partition_id": "disclosed-top-customers",
                "partition_dimension": "customer",
                "partition_exhaustive": "false",
                "partition_mutually_exclusive": "true",
                "check_to_consolidated": "",
                "segment_reconciliation_status": "disclosure_limited",
                "missing_disclosure_reason": "Only the largest customer is disclosed; the view is not exhaustive.",
            }
        )
        customer = next(
            row for row in rows
            if row["period"] == "FY2024" and row["row_type"] == "segment"
        )
        customer.update(
            {
                "reported_segment": "Largest disclosed customer",
                "normalized_segment": "Largest disclosed customer",
                "revenue": "30",
                "partition_id": "disclosed-top-customers",
                "partition_dimension": "customer",
                "partition_member_id": "largest-disclosed-customer",
                "partition_exhaustive": "false",
                "partition_mutually_exclusive": "true",
            }
        )

        self.assertEqual(_validate(rows, readiness="screen-grade"), [])
        research_grade_problems = _validate(rows, readiness="research-grade")
        self.assertTrue(
            any("readiness_target capped" in problem for problem in research_grade_problems),
            research_grade_problems,
        )
        self.assertFalse(
            any("member sum" in problem for problem in research_grade_problems),
            research_grade_problems,
        )

    def test_top_customer_cross_check_does_not_pollute_a_complete_segment_partition(self):
        rows = _valid_rows()
        for customer_name, revenue in (("Customer A", 30), ("Customer B", 20)):
            customer = _segment("FY2024", revenue)
            customer.update(
                {
                    "reported_segment": customer_name,
                    "normalized_segment": customer_name,
                    "partition_id": "disclosed-top-customers",
                    "partition_dimension": "customer",
                    "partition_member_id": customer_name,
                    "partition_exhaustive": "false",
                    "partition_mutually_exclusive": "true",
                }
            )
            rows.append(customer)

        self.assertEqual(_validate(rows), [])

    def test_top_n_plus_other_full_partition_remains_valid(self):
        rows = _valid_rows()
        consolidated = next(
            row for row in rows
            if row["period"] == "FY2024" and row["row_type"] == "consolidated"
        )
        consolidated.update(
            {
                "partition_id": "customer-top-n-plus-other",
                "partition_dimension": "customer",
                "partition_exhaustive": "true",
                "partition_mutually_exclusive": "true",
                "segment_reconciliation_status": "reconciled",
            }
        )
        customer = next(
            row for row in rows
            if row["period"] == "FY2024" and row["row_type"] == "segment"
        )
        customer.update(
            {
                "reported_segment": "Top customer",
                "normalized_segment": "Top customer",
                "revenue": "30",
                "partition_id": "customer-top-n-plus-other",
                "partition_dimension": "customer",
                "partition_member_id": "top-customer",
            }
        )
        other = dict(customer)
        other.update(
            {
                "reported_segment": "Other customers",
                "normalized_segment": "Other customers",
                "partition_member_id": "other-customers",
                "revenue": "60",
            }
        )
        rows.append(other)

        self.assertEqual(_validate(rows), [])

    def test_disclosure_limited_cannot_hide_a_declared_full_partition_mismatch(self):
        rows = _valid_rows()
        consolidated = next(
            row for row in rows
            if row["period"] == "FY2024" and row["row_type"] == "consolidated"
        )
        consolidated.update(
            {
                "segment_reconciliation_status": "disclosure_limited",
                "missing_disclosure_reason": "Segment detail is described as disclosure limited.",
            }
        )
        next(
            row for row in rows
            if row["period"] == "FY2024" and row["row_type"] == "segment"
        )["revenue"] = "1"

        problems = _validate(rows, readiness="screen-grade")

        self.assertTrue(any("member sum" in problem for problem in problems), problems)

    def test_full_partition_cannot_ignore_a_nonnumeric_declared_elimination(self):
        rows = _valid_rows()
        elimination = _segment("FY2024", 0)
        elimination.update(
            {
                "row_type": "elimination",
                "reported_segment": "Intersegment eliminations",
                "normalized_segment": "Intersegment eliminations",
                "revenue": "",
                "missing_disclosure_reason": "Elimination amount is not disclosed.",
            }
        )
        rows.append(elimination)

        problems = _validate(rows)

        self.assertTrue(
            any("members must be non-empty and numeric" in problem for problem in problems),
            problems,
        )

    def test_partition_members_must_match_parent_identity_and_basis(self):
        mutations = (
            ("currency", "EUR"),
            ("period_type", "interim"),
            ("actual_or_forecast", "forecast"),
        )
        for field, value in mutations:
            with self.subTest(field=field):
                rows = _valid_rows()
                segment = next(
                    row for row in rows
                    if row["period"] == "FY2024" and row["row_type"] == "segment"
                )
                segment[field] = value

                problems = _validate(rows)

                self.assertTrue(
                    any(f"member {field}" in problem for problem in problems),
                    problems,
                )

    def test_full_partition_rejects_duplicate_member_identity(self):
        rows = _valid_rows()
        first = next(
            row for row in rows
            if row["period"] == "FY2024" and row["row_type"] == "segment"
        )
        first["revenue"] = "45"
        duplicate = dict(first)
        duplicate["revenue"] = "45"
        rows.append(duplicate)

        problems = _validate(rows)

        self.assertTrue(any("duplicate member identity" in problem for problem in problems), problems)

    def test_reported_partition_rejects_duplicate_reported_identity_with_new_normalized_alias(self):
        rows = _valid_rows()
        first = next(
            row for row in rows
            if row["period"] == "FY2024" and row["row_type"] == "segment"
        )
        first["revenue"] = "45"
        duplicate = dict(first)
        duplicate.update(
            {
                "normalized_segment": "Alternate normalized alias",
                "revenue": "45",
            }
        )
        rows.append(duplicate)

        problems = _validate(rows)

        self.assertTrue(
            any(
                "duplicate member identity Operating segment for "
                "partition_dimension reported_operating_segment" in problem
                for problem in problems
            ),
            problems,
        )

    def test_reported_partition_rejects_placeholder_in_its_mapped_member_field(self):
        rows = _valid_rows()
        member = next(
            row for row in rows
            if row["period"] == "FY2024" and row["row_type"] == "segment"
        )
        member.update(
            {
                "reported_segment": "TBD",
                "normalized_segment": "Usable-looking normalized alias",
            }
        )

        problems = _validate(rows)

        self.assertTrue(
            any(
                "partition_dimension reported_operating_segment requires "
                "non-placeholder reported_segment" in problem
                for problem in problems
            ),
            problems,
        )

    def test_generic_partition_rejects_duplicate_member_id_despite_alias_changes(self):
        rows = _valid_rows()
        consolidated = next(
            row for row in rows
            if row["period"] == "FY2024" and row["row_type"] == "consolidated"
        )
        consolidated.update(
            {
                "partition_id": "customer-partition",
                "partition_dimension": "customer",
            }
        )
        first = next(
            row for row in rows
            if row["period"] == "FY2024" and row["row_type"] == "segment"
        )
        first.update(
            {
                "reported_segment": "Customer alias A",
                "normalized_segment": "Normalized alias A",
                "partition_id": "customer-partition",
                "partition_dimension": "customer",
                "partition_member_id": "customer-001",
                "revenue": "45",
            }
        )
        duplicate = dict(first)
        duplicate.update(
            {
                "reported_segment": "Customer alias B",
                "normalized_segment": "Normalized alias B",
                "revenue": "45",
            }
        )
        rows.append(duplicate)

        problems = _validate(rows)

        self.assertTrue(
            any(
                "duplicate member identity customer-001 for partition_dimension customer"
                in problem
                for problem in problems
            ),
            problems,
        )

    def test_placeholder_period_row_is_reported_instead_of_silently_filtered(self):
        rows = _valid_rows()
        hidden = _segment("TBD", 1)
        hidden.update(
            {
                "reported_segment": "Hidden segment",
                "normalized_segment": "Hidden segment",
            }
        )
        rows.append(hidden)

        problems = _validate(rows)

        self.assertTrue(
            any("period must be explicit; blank/TBD/PENDING is invalid" in problem for problem in problems),
            problems,
        )

    def test_normalized_partition_rejects_duplicate_normalized_identity_with_new_reported_alias(self):
        rows = _valid_rows()
        consolidated = next(
            row for row in rows
            if row["period"] == "FY2024" and row["row_type"] == "consolidated"
        )
        consolidated.update(
            {
                "partition_id": "normalized-branches",
                "partition_dimension": "normalized_economic_branch",
            }
        )
        first = next(
            row for row in rows
            if row["period"] == "FY2024" and row["row_type"] == "segment"
        )
        first.update(
            {
                "reported_segment": "Reported segment A",
                "normalized_segment": "Compute branch",
                "revenue": "45",
                "partition_id": "normalized-branches",
                "partition_dimension": "normalized_economic_branch",
            }
        )
        duplicate = dict(first)
        duplicate.update(
            {
                "reported_segment": "Reported segment B",
                "revenue": "45",
            }
        )
        rows.append(duplicate)

        problems = _validate(rows)

        self.assertTrue(
            any(
                "duplicate member identity Compute branch for "
                "partition_dimension normalized_economic_branch" in problem
                for problem in problems
            ),
            problems,
        )

    def test_partition_member_uniqueness_uses_only_the_declared_dimension_field(self):
        cases = (
            (
                "reported_operating_segment",
                "reported_segment",
                "normalized_segment",
                "Shared reported member",
                "Normalized alias",
            ),
            (
                "normalized_economic_branch",
                "normalized_segment",
                "reported_segment",
                "Shared normalized member",
                "Reported alias",
            ),
        )
        for dimension, primary_field, alias_field, member_name, alias_prefix in cases:
            with self.subTest(partition_dimension=dimension):
                rows = _valid_rows()
                consolidated = next(
                    row for row in rows
                    if row["period"] == "FY2024" and row["row_type"] == "consolidated"
                )
                consolidated["partition_dimension"] = dimension
                first = next(
                    row for row in rows
                    if row["period"] == "FY2024" and row["row_type"] == "segment"
                )
                first.update(
                    {
                        "partition_dimension": dimension,
                        primary_field: member_name,
                        alias_field: f"{alias_prefix} A",
                        "revenue": "45",
                    }
                )
                duplicate = dict(first)
                duplicate.update(
                    {
                        "row_type": "elimination",
                        alias_field: f"{alias_prefix} B",
                        "revenue": "45",
                    }
                )
                rows.append(duplicate)

                problems = _validate(rows)

                self.assertTrue(
                    any(
                        f"duplicate member identity {member_name} for "
                        f"partition_dimension {dimension}" in problem
                        for problem in problems
                    ),
                    problems,
                )

    def test_historical_identities_do_not_receive_a_fixed_percent_allowance(self):
        cases = (
            (
                "gross profit",
                lambda rows: next(
                    row for row in rows
                    if row["period"] == "FY2024" and row["row_type"] == "consolidated"
                ).__setitem__("gross_profit", "35.5"),
                "revenue - cost",
            ),
            (
                "comparability bridge",
                lambda rows: next(
                    row for row in rows
                    if row["period"] == "FY2024" and row["row_type"] == "consolidated"
                ).update(
                    {
                        "comparability_status": "bridged",
                        "perimeter_bridge": "Reported perimeter recast to comparable scope.",
                        "reported_revenue": "88",
                        "reported_cost": "52.8",
                        "reported_gross_profit": "35.2",
                        "reported_operating_profit": "17.6",
                        "reported_gaap_net_income_attributable": "10.56",
                        "revenue_comparability_delta": "1.5",
                        "cost_comparability_delta": "1.2",
                        "gross_profit_comparability_delta": "0.8",
                        "operating_profit_comparability_delta": "0.4",
                        "gaap_net_income_attributable_comparability_delta": "0.24",
                    }
                ),
                "revenue_comparability_delta",
            ),
            (
                "forecast bridge",
                lambda rows: next(
                    row for row in rows if row["period_type"] == "first_forecast"
                ).__setitem__("revenue_bridge_delta", "59.5"),
                "revenue_bridge_delta",
            ),
        )
        for label, mutate, expected in cases:
            with self.subTest(case=label):
                rows = _valid_rows()
                mutate(rows)

                problems = _validate(rows)

                self.assertTrue(any(expected in problem for problem in problems), problems)

    def test_reconciled_partition_must_be_declared_exhaustive_and_mutually_exclusive(self):
        rows = _valid_rows()
        target = next(
            row for row in rows
            if row["period"] == "FY2024" and row["row_type"] == "consolidated"
        )
        target["partition_exhaustive"] = "false"

        problems = _validate(rows)

        self.assertTrue(
            any("exhaustive and mutually exclusive" in problem for problem in problems),
            problems,
        )

    def test_declared_residual_cannot_disagree_with_recomputed_partition(self):
        rows = _valid_rows()
        target = next(
            row for row in rows
            if row["period"] == "FY2024" and row["row_type"] == "consolidated"
        )
        target["check_to_consolidated"] = "1"

        problems = _validate(rows)

        self.assertTrue(any("does not equal recomputed residual" in problem for problem in problems), problems)

    def test_bridged_comparability_requires_a_real_scope_or_accounting_bridge(self):
        rows = _valid_rows()
        target = next(row for row in rows if row["period"] == "FY2024" and row["row_type"] == "consolidated")
        target["comparability_status"] = "bridged"

        problems = _validate(rows)

        self.assertTrue(any("comparability" in problem and "bridge" in problem for problem in problems))

    def test_bridge_narrative_without_metric_reconciliation_is_not_comparable_history(self):
        rows = _valid_rows()
        target = next(row for row in rows if row["period"] == "FY2024" and row["row_type"] == "consolidated")
        target.update(
            {
                "comparability_status": "bridged",
                "perimeter_bridge": "Acquisition added the target business during the period.",
            }
        )

        problems = _validate(rows)

        self.assertTrue(any("comparability_delta" in problem for problem in problems))

    def test_quantified_metric_level_comparability_bridge_passes(self):
        rows = _valid_rows()
        target = next(row for row in rows if row["period"] == "FY2024" and row["row_type"] == "consolidated")
        target.update(
            {
                "comparability_status": "bridged",
                "perimeter_bridge": "Acquisition recast to the continuing-operations perimeter.",
                "reported_revenue": "88",
                "reported_cost": "52.8",
                "reported_gross_profit": "35.2",
                "reported_operating_profit": "17.6",
                "reported_gaap_net_income_attributable": "10.56",
                "revenue_comparability_delta": "2",
                "cost_comparability_delta": "1.2",
                "gross_profit_comparability_delta": "0.8",
                "operating_profit_comparability_delta": "0.4",
                "gaap_net_income_attributable_comparability_delta": "0.24",
            }
        )

        self.assertEqual(_validate(rows), [])

    def test_first_forecast_deltas_must_reconcile_from_marked_latest_actual(self):
        rows = _valid_rows()
        forecast = next(row for row in rows if row["period_type"] == "first_forecast")
        forecast["revenue_bridge_delta"] = "12"

        problems = _validate(rows)

        self.assertTrue(any("revenue_bridge_delta" in problem for problem in problems))


if __name__ == "__main__":
    unittest.main()
