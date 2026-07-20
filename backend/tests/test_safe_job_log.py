from __future__ import annotations

import json

from backend.app import jobs


def test_safe_job_log_removes_the_exact_prompt_prefix(monkeypatch, tmp_path):
    monkeypatch.setattr(jobs, "JOBS_DIR", tmp_path)
    job_id = "20260720-120000-abcd"
    prompt = "private research instructions\nwith several lines"
    record = {
        "id": job_id,
        "prompt": prompt,
        "status": "finished",
    }
    (tmp_path / f"{job_id}.json").write_text(json.dumps(record), encoding="utf-8")
    (tmp_path / f"{job_id}.log").write_text(
        f"# job {job_id} | live_forecast | engine=codex\n"
        f"# prompt:\n{prompt}\n\n"
        "engine progress line\n# result summary:\ndelivered safely\n",
        encoding="utf-8",
    )

    regular = jobs.job_log(job_id, tail=200)
    safe = jobs.job_log(job_id, tail=200, safe=True)

    assert prompt in regular
    assert prompt not in safe
    assert "# prompt:" not in safe
    assert "engine progress line" in safe
    assert "delivered safely" in safe


def test_safe_job_log_fails_closed_when_the_record_is_missing(monkeypatch, tmp_path):
    monkeypatch.setattr(jobs, "JOBS_DIR", tmp_path)
    job_id = "20260720-120001-abcd"
    (tmp_path / f"{job_id}.log").write_text("untrusted output", encoding="utf-8")

    assert jobs.job_log(job_id, tail=200, safe=True) is None
