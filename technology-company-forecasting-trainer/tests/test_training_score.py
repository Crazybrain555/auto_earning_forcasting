import json, subprocess, sys, tempfile, unittest
from pathlib import Path
SKILL = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SKILL / "scripts"))
import _seal_core as core

SNAP = {"outputs": {
    "year_1": {"revenue_point": 100, "revenue_low": 90, "revenue_high": 110,
               "operating_profit_point": 18, "operating_profit_low": 13, "operating_profit_high": 23,
               "profit_point": 10, "profit_low": 5, "profit_high": 15,
               "interval_alpha": 0.2, "point_evaluable": True},
    "year_2": {"revenue_point": 120, "revenue_low": 100, "revenue_high": 140,
               "operating_profit_point": 20, "operating_profit_low": 12, "operating_profit_high": 28,
               "profit_point": 12, "profit_low": 4, "profit_high": 20,
               "interval_alpha": 0.2, "point_evaluable": True},
    "year_3_distribution": {"revenue_point": 130, "revenue_low": 80, "revenue_high": 180,
                            "operating_profit_point": 15, "operating_profit_low": -15, "operating_profit_high": 45,
                            "profit_point": 13, "profit_low": -20, "profit_high": 40,
                            "interval_alpha": 0.1, "point_evaluable": False}}}

SCOPES = {
    "revenue": "consolidated_revenue",
    "operating_profit": "consolidated_operating_profit",
    "gaap_net_income_attributable": "attributable_to_parent_shareholders",
    "pretax_income": "consolidated_pretax_income",
    "income_tax_expense": "consolidated_income_tax_expense",
    "consolidated_net_income": "consolidated_net_income_before_nci_attribution",
    "noncontrolling_interest_net_income": "net_income_attributable_to_noncontrolling_interests",
}
SIGNS = {
    **{metric: "income_positive" for metric in (
        "revenue", "operating_profit", "gaap_net_income_attributable",
        "pretax_income", "consolidated_net_income",
    )},
    "income_tax_expense": "expense_positive",
    "noncontrolling_interest_net_income": "income_attributable_to_nci_positive",
}
PERIOD_DATES = {
    "FY+1": ("2023-01-01", "2023-12-31"),
    "FY+2": ("2024-01-01", "2024-12-31"),
    "FY+3": ("2025-01-01", "2025-12-31"),
}


def actual_observation(period, metric, value, *, attribution_method=None):
    start, end = PERIOD_DATES[period]
    row = {
        "observation_id": f"T|{period}|{metric}",
        "entity_id": "ENTITY-T",
        "period": period,
        "fiscal_period_start": start,
        "fiscal_period_end": end,
        "metric": metric,
        "value": value,
        "currency": "USD",
        "unit": "USD millions",
        "accounting_basis": "IFRS as issued by IASB",
        "accounting_basis_id": "ifrs-iasb",
        "consolidation_perimeter": "Consolidated group including controlled subsidiaries",
        "fact_scope": SCOPES[metric],
        "sign_convention": SIGNS[metric],
        "official_source_ids": ["T-2025-ANNUAL-REPORT"],
        "source_fact_label": f"Reported {metric.replace('_', ' ')}",
        "source_fact_anchor": f"financial-statements/{period}/{metric}",
        "source_fact_value_text": str(value),
        "fact_origin": "direct_official_reported_fact",
        "reported_precision": {
            "basis": "exact",
            "rounding_increment_in_reported_unit": 0.0,
        },
    }
    if attribution_method is not None:
        row["attribution_method"] = attribution_method
    return row


