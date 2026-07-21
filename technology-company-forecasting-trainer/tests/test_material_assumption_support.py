"""Reference-thesis evidence is gated by causal lineage, not labels or quotas."""
from __future__ import annotations

import sys
from pathlib import Path


SKILL = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SKILL / "scripts"))

from provenance_contract import ProvenanceNode
from validate_research_completeness import validate_material_assumption_lineage


GRAPH = {
    "nodes": [
        {"id": "end_demand", "kind": "observable", "unit": "unit"},
        {"id": "revenue", "kind": "derived", "unit": "USD"},
        {"id": "demand_break", "kind": "falsification", "unit": "ratio"},
        {"id": "minor_opex", "kind": "input", "unit": "USD"},
    ],
    "equations": [
        {"id": "eq:revenue", "output": "revenue", "operation": "identity", "inputs": ["end_demand"]},
    ],
}


def _node(source_id: str, root: str, publisher: str, team: str, method: str) -> ProvenanceNode:
    return ProvenanceNode(
        source_id=source_id,
        root_original_source_id=root,
        derived_from_source_id="" if source_id == root else root,
        common_origin=source_id != root,
        independence_cluster=root,
        publisher=publisher,
        authors=frozenset({team}),
        measurement_method_id=method,
        source_type="measurement",
    )


INDEPENDENT = {
    "S1": _node("S1", "S1", "issuer", "issuer team", "acceptance census"),
    "S2": _node("S2", "S2", "industry body", "panel team", "sell through panel"),
}


def _row(**updates) -> dict[str, str]:
    row = {
        "assumption_id": "A1",
        "claim": "end demand persists",
        "driver_link": "end_demand",
        "test_delta": "end demand -10%",
        "revenue_impact_pct": "10",
        "profit_impact_pct": "18",
        "changes_conclusion": "yes",
        "support_status": "corroborated",
        "source_ids": "S1;S2",
        "lanes": "",
        "falsification_trigger": "demand_break",
        "horizon": "FY+2",
        "scenario": "central_operating_path",
        "notes": "",
    }
    row.update(updates)
    return row


def _validate(rows, provenance=INDEPENDENT):
    return validate_material_assumption_lineage(
        rows,
        graph=GRAPH,
        carriers={"end_demand"},
        falsifiers={"demand_break"},
        known_scenario_ids={"central_operating_path", "demand_contraction"},
        reference_scenario_ids={"central_operating_path"},
        known_source_ids=set(provenance),
        eligible_source_ids=set(provenance),
        provenance_graph=provenance,
    )[0]


def test_uncomputed_main_line_assumption_is_rejected():
    errors = _validate([_row(test_delta="")])
    assert "test_delta" in " ".join(errors)


def test_corrobated_label_must_be_true_not_two_lane_text():
    copied = {
        "S1": INDEPENDENT["S1"],
        "S2": _node("S2", "S1", "issuer", "issuer team", "renamed copy"),
    }
    errors = _validate([_row()], copied)
    assert "independent" in " ".join(errors)


def test_one_direct_hard_anchor_is_not_rejected_by_a_universal_source_quota():
    errors = _validate([
        _row(support_status="hard_anchor", source_ids="S1")
    ])
    assert errors == []


def test_main_line_assumption_needs_a_declared_falsification_node():
    errors = _validate([_row(falsification_trigger="price fell in a report")])
    assert "falsification" in " ".join(errors)


def test_off_main_line_detail_is_not_promoted_to_a_universal_gate():
    errors = _validate([
        _row(
            driver_link="minor_opex",
            changes_conclusion="no",
            test_delta="",
            support_status="single_lane",
            source_ids="",
            falsification_trigger="",
        )
    ])
    assert errors == []


def test_genuinely_independent_main_line_support_passes():
    assert _validate([_row()]) == []


def test_reference_role_uses_free_scenario_id_not_literal_base_label():
    assert _validate([_row(scenario="central_operating_path")]) == []
    errors = _validate([_row(scenario="Base")])
    assert "unknown scenario IDs Base" in " ".join(errors)


def test_alternative_scenario_does_not_inherit_reference_evidence_permission():
    assert _validate([
        _row(
            scenario="demand_contraction",
            support_status="scenario_only",
            source_ids="",
            test_delta="",
            falsification_trigger="",
        )
    ]) == []
