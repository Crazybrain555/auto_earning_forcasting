"""The statement-decomposition spine.

The method organizes every case around the reconstructed historical
statements: accounting credibility is diagnosed first, the statement skeleton
is rebuilt and closed by construction, and only then are material lines
decomposed into driver paths. These tests pin that ordering and the
single-source-of-truth rules that keep the document set from fragmenting.
Each test owns one failure mode (constitution #8).
"""
from __future__ import annotations

import json
import re
import unittest
from pathlib import Path

TRAINER_ROOT = Path(__file__).resolve().parents[1]
METHOD_SYSTEM = TRAINER_ROOT / "assets" / "method_system.json"
CONTRACTS = TRAINER_ROOT / "assets" / "skill_system" / "contracts" / "protocol_manifest.json"
REFERENCES = TRAINER_ROOT / "references"


def _method_system() -> dict:
    return json.loads(METHOD_SYSTEM.read_text(encoding="utf-8"))


def _stage_ids() -> list[str]:
    return [stage["id"] for stage in _method_system()["stages"]]


class StatementSkeletonOrdering(unittest.TestCase):
    def test_statement_skeleton_stages_exist_and_precede_decomposition(self) -> None:
        ids = _stage_ids()
        for required in ("accounting_diagnosis", "historical_statements"):
            self.assertIn(required, ids)
        order = {stage_id: index for index, stage_id in enumerate(ids)}
        self.assertLess(order["evidence_system"], order["accounting_diagnosis"])
        self.assertLess(order["accounting_diagnosis"], order["historical_statements"])
        self.assertLess(order["historical_statements"], order["causal_graph"])
        self.assertLess(order["causal_graph"], order["operating_model"])
        self.assertLess(order["operating_model"], order["integrated_statements"])

    def test_historical_base_gates_live_in_the_skeleton_stage_not_evidence(self) -> None:
        stages = {stage["id"]: stage for stage in _method_system()["stages"]}
        evidence_gates = set(stages["evidence_system"]["gates"])
        skeleton_gates = set(stages["historical_statements"]["gates"])
        for moved in (
            "three_year_complete_comparable_historical_base",
            "historical_profit_chain_and_segment_reconciliation",
            "latest_actual_to_first_forecast_numeric_bridge",
        ):
            self.assertNotIn(moved, evidence_gates)
        self.assertIn("operating_financing_split_closes", skeleton_gates)
        self.assertIn("estimates_fenced_out_of_closure", skeleton_gates)

    def test_line_decomposition_gates_present_on_causal_graph_stage(self) -> None:
        stages = {stage["id"]: stage for stage in _method_system()["stages"]}
        gates = set(stages["causal_graph"]["gates"])
        self.assertIn("lines_ranked_by_materiality", gates)
        self.assertIn("fat_tail_drivers_marked_scenario_only", gates)


class ProseMatchesRegistry(unittest.TestCase):
    def test_spine_documents_use_only_registered_stage_ids(self) -> None:
        ids = set(_stage_ids())
        retired = {"freeze_monitor_learn"}
        for name in ("research-sop.md", "analysis-kernel.md"):
            text = (REFERENCES / name).read_text(encoding="utf-8")
            tokens = set(re.findall(r"`([a-z]+(?:_[a-z]+)+)`", text))
            stage_like = {t for t in tokens if t in ids | retired}
            self.assertEqual(
                stage_like - ids, set(),
                f"{name} names stage IDs that are not in method_system.json",
            )

    def test_stage_files_resolve_and_forwarding_stubs_are_gone(self) -> None:
        for stage in _method_system()["stages"]:
            for rel in stage["files"]:
                self.assertTrue(
                    (TRAINER_ROOT / rel).exists(),
                    f"stage {stage['id']} routes to missing file {rel}",
                )
        for stub in ("causal-modeling-kernel.md", "core-forecast-workflow.md"):
            self.assertFalse(
                (REFERENCES / stub).exists(),
                f"forwarding stub {stub} should be deleted, not maintained",
            )


class SingleSourceOfTruth(unittest.TestCase):
    def test_canonical_definition_registry_and_unique_anchors(self) -> None:
        registry = _method_system().get("canonical_definitions")
        self.assertIsInstance(registry, dict)
        self.assertGreaterEqual(len(registry), 4)
        reference_files = sorted(REFERENCES.glob("*.md"))
        for concept, owner_rel in registry.items():
            owner = TRAINER_ROOT / owner_rel
            self.assertTrue(owner.exists(), f"{concept} owner missing: {owner_rel}")
            anchor = f"<!-- canonical: {concept} -->"
            self.assertIn(
                anchor, owner.read_text(encoding="utf-8"),
                f"{owner_rel} must carry the canonical anchor for {concept}",
            )
            holders = [
                path.name
                for path in reference_files
                if anchor in path.read_text(encoding="utf-8")
            ]
            expected = [Path(owner_rel).name] if owner.parent == REFERENCES else []
            self.assertEqual(
                holders, expected,
                f"{concept} is defined in more than one reference document",
            )


class StockFlowAttribution(unittest.TestCase):
    def test_protocol_declares_stock_flow_attribution_invariant(self) -> None:
        manifest = json.loads(CONTRACTS.read_text(encoding="utf-8"))
        invariants = manifest.get("reasoning_invariants") or {}
        self.assertIn("stock_flow_attribution", invariants)
        principle = json.dumps(invariants["stock_flow_attribution"]).lower()
        self.assertIn("exactly once", principle)


if __name__ == "__main__":
    unittest.main()