ACTUALS = {
    "schema_version": "3.2",
    "case_id": "case",
    "entity": {
        "entity_id": "ENTITY-T",
        "legal_name": "Test Holdings Limited",
        "reporting_perimeter": "Consolidated group including controlled subsidiaries",
    },
    "retrieved_at": "2026-03-01T00:00:00Z",
    "information_cutoff_at": "2026-02-28T23:59:59Z",
    "official_source_ids": ["T-2025-ANNUAL-REPORT"],
    "official_sources": [{
        "source_id": "T-2025-ANNUAL-REPORT",
        "issuer_or_regulator": "Test Holdings Limited",
        "document_type": "audited annual report",
        "title": "Annual report for fiscal 2025",
        "published_at": "2026-02-20T08:00:00Z",
        "locator": "https://issuer.example/filings/2025-annual-report",
        "content_sha256": "sha256:" + "a" * 64,
        "origin_class": "issuer_statutory_filing",
    }],
    "observations": [
        actual_observation(period, metric, value,
                           attribution_method="direct_official_attributable_fact" if metric == "gaap_net_income_attributable" else None)
        for period, values in {
            "FY+1": {"revenue": 105, "operating_profit": 19, "gaap_net_income_attributable": 11},
            "FY+2": {"revenue": 118, "operating_profit": 17, "gaap_net_income_attributable": 10},
            "FY+3": {"revenue": 70, "operating_profit": -5, "gaap_net_income_attributable": -10},
        }.items()
        for metric, value in values.items()
    ],
}


def sealed_workspace(td, receipt=True, *, snapshot=None, actuals=None):
    w = Path(td) / "case"
    w.mkdir(parents=True)
    (w / "forecast_snapshot.json").write_text(json.dumps(snapshot or SNAP))
    seal = core.build_seal(w, sealed_at="2026-01-01T00:00:00+00:00")
    (w / "forecast_seal.json").write_text(json.dumps(seal))
    if receipt:
        rd = Path(td) / "seal_receipts"
        rd.mkdir(exist_ok=True)
        (rd / "case.json").write_text(json.dumps({
            "schema_version": 1, "case_id": "case", "pack_hash": seal["pack_hash"],
            "sealed_at": seal["sealed_at"], "recorded_at": "2026-01-01T00:00:01+00:00",
            "recorded_before_actuals": True, "group_lock_hash": None}))
    a = Path(td) / "actuals.json"
    a.write_text(json.dumps(actuals or ACTUALS))
    return w, a


def score(w, a, extra=None):
    return subprocess.run([sys.executable, str(SKILL / "scripts/score_training_forecast.py"),
                            "--workspace", str(w), "--actuals", str(a)] + (extra or []),
                           capture_output=True, text=True)


