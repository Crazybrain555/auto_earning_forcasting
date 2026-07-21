from __future__ import annotations

import json

import pytest

from backend.app import data, jobs


def company(entity: str, security: str, as_of: str) -> dict[str, str]:
    return {"entity": entity, "security": security, "as_of": as_of}


def test_round_plan_accepts_case_selected_uneven_groups(monkeypatch, tmp_path):
    monkeypatch.setattr(data, "RUNS_ROOT", tmp_path)

    plan = data.save_round_plan(
        "round-flex",
        [company("Development A", "DA", "2020-01-31")],
        [
            company("Holdout A", "HA", "2020-02-29"),
            company("Holdout B", "HB", "2020-03-31"),
            company("Holdout C", "HC", "2020-04-30"),
        ],
        "case-selected failure modes",
        "abc123",
    )

    assert len(plan["group_a"]) == 1
    assert len(plan["group_b"]) == 3
    assert plan["group_a"][0]["role"] == "development"
    assert all(item["role"] == "validation" for item in plan["group_b"])


@pytest.mark.parametrize("group_a,group_b", [([], [company("B", "B", "2020-01-31")]), ([company("A", "A", "2020-01-31")], [])])
def test_round_plan_requires_evidence_bearing_development_and_holdout_groups(
    monkeypatch, tmp_path, group_a, group_b
):
    monkeypatch.setattr(data, "RUNS_ROOT", tmp_path)

    with pytest.raises(ValueError, match="at least one"):
        data.save_round_plan("round-empty", group_a, group_b, "", "abc123")


def test_round_plan_rejects_the_same_case_in_development_and_holdout(monkeypatch, tmp_path):
    monkeypatch.setattr(data, "RUNS_ROOT", tmp_path)
    same = company("Same issuer", "SAME", "2020-01-31")

    with pytest.raises(ValueError, match="development and validation"):
        data.save_round_plan("round-overlap", [same], [same], "", "abc123")


def test_round_plan_rejects_duplicate_cases_inside_one_group(monkeypatch, tmp_path):
    monkeypatch.setattr(data, "RUNS_ROOT", tmp_path)
    repeated = company("Repeated issuer", "REP", "2020-01-31")

    with pytest.raises(ValueError, match="duplicate case"):
        data.save_round_plan(
            "round-duplicate",
            [repeated, repeated],
            [company("Holdout", "HOLD", "2020-02-29")],
            "",
            "abc123",
        )


def test_round_plan_replanning_preserves_case_and_round_extensions(monkeypatch, tmp_path):
    monkeypatch.setattr(data, "RUNS_ROOT", tmp_path)
    round_dir = tmp_path / "round-preserve"
    round_dir.mkdir()
    (round_dir / "round.json").write_text(
        json.dumps(
            {
                "round_id": "round-preserve",
                "status": "planned",
                "base_method_commit": "original-commit",
                "review_policy": {"kind": "independent"},
                "group_a": [
                    {
                        **company("Development old label", "DEV", "2020-01-31"),
                        "case_id": "DEV@2020-01-31",
                        "role": "development",
                        "curriculum_ref": "CURR-A",
                        "mechanism": "capacity cycle",
                        "metrics": {"revenue_mape": 0.1},
                    }
                ],
                "group_b": [
                    {
                        **company("Holdout", "HOLD", "2020-02-29"),
                        "case_id": "HOLD@2020-02-29",
                        "role": "validation",
                        "target_periods": ["FY1", "FY2"],
                        "scored": False,
                    }
                ],
            }
        ),
        encoding="utf-8",
    )

    plan = data.save_round_plan(
        "round-preserve",
        [company("Development corrected label", "dev", "2020-01-31")],
        [company("Holdout", "hold", "2020-02-29")],
        "updated note",
        "new-commit",
    )

    assert plan["review_policy"] == {"kind": "independent"}
    assert plan["base_method_commit"] == "original-commit"
    assert plan["group_a"][0]["entity"] == "Development corrected label"
    assert plan["group_a"][0]["curriculum_ref"] == "CURR-A"
    assert plan["group_a"][0]["mechanism"] == "capacity cycle"
    assert plan["group_a"][0]["metrics"] == {"revenue_mape": 0.1}
    assert plan["group_b"][0]["target_periods"] == ["FY1", "FY2"]
    assert plan["group_b"][0]["scored"] is False


