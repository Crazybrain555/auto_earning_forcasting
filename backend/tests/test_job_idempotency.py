from __future__ import annotations

import time

import pytest

from backend.app import jobs


class _FakeProcess:
    pid = 4242

    def wait(self):
        return 0


class _RunningProcess:
    def poll(self):
        return None


def _prepare(monkeypatch, tmp_path):
    launches = []
    from backend.app import db as app_db
    # Keep the reaper's db.scan ingest away from the real runs tree in tests.
    monkeypatch.setattr(app_db, "scan", lambda *args, **kwargs: None)
    monkeypatch.setattr(jobs, "JOBS_DIR", tmp_path)
    monkeypatch.setattr(jobs, "build_prompt", lambda job_type, params: ("safe prompt", dict(params)))
    monkeypatch.setattr(jobs, "compose_cmd", lambda spec, prompt, params: ["codex", "exec"])
    monkeypatch.setattr(
        jobs,
        "engines",
        lambda: {"codex": {"available": True, "cmd": ["codex", "exec", "{prompt}"]}},
    )

    def popen(*args, **kwargs):
        launches.append((args, kwargs))
        return _FakeProcess()

    monkeypatch.setattr(jobs.subprocess, "Popen", popen)
    jobs._PROCS.clear()
    return launches


def test_job_start_replays_same_idempotency_key_without_second_process(monkeypatch, tmp_path):
    launches = _prepare(monkeypatch, tmp_path)

    first = jobs.start_job(
        "live_forecast",
        "codex",
        {"entity": "Micron", "security": "MU"},
        idempotency_key="65756a06-e455-4ea0-944a-dc8a88d42a22",
    )
    second = jobs.start_job(
        "live_forecast",
        "codex",
        {"entity": "Micron", "security": "MU"},
        idempotency_key="65756a06-e455-4ea0-944a-dc8a88d42a22",
    )

    assert second["id"] == first["id"]
    assert len(launches) == 1

    # Let the tiny fake reaper leave no global process entry for other tests.
    for _ in range(20):
        if not jobs._PROCS:
            break
        time.sleep(0.01)


def test_job_start_rejects_reusing_key_for_different_payload(monkeypatch, tmp_path):
    launches = _prepare(monkeypatch, tmp_path)
    key = "65756a06-e455-4ea0-944a-dc8a88d42a22"
    jobs.start_job("live_forecast", "codex", {"entity": "Micron", "security": "MU"}, idempotency_key=key)

    with pytest.raises(ValueError, match="Idempotency-Key"):
        jobs.start_job("live_forecast", "codex", {"entity": "NVIDIA", "security": "NVDA"}, idempotency_key=key)

    assert len(launches) == 1


@pytest.mark.parametrize("key", ["short", "../escape", "contains space", "x" * 129])
def test_job_start_rejects_unsafe_idempotency_key(monkeypatch, tmp_path, key):
    launches = _prepare(monkeypatch, tmp_path)
    with pytest.raises(ValueError, match="Idempotency-Key"):
        jobs.start_job("live_forecast", "codex", {"entity": "Micron", "security": "MU"}, idempotency_key=key)
    assert launches == []


def test_job_start_queues_instead_of_rejecting_at_capacity(monkeypatch, tmp_path):
    launches = _prepare(monkeypatch, tmp_path)
    monkeypatch.setitem(jobs.CONFIG, "max_concurrent_jobs", 1)
    jobs._PROCS["already-running"] = _RunningProcess()

    record = jobs.start_job(
        "live_forecast",
        "codex",
        {"entity": "Micron", "security": "MU"},
    )

    assert record["status"] == "queued"
    assert record["queue_position"] == 1
    assert launches == []
    jobs._PROCS.clear()