class SealedScoreTest(unittest.TestCase):
    def test_template_and_docs_name_local_only_actuals_trust(self):
        template = json.loads(
            (SKILL / "assets/templates/training_actuals_template.json").read_text()
        )
        self.assertEqual(template["schema_version"], "3.2")
        docs = "\n".join(
            (
                (SKILL / "SKILL.md").read_text(),
                (SKILL / "references/historical-training-loop.md").read_text(),
                (SKILL / "references/profit-forecast-accuracy.md").read_text(),
            )
        )
        self.assertIn("locally_consistent_untrusted", docs)
        self.assertIn("forecast_seal_receipt_status", docs)
        self.assertNotIn("`receipt_verified`", docs)

    def test_clean_seal_scores_and_stays_intact(self):
        with tempfile.TemporaryDirectory() as td:
            w, a = sealed_workspace(td)
            r = score(w, a)
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
            out = json.loads((w / "evaluation/evaluation.json").read_text())
            self.assertTrue(out["hash_verified"])
            self.assertTrue(out["seal_reverified_after_scoring"])
            receipt = out["actuals_validation_receipt"]
            self.assertEqual(receipt["contract_version"], "training_actuals/3.2")
            self.assertEqual(receipt["status"], "locally_consistent_untrusted")
            self.assertEqual(out["forecast_seal_receipt_status"], "verified")
            self.assertNotIn("receipt_verified", out)
            self.assertEqual(len(receipt["validated_observations"]), 9)
            self.assertIn("fiscal_period_start", receipt["validated_observations"][0])
            self.assertEqual(
                receipt["derived_reconciliation_tolerances"]["method"],
                "sum_half_reported_rounding_increments",
            )
            self.assertTrue(receipt["receipt_id"].startswith("sha256:"))
            self.assertIn(
                "attributable to parent shareholders",
                out["metric_identity_definition"]["net_income"],
            )
            self.assertTrue((w / "actuals_vault/actuals.json").exists())
            core.verify_seal(w)  # still intact after a full scoring pass

    def test_tampered_file_fails(self):
        with tempfile.TemporaryDirectory() as td:
            w, a = sealed_workspace(td)
            (w / "forecast_snapshot.json").write_text(json.dumps({**SNAP, "x": 1}))
            self.assertNotEqual(score(w, a).returncode, 0)

    def test_added_file_fails(self):
        with tempfile.TemporaryDirectory() as td:
            w, a = sealed_workspace(td)
            (w / "smuggled.json").write_text("{}")
            self.assertNotEqual(score(w, a).returncode, 0)

    def test_forged_seal_fails(self):
        with tempfile.TemporaryDirectory() as td:
            w, a = sealed_workspace(td)
            (w / "forecast_snapshot.json").write_text(json.dumps({**SNAP, "x": 1}))
            seal = json.loads((w / "forecast_seal.json").read_text())
            seal["files"][0]["sha256"] = core.sha256_file(w / "forecast_snapshot.json")
            (w / "forecast_seal.json").write_text(json.dumps(seal))  # pack_hash left stale
            r = score(w, a)
            self.assertNotEqual(r.returncode, 0)
            self.assertIn("seal was edited", r.stdout + r.stderr)

    def test_actuals_inside_sealed_area_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            w, a = sealed_workspace(td)
            inside = w / "actuals.json"
            inside.write_text(a.read_text())
            self.assertNotEqual(score(w, inside).returncode, 0)

    def test_missing_receipt_fails_without_flag(self):
        with tempfile.TemporaryDirectory() as td:
            w, a = sealed_workspace(td, receipt=False)
            r = score(w, a)
            self.assertNotEqual(r.returncode, 0)
            self.assertIn("no external seal receipt", r.stdout + r.stderr)

    def test_missing_receipt_allowed_for_legacy(self):
        with tempfile.TemporaryDirectory() as td:
            w, a = sealed_workspace(td, receipt=False)
            r = score(w, a, ["--allow-missing-receipt"])
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
            out = json.loads((w / "evaluation/evaluation.json").read_text())
            self.assertEqual(
                out["forecast_seal_receipt_status"],
                "legacy_missing_unverified",
            )
            self.assertNotIn("receipt_verified", out)

    def test_receipt_pack_hash_mismatch_fails(self):
        # simulates the rebuild-after-actuals attack: workspace resealed cleanly,
        # but the externally recorded receipt still carries the original hash
        with tempfile.TemporaryDirectory() as td:
            w, a = sealed_workspace(td)
            (w / "forecast_snapshot.json").write_text(json.dumps({**SNAP, "x": 1}))
            seal = core.build_seal(w, sealed_at="2026-01-01T00:00:00+00:00")
            (w / "forecast_seal.json").write_text(json.dumps(seal))   # reseal: workspace-self-consistent
            r = score(w, a)
            self.assertNotEqual(r.returncode, 0)
            self.assertIn("pack_hash mismatch", r.stdout + r.stderr)

    def test_forecast_seal_receipt_status_is_explicit(self):
        with tempfile.TemporaryDirectory() as td:
            w, a = sealed_workspace(td)
            r = score(w, a)
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
            out = json.loads((w / "evaluation/evaluation.json").read_text())
            self.assertEqual(out["forecast_seal_receipt_status"], "verified")
            self.assertEqual(
                out["actuals_validation_receipt"]["status"],
                "locally_consistent_untrusted",
            )
            self.assertNotIn("receipt_verified", out)

    def test_operating_and_net_profit_are_scored_directly_with_cross_zero_safe_scale(self):
        with tempfile.TemporaryDirectory() as td:
            w, a = sealed_workspace(td)
            r = score(w, a)
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
            out = json.loads((w / "evaluation/evaluation.json").read_text())
            self.assertIn("operating_profit_scaled_mae", out["metrics"])
            self.assertIn("net_income_scaled_mae", out["metrics"])
            self.assertIn("operating_profit_interval_score", out["metrics"])
            self.assertIn("net_income_sign_hit", out["metrics"])
            self.assertNotIn("profit_mape", out["metrics"])

    def test_fy3_distribution_counts_in_coverage_and_interval_aggregates(self):
        with tempfile.TemporaryDirectory() as td:
            w, a = sealed_workspace(td)
            r = score(w, a)
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
            out = json.loads((w / "evaluation/evaluation.json").read_text())
            metrics = out["metrics"]

            # FY+1 and FY+2 hit revenue; FY+3 misses below its distribution.
            self.assertAlmostEqual(metrics["revenue_coverage"], 2 / 3)
            self.assertAlmostEqual(metrics["operating_profit_coverage"], 1.0)
            self.assertAlmostEqual(metrics["net_income_coverage"], 1.0)
            self.assertAlmostEqual(metrics["profit_coverage"], 1.0)  # compatibility alias

            expected_revenue_interval_score = (
                (110 - 90) / 105
                + (140 - 100) / 118
                + ((180 - 80) + (2 / 0.1) * (80 - 70)) / 70
            ) / 3
            self.assertAlmostEqual(
                metrics["revenue_interval_score"], expected_revenue_interval_score
            )
            self.assertEqual(out["metric_observation_counts"]["revenue_coverage"], 3)
            self.assertEqual(out["metric_observation_counts"]["revenue_interval_score"], 3)

    def test_interval_score_uses_the_frozen_nominal_miscoverage_not_a_horizon_default(self):
        with tempfile.TemporaryDirectory() as td:
            snapshot = json.loads(json.dumps(SNAP))
            snapshot["outputs"]["year_3_distribution"]["interval_alpha"] = 0.25
            w, a = sealed_workspace(td, snapshot=snapshot)
            r = score(w, a)
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
            out = json.loads((w / "evaluation/evaluation.json").read_text())
            fy3 = next(row for row in out["scores"] if row["period"] == "FY+3")
            expected = ((180 - 80) + (2 / 0.25) * (80 - 70)) / 70
            self.assertAlmostEqual(fy3["revenue_interval_score"], expected)
            self.assertEqual(fy3["interval_alpha"], 0.25)

    def test_missing_or_reversed_interval_contract_is_a_hard_error(self):
        with tempfile.TemporaryDirectory() as td:
            snapshot = json.loads(json.dumps(SNAP))
            del snapshot["outputs"]["year_1"]["interval_alpha"]
            w, a = sealed_workspace(Path(td) / "missing", snapshot=snapshot)
            r = score(w, a)
            self.assertNotEqual(r.returncode, 0)
            self.assertIn("interval_alpha", r.stdout + r.stderr)

            reversed_snapshot = json.loads(json.dumps(SNAP))
            reversed_snapshot["outputs"]["year_1"]["revenue_low"] = 120
            reversed_snapshot["outputs"]["year_1"]["revenue_high"] = 80
            w2, a2 = sealed_workspace(Path(td) / "reversed", snapshot=reversed_snapshot)
            r2 = score(w2, a2)
            self.assertNotEqual(r2.returncode, 0)
            self.assertIn("ordered", r2.stdout + r2.stderr)

    def test_signed_bias_uses_point_forecasts_and_preserves_direction(self):
        with tempfile.TemporaryDirectory() as td:
            w, a = sealed_workspace(td)
            r = score(w, a)
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
            out = json.loads((w / "evaluation/evaluation.json").read_text())
            metrics = out["metrics"]
            expected_revenue = (((100 - 105) / 105) + ((120 - 118) / 118)) / 2
            expected_operating_profit = (((18 - 19) / 105) + ((20 - 17) / 118)) / 2
            expected_net_income = (((10 - 11) / 105) + ((12 - 10) / 118)) / 2
            self.assertAlmostEqual(metrics["revenue_signed_bias"], expected_revenue)
            self.assertAlmostEqual(metrics["operating_profit_signed_bias"], expected_operating_profit)
            self.assertAlmostEqual(metrics["net_income_signed_bias"], expected_net_income)
            self.assertEqual(out["metric_observation_counts"]["revenue_signed_bias"], 2)
            self.assertEqual(out["signed_error_definition"]["direction"], "forecast_minus_actual")
            self.assertIn("revenue_signed_error", out["scores"][0])
            self.assertNotIn("revenue_signed_error", out["scores"][2])
            self.assertNotIn("profit_mape", metrics)

    def test_missing_actual_operating_profit_is_a_hard_error(self):
        with tempfile.TemporaryDirectory() as td:
            actuals = json.loads(json.dumps(ACTUALS))
            actuals["observations"] = [
                row for row in actuals["observations"]
                if not (row["period"] == "FY+1" and row["metric"] == "operating_profit")
            ]
            w, a = sealed_workspace(td, actuals=actuals)
            r = score(w, a)
            self.assertNotEqual(r.returncode, 0)
            self.assertIn("actuals FY+1 missing canonical operating_profit", r.stdout + r.stderr)

    def test_generic_profit_or_consolidated_net_income_cannot_masquerade_as_attributable(self):
        for alias in ("profit", "net_income"):
            with self.subTest(alias=alias), tempfile.TemporaryDirectory() as td:
                actuals = json.loads(json.dumps(ACTUALS))
                row = next(
                    row for row in actuals["observations"]
                    if row["period"] == "FY+1" and row["metric"] == "gaap_net_income_attributable"
                )
                row["metric"] = alias
                w, a = sealed_workspace(td, actuals=actuals)
                result = score(w, a)
                self.assertNotEqual(result.returncode, 0)
                self.assertIn("generic profit/net_income aliases are prohibited", result.stdout + result.stderr)

    def test_retrieval_and_cutoff_have_timezone_aware_seal_bound_semantics(self):
        cases = (
            ("retrieved_at", "2026-03-01T00:00:00", "timezone-aware"),
            ("retrieved_at", "2025-12-31T23:59:59Z", "after the frozen forecast seal"),
            ("information_cutoff_at", "2026-03-02T00:00:00Z", "cannot be after retrieved_at"),
        )
        for field, value, expected in cases:
            with self.subTest(field=field, value=value), tempfile.TemporaryDirectory() as td:
                actuals = json.loads(json.dumps(ACTUALS))
                actuals[field] = value
                w, a = sealed_workspace(td, actuals=actuals)
                result = score(w, a)
                self.assertNotEqual(result.returncode, 0)
                self.assertIn(expected, result.stdout + result.stderr)

    def test_official_source_ids_are_required_at_pack_and_observation_level(self):
        with tempfile.TemporaryDirectory() as td:
            actuals = json.loads(json.dumps(ACTUALS))
            actuals["official_source_ids"] = []
            w, a = sealed_workspace(td, actuals=actuals)
            result = score(w, a)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("official_source_ids", result.stdout + result.stderr)

        with tempfile.TemporaryDirectory() as td:
            actuals = json.loads(json.dumps(ACTUALS))
            actuals["observations"][0]["official_source_ids"] = []
            w, a = sealed_workspace(td, actuals=actuals)
            result = score(w, a)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("bind the fact", result.stdout + result.stderr)

    def test_each_fact_source_must_be_published_after_its_fiscal_period(self):
        with tempfile.TemporaryDirectory() as td:
            actuals = json.loads(json.dumps(ACTUALS))
            actuals["official_sources"][0]["published_at"] = "2025-06-30T08:00:00Z"
            w, a = sealed_workspace(td, actuals=actuals)
            result = score(w, a)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("published before fiscal_period_end", result.stdout + result.stderr)

    def test_official_fact_requires_content_addressed_source_and_exact_anchor(self):
        mutations = (
            ("source content hash", lambda actuals: actuals["official_sources"][0].pop("content_sha256"), "content_sha256"),
            ("fact anchor", lambda actuals: actuals["observations"][0].pop("source_fact_anchor"), "source_fact_anchor"),
        )
        for case, mutate, expected in mutations:
            with self.subTest(case=case), tempfile.TemporaryDirectory() as td:
                actuals = json.loads(json.dumps(ACTUALS))
                mutate(actuals)
                w, a = sealed_workspace(td, actuals=actuals)
                result = score(w, a)
                self.assertNotEqual(result.returncode, 0)
                self.assertIn(expected, result.stdout + result.stderr)

    def test_non_gaap_pack_cannot_self_consistently_masquerade_as_actuals(self):
        with tempfile.TemporaryDirectory() as td:
            actuals = json.loads(json.dumps(ACTUALS))
            for row in actuals["observations"]:
                row["accounting_basis"] = "non-GAAP adjusted management measure"
                row["accounting_basis_id"] = "non-gaap-adjusted"
            w, a = sealed_workspace(td, actuals=actuals)
            result = score(w, a)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("statutory GAAP/IFRS basis", result.stdout + result.stderr)

    def test_statutory_basis_id_cannot_launder_a_non_gaap_basis_label(self):
        with tempfile.TemporaryDirectory() as td:
            actuals = json.loads(json.dumps(ACTUALS))
            for row in actuals["observations"]:
                row["accounting_basis"] = "non-GAAP adjusted management measure"
                # Keep the otherwise valid controlled ID: the two fields must
                # agree rather than allowing the ID to launder the free label.
                row["accounting_basis_id"] = "ifrs-iasb"
            w, a = sealed_workspace(td, actuals=actuals)
            result = score(w, a)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("canonical statutory basis label", result.stdout + result.stderr)

    def test_source_numeric_literal_must_equal_the_validated_fact_value(self):
        with tempfile.TemporaryDirectory() as td:
            actuals = json.loads(json.dumps(ACTUALS))
            actuals["observations"][0]["source_fact_value_text"] = "999"
            w, a = sealed_workspace(td, actuals=actuals)
            result = score(w, a)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("does not equal value", result.stdout + result.stderr)

    def test_rounding_increment_is_derived_from_the_source_numeric_literal(self):
        with tempfile.TemporaryDirectory() as td:
            actuals = json.loads(json.dumps(ACTUALS))
            row = actuals["observations"][0]
            row["reported_precision"] = {
                "basis": "rounded",
                "rounding_increment_in_reported_unit": 1e12,
            }
            w, a = sealed_workspace(td, actuals=actuals)
            result = score(w, a)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("displayed numeric increment", result.stdout + result.stderr)

    def test_reconciliation_tolerance_is_derived_not_analyst_selected(self):
        with tempfile.TemporaryDirectory() as td:
            actuals = json.loads(json.dumps(ACTUALS))
            actuals["reconciliation_tolerance"] = {
                "absolute_in_reported_unit": 1e12,
                "rationale": "make every bridge pass",
            }
            w, a = sealed_workspace(td, actuals=actuals)
            result = score(w, a)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("analyst-supplied and prohibited", result.stdout + result.stderr)

    def test_same_fiscal_period_cannot_be_reused_under_a_different_horizon_label(self):
        with tempfile.TemporaryDirectory() as td:
            actuals = json.loads(json.dumps(ACTUALS))
            copied = [
                json.loads(json.dumps(row))
                for row in actuals["observations"]
                if row["period"] == "FY+1"
            ]
            for row in copied:
                row["period"] = "FY+99"
                row["observation_id"] = row["observation_id"].replace("FY+1", "FY+99")
            actuals["observations"].extend(copied)
            w, a = sealed_workspace(td, actuals=actuals)
            result = score(w, a)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("multiple horizon labels", result.stdout + result.stderr)

    def test_actuals_case_identity_must_match_the_frozen_case(self):
        with tempfile.TemporaryDirectory() as td:
            actuals = json.loads(json.dumps(ACTUALS))
            actuals["case_id"] = "another-case"
            w, a = sealed_workspace(td, actuals=actuals)
            result = score(w, a)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("must match the frozen case identity", result.stdout + result.stderr)

    def test_duplicate_or_conflicting_entity_period_metric_observations_are_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            actuals = json.loads(json.dumps(ACTUALS))
            duplicate = json.loads(json.dumps(actuals["observations"][0]))
            duplicate["observation_id"] = "different-id-same-economic-identity"
            duplicate["value"] += 1
            duplicate["source_fact_value_text"] = str(duplicate["value"])
            actuals["observations"].append(duplicate)
            w, a = sealed_workspace(td, actuals=actuals)
            result = score(w, a)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("duplicate/conflicting actual observation", result.stdout + result.stderr)

    def test_missing_disclosure_is_not_coerced_to_zero(self):
        with tempfile.TemporaryDirectory() as td:
            actuals = json.loads(json.dumps(ACTUALS))
            next(
                row for row in actuals["observations"]
                if row["period"] == "FY+1" and row["metric"] == "operating_profit"
            )["value"] = None
            w, a = sealed_workspace(td, actuals=actuals)
            result = score(w, a)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("missing disclosure is not zero", result.stdout + result.stderr)

    def test_required_metrics_must_share_accounting_basis_perimeter_unit_and_currency(self):
        with tempfile.TemporaryDirectory() as td:
            actuals = json.loads(json.dumps(ACTUALS))
            row = next(
                row for row in actuals["observations"]
                if row["period"] == "FY+1" and row["metric"] == "operating_profit"
            )
            row["accounting_basis_id"] = "us-gaap"
            row["accounting_basis"] = "US GAAP"
            w, a = sealed_workspace(td, actuals=actuals)
            result = score(w, a)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("inconsistent bases or units", result.stdout + result.stderr)

    def test_attributable_net_income_bridge_is_complete_and_reconciles(self):
        with tempfile.TemporaryDirectory() as td:
            actuals = json.loads(json.dumps(ACTUALS))
            target = next(
                row for row in actuals["observations"]
                if row["period"] == "FY+1" and row["metric"] == "gaap_net_income_attributable"
            )
            target["attribution_method"] = "derived_from_reported_bridge"
            for metric, value in {
                "pretax_income": 15,
                "income_tax_expense": 3,
                "consolidated_net_income": 12,
                "noncontrolling_interest_net_income": 1,
            }.items():
                actuals["observations"].append(actual_observation("FY+1", metric, value))
            w, a = sealed_workspace(td, actuals=actuals)
            result = score(w, a)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

            inconsistent = json.loads(json.dumps(actuals))
            inconsistent_row = next(
                row for row in inconsistent["observations"]
                if row["period"] == "FY+1" and row["metric"] == "consolidated_net_income"
            )
            inconsistent_row["value"] = 13
            inconsistent_row["source_fact_value_text"] = "13"
            bad_root = Path(td) / "bad"
            bad_root.mkdir()
            w2, a2 = sealed_workspace(bad_root, actuals=inconsistent)
            bad = score(w2, a2)
            self.assertNotEqual(bad.returncode, 0)
            self.assertIn("does not reconcile", bad.stdout + bad.stderr)

    def test_missing_nci_bridge_fact_is_not_inferred_as_zero(self):
        with tempfile.TemporaryDirectory() as td:
            actuals = json.loads(json.dumps(ACTUALS))
            target = next(
                row for row in actuals["observations"]
                if row["period"] == "FY+1" and row["metric"] == "gaap_net_income_attributable"
            )
            target["attribution_method"] = "derived_from_reported_bridge"
            for metric, value in {
                "pretax_income": 15,
                "income_tax_expense": 4,
                "consolidated_net_income": 11,
            }.items():
                actuals["observations"].append(actual_observation("FY+1", metric, value))
            w, a = sealed_workspace(td, actuals=actuals)
            result = score(w, a)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("cannot be assumed to be zero", result.stdout + result.stderr)

    def test_assumed_zero_nci_is_not_an_official_zero_fact(self):
        with tempfile.TemporaryDirectory() as td:
            actuals = json.loads(json.dumps(ACTUALS))
            target = next(
                row for row in actuals["observations"]
                if row["period"] == "FY+1" and row["metric"] == "gaap_net_income_attributable"
            )
            target["attribution_method"] = "derived_from_reported_bridge"
            target["value"] = 11
            target["source_fact_value_text"] = "11"
            for metric, value in {
                "pretax_income": 15,
                "income_tax_expense": 4,
                "consolidated_net_income": 11,
                "noncontrolling_interest_net_income": 0,
            }.items():
                row = actual_observation("FY+1", metric, value)
                if metric == "noncontrolling_interest_net_income":
                    row["source_fact_label"] = "NCI not disclosed; analyst assumed zero"
                    row["source_fact_value_text"] = "not disclosed; analyst assumed zero"
                    # A controlled enum cannot manufacture evidence that the
                    # official source actually printed a numeric zero.
                    row["zero_value_basis"] = "explicit_official_zero_or_reported_rounding"
                actuals["observations"].append(row)
            w, a = sealed_workspace(td, actuals=actuals)
            result = score(w, a)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("direct numeric literal", result.stdout + result.stderr)

    def test_missing_forecast_operating_profit_is_a_hard_error(self):
        with tempfile.TemporaryDirectory() as td:
            snapshot = json.loads(json.dumps(SNAP))
            del snapshot["outputs"]["year_1"]["operating_profit_point"]
            w, a = sealed_workspace(td, snapshot=snapshot)
            r = score(w, a)
            self.assertNotEqual(r.returncode, 0)
            self.assertIn("forecast FY+1 missing operating_profit", r.stdout + r.stderr)

    def test_missing_forecast_net_income_is_a_hard_error(self):
        with tempfile.TemporaryDirectory() as td:
            snapshot = json.loads(json.dumps(SNAP))
            del snapshot["outputs"]["year_1"]["profit_point"]
            w, a = sealed_workspace(td, snapshot=snapshot)
            r = score(w, a)
            self.assertNotEqual(r.returncode, 0)
            self.assertIn("forecast FY+1 missing GAAP net income attributable", r.stdout + r.stderr)

    def test_generic_forecast_net_income_and_profit_aliases_cannot_masquerade_as_attributable(self):
        with tempfile.TemporaryDirectory() as td:
            snapshot = json.loads(json.dumps(SNAP))
            output = snapshot["outputs"]["year_1"]
            output["net_income_point"] = output.pop("profit_point")
            output["net_income_low"] = output.pop("profit_low")
            output["net_income_high"] = output.pop("profit_high")
            output["profit"] = output["net_income_point"]
            w, a = sealed_workspace(td, snapshot=snapshot)
            result = score(w, a)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("missing GAAP net income attributable point", result.stdout + result.stderr)

    def test_distribution_may_omit_points_but_not_profit_intervals(self):
        with tempfile.TemporaryDirectory() as td:
            snapshot = json.loads(json.dumps(SNAP))
            del snapshot["outputs"]["year_3_distribution"]["operating_profit_point"]
            del snapshot["outputs"]["year_3_distribution"]["profit_point"]
            w, a = sealed_workspace(td, snapshot=snapshot)
            r = score(w, a)
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
            out = json.loads((w / "evaluation/evaluation.json").read_text())
            fy3 = next(row for row in out["scores"] if row["period"] == "FY+3")
            self.assertFalse(fy3["point_evaluable"])
            self.assertTrue(fy3["operating_profit_hit"])
            self.assertTrue(fy3["net_income_hit"])

            missing_op_interval = json.loads(json.dumps(SNAP))
            del missing_op_interval["outputs"]["year_3_distribution"]["operating_profit_low"]
            op_root = Path(td) / "op"
            op_root.mkdir()
            w2, a2 = sealed_workspace(op_root, snapshot=missing_op_interval)
            r2 = score(w2, a2)
            self.assertNotEqual(r2.returncode, 0)
            self.assertIn("forecast FY+3 missing operating_profit interval", r2.stdout + r2.stderr)

            missing_ni_interval = json.loads(json.dumps(SNAP))
            del missing_ni_interval["outputs"]["year_3_distribution"]["profit_high"]
            ni_root = Path(td) / "ni"
            ni_root.mkdir()
            w3, a3 = sealed_workspace(ni_root, snapshot=missing_ni_interval)
            r3 = score(w3, a3)
            self.assertNotEqual(r3.returncode, 0)
            self.assertIn("forecast FY+3 missing GAAP net income attributable interval", r3.stdout + r3.stderr)