def test_legacy_two_plus_two_round_remains_a_valid_case_selection(monkeypatch, tmp_path):
    monkeypatch.setattr(data, "RUNS_ROOT", tmp_path)

    plan = data.save_round_plan(
        "round-legacy",
        [
            company("Development A", "DA", "2020-01-31"),
            company("Development B", "DB", "2020-02-29"),
        ],
        [
            company("Holdout A", "HA", "2020-03-31"),
            company("Holdout B", "HB", "2020-04-30"),
        ],
        "legacy-compatible",
        "abc123",
    )

    assert [len(plan["group_a"]), len(plan["group_b"])] == [2, 2]


def test_replanning_an_abandoned_round_reopens_it_as_planned(monkeypatch, tmp_path):
    monkeypatch.setattr(data, "RUNS_ROOT", tmp_path)
    round_dir = tmp_path / "round-reopen"
    round_dir.mkdir()
    (round_dir / "round.json").write_text(
        json.dumps({"round_id": "round-reopen", "status": "abandoned", "abandoned_reason": "old hypothesis"}),
        encoding="utf-8",
    )

    plan = data.save_round_plan(
        "round-reopen",
        [company("Development", "DEV", "2020-01-31")],
        [company("Holdout", "HOLD", "2020-02-29")],
        "new bounded hypothesis",
        "abc123",
    )

    assert plan["status"] == "planned"
    assert plan["abandoned_reason"] == "old hypothesis"


def test_training_round_job_loads_a_case_selected_saved_plan(monkeypatch, tmp_path):
    monkeypatch.setattr(jobs, "RUNS_ROOT", tmp_path)
    round_dir = tmp_path / "round-flex"
    round_dir.mkdir()
    (round_dir / "round.json").write_text(
        json.dumps(
            {
                "group_a": [company("Development A", "DA", "2020-01-31")],
                "group_b": [
                    company("Holdout A", "HA", "2020-02-29"),
                    company("Holdout B", "HB", "2020-03-31"),
                    company("Holdout C", "HC", "2020-04-30"),
                ],
            }
        ),
        encoding="utf-8",
    )

    prompt, normalized = jobs.build_prompt("training_round", {"round_id": "round-flex"})

    assert len(normalized["group_a"]) == 1
    assert len(normalized["group_b"]) == 3
    assert "Development A" in prompt
    assert "Holdout C" in prompt


def test_training_round_job_rejects_cross_group_case_reuse(monkeypatch, tmp_path):
    monkeypatch.setattr(jobs, "RUNS_ROOT", tmp_path)
    same = company("Same issuer", "SAME", "2020-01-31")

    with pytest.raises(ValueError, match="development and validation"):
        jobs.build_prompt(
            "training_round",
            {"round_id": "round-overlap", "group_a": [same], "group_b": [same]},
        )


def test_training_round_job_normalizes_inline_case_identity_and_roles():
    prompt, normalized = jobs.build_prompt(
        "training_round",
        {
            "round_id": "round-inline",
            "group_a": [company("Development", "dev", "2020-01-31")],
            "group_b": [
                company("Holdout A", "ha", "2020-02-29"),
                company("Holdout B", "hb", "2020-03-31"),
            ],
        },
    )

    assert normalized["group_a"][0]["case_id"] == "DEV@2020-01-31"
    assert normalized["group_a"][0]["role"] == "development"
    assert [item["role"] for item in normalized["group_b"]] == ["validation", "validation"]
    assert "Holdout B" in prompt
