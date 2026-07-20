import json, subprocess, sys, tempfile, unittest
from pathlib import Path
SKILL = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SKILL / "scripts"))
import _seal_core as core

SNAP = {"outputs": {
    "year_1": {"revenue_point": 100, "revenue_low": 90, "revenue_high": 110, "profit_point": 10, "profit_low": 5, "profit_high": 15, "point_evaluable": True},
    "year_2": {"revenue_point": 120, "revenue_low": 100, "revenue_high": 140, "profit_point": 12, "profit_low": 4, "profit_high": 20, "point_evaluable": True},
    "year_3_distribution": {"revenue_point": 130, "revenue_low": 80, "revenue_high": 180, "profit_point": 13, "profit_low": -20, "profit_high": 40, "point_evaluable": False}}}
ACTUALS = {"case_id": "T", "retrieved_after_seal": True, "retrieved_at": "2026-01-01T00:00:00Z",
           "periods": [{"period": "FY+1", "revenue": 105, "profit": 11},
                        {"period": "FY+2", "revenue": 118, "profit": 10},
                        {"period": "FY+3", "revenue": 70, "profit": -10}]}


def sealed_workspace(td):
    w = Path(td) / "case"
    w.mkdir()
    (w / "forecast_snapshot.json").write_text(json.dumps(SNAP))
    seal = core.build_seal(w, sealed_at="2026-01-01T00:00:00+00:00")
    (w / "forecast_seal.json").write_text(json.dumps(seal))
    a = Path(td) / "actuals.json"
    a.write_text(json.dumps(ACTUALS))
    return w, a


def score(w, a, extra=None):
    return subprocess.run([sys.executable, str(SKILL / "scripts/score_training_forecast.py"),
                            "--workspace", str(w), "--actuals", str(a)] + (extra or []),
                           capture_output=True, text=True)


class SealedScoreTest(unittest.TestCase):
    def test_clean_seal_scores_and_stays_intact(self):
        with tempfile.TemporaryDirectory() as td:
            w, a = sealed_workspace(td)
            r = score(w, a)
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
            out = json.loads((w / "evaluation/evaluation.json").read_text())
            self.assertTrue(out["hash_verified"])
            self.assertTrue(out["seal_reverified_after_scoring"])
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

if __name__ == "__main__":
    unittest.main()