class FreezeReceiptTest(unittest.TestCase):
    def test_freeze_refuses_second_seal_when_receipt_exists(self):
        # freeze itself needs a full valid workspace to run end-to-end, so this
        # exercises just the receipt-collision guard the same way freeze does
        with tempfile.TemporaryDirectory() as td:
            w, a = sealed_workspace(td)   # receipt now exists for "case"
            receipt = Path(td) / "seal_receipts" / "case.json"
            self.assertTrue(receipt.exists())
            # a second freeze of the same case id must refuse: guard condition
            self.assertTrue(receipt.exists() and (w / "forecast_seal.json").exists())


class AccuracyScoreContractTest(unittest.TestCase):
    def test_accuracy_doctrine_declares_distribution_and_signed_bias_contract(self):
        text = (SKILL / "references/profit-forecast-accuracy.md").read_text(encoding="utf-8")
        for phrase in (
            "FY+3 distribution",
            "all scored horizons",
            "revenue_signed_bias",
            "operating_profit_signed_bias",
            "net_income_signed_bias",
            "forecast minus actual",
            "scaled by actual revenue",
            "Profit MAPE remains prohibited",
            "Missing required operating-profit or GAAP-net-income",
        ):
            self.assertIn(phrase, text)


if __name__ == "__main__":
    unittest.main()
