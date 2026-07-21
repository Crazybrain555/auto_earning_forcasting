import csv
import unittest
from pathlib import Path


SKILL = Path(__file__).resolve().parents[1]


class OperationalDecisionContractTest(unittest.TestCase):
    def _header(self, name: str) -> set[str]:
        with (SKILL / "assets" / "templates" / name).open(
            encoding="utf-8-sig", newline=""
        ) as handle:
            return set(next(csv.reader(handle)))

    def test_patent_register_carries_legal_and_economic_diligence(self):
        required = {
            "patent_evidence_status",
            "patent_source_ids",
            "patent_claim_scope",
            "patent_assignee_and_encumbrances",
            "patent_family_and_citation_context",
            "freedom_to_operate_status",
            "patent_design_around_and_knowhow",
            "ip_economic_link",
            "patent_not_material_reason",
        }
        self.assertTrue(
            required <= self._header("technology_commercialization_template.csv"),
            required - self._header("technology_commercialization_template.csv"),
        )

    def test_monitoring_register_is_cell_and_date_executable(self):
        required = {
            "model_cell_or_formula",
            "monitor_type",
            "frequency",
            "next_expected_at",
            "milestone_date",
            "current_value",
            "model_value",
            "trigger_operator",
            "trigger_value",
            "action_if_breached",
            "owner",
        }
        self.assertTrue(
            required <= self._header("driver_monitoring_template.csv"),
            required - self._header("driver_monitoring_template.csv"),
        )

    def test_every_decision_memo_has_operational_minimum_tables(self):
        skill_text = (SKILL / "SKILL.md").read_text(encoding="utf-8")
        output_contract = (SKILL / "references" / "core-output-and-valuation.md").read_text(
            encoding="utf-8"
        )
        for phrase in (
            "Minimum decision-memo tables",
            "not-decision-ready does not waive",
            "Patent / IP diligence",
            "Value-creation identity",
            "Executable monitoring",
            "Recurring / usage economics",
        ):
            self.assertIn(phrase, skill_text + "\n" + output_contract)


if __name__ == "__main__":
    unittest.main()
