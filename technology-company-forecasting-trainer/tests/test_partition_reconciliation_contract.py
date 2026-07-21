"""Partition assurance distinguishes full tie-outs from partial cross-cuts."""

from __future__ import annotations

import importlib.util
from pathlib import Path


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "validate_delivery.py"
SPEC = importlib.util.spec_from_file_location("validate_delivery_partitions", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
SPEC.loader.exec_module(MODULE)


def _primary_tree() -> dict:
    return {
        "segments": [
            {"name": "Segment A", "revenue_point": 60.0},
            {"name": "Segment B", "revenue_point": 40.0},
        ],
        "partition": {
            "partition_id": "reported-segments",
            "dimension": "reported_operating_segment",
            "exhaustive": True,
            "mutually_exclusive": True,
            "declared_residual": 0.0,
        },
        "cross_check_views": [],
    }


def test_primary_revenue_partition_recomputes_instead_of_trusting_zero_residual() -> None:
    tree = _primary_tree()
    tree["segments"][1]["revenue_point"] = 35.0

    problems = MODULE.validate_driver_tree_partitions(tree, consolidated_revenue=100.0)

    assert any("member sum" in problem for problem in problems), problems
    assert any("declared residual" in problem for problem in problems), problems


def test_primary_tree_cannot_claim_reconciliation_for_partial_partition() -> None:
    tree = _primary_tree()
    tree["partition"]["exhaustive"] = False
    tree["partition"]["declared_residual"] = None

    problems = MODULE.validate_driver_tree_partitions(tree, consolidated_revenue=100.0)

    assert any("exhaustive and mutually exclusive" in problem for problem in problems), problems


def test_non_exhaustive_top_customer_view_is_not_forced_to_sum_to_one() -> None:
    tree = _primary_tree()
    tree["cross_check_views"] = [{
        "name": "disclosed top customers",
        "members": [
            {"name": "Customer A", "share": 0.40},
            {"name": "Customer B", "share": 0.30},
        ],
        "partition": {
            "partition_id": "disclosed-top-customers",
            "dimension": "customer",
            "exhaustive": False,
            "mutually_exclusive": True,
            "parent_value": 1.0,
            "declared_residual": None,
        },
    }]

    assert MODULE.validate_driver_tree_partitions(tree, consolidated_revenue=100.0) == []


def test_exhaustive_share_partition_does_reconcile_to_one() -> None:
    tree = _primary_tree()
    tree["cross_check_views"] = [{
        "name": "complete customer partition",
        "members": [
            {"name": "Customer A", "share": 0.40},
            {"name": "Customer B", "share": 0.30},
            {"name": "All other customers", "share": 0.20},
        ],
        "partition": {
            "partition_id": "all-customers",
            "dimension": "customer",
            "exhaustive": True,
            "mutually_exclusive": True,
            "parent_value": 1.0,
            "declared_residual": 0.0,
        },
    }]

    problems = MODULE.validate_driver_tree_partitions(tree, consolidated_revenue=100.0)

    assert any("member sum" in problem for problem in problems), problems
    assert any("declared residual" in problem for problem in problems), problems


def test_mutually_exclusive_top_customer_subset_cannot_exceed_parent() -> None:
    tree = _primary_tree()
    tree["cross_check_views"] = [{
        "name": "disclosed top customers",
        "members": [
            {"name": "Customer A", "share": 0.70},
            {"name": "Customer B", "share": 0.50},
        ],
        "partition": {
            "partition_id": "disclosed-top-customers",
            "dimension": "customer",
            "exhaustive": False,
            "mutually_exclusive": True,
            "parent_value": 1.0,
            "declared_residual": None,
        },
    }]

    problems = MODULE.validate_driver_tree_partitions(tree, consolidated_revenue=100.0)

    assert any("exceeds parent" in problem for problem in problems), problems


def _driver_schedule_row(*, role: str, exhaustive: str) -> dict[str, str]:
    return {
        "segment_or_product": "AI products",
        "primary_tree_or_cross_check": role,
        "partition_id": "ai-product-view",
        "partition_dimension": "product",
        "partition_exhaustive": exhaustive,
        "partition_mutually_exclusive": "true",
        "driver_node_ids": "ai_units;ai_asp",
        "evidence_source_ids": "SRC1",
        "consolidation_link": "ai_revenue",
        "schedule_status": "accepted",
    }


def test_construction_schedule_routes_partial_views_to_cross_check() -> None:
    partial_primary = _driver_schedule_row(role="primary", exhaustive="false")
    partial_cross_check = _driver_schedule_row(role="cross_check", exhaustive="false")

    primary_problems = MODULE.validate_product_customer_driver_rows([partial_primary])

    assert any("route partial or overlapping rows to cross_check" in problem for problem in primary_problems)
    assert MODULE.validate_product_customer_driver_rows([partial_cross_check]) == []
