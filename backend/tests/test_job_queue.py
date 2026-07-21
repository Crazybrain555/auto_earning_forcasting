"""The runner job queue: capacity-full submits queue (never error), promote
FIFO when the slot frees, dedup identical pending requests, and cancel cheaply.
"""
from __future__ import annotations

import json
import threading
import time

import pytest

from backend.app import db as app_db
from backend.app import jobs


class _HeldProcess:
    """A fake child whose exit the test controls."""

    pid = 4242

    def __init__(self):
        self._done = threading.Event()
        self._rc = 0

    def finish(self, rc: int = 0):
        self._rc = rc
        self._done.set()

    def poll(self):
        return self._rc if self._done.is_set() else None

    def wait(self):
        self._done.wait(timeout=10)
        return self._rc


def _prepare(monkeypatch, tmp_path):
    procs: list[_HeldProcess] = []
    # The reaper ingests results via db.scan over the real runs tree; in tests
    # that is seconds of background IO against real data - neutralize it.
    monkeypatch.setattr(app_db, "scan", lambda *args, **kwargs: None)
    monkeypatch.setattr(jobs, "JOBS_DIR", tmp_path)
    monkeypatch.setattr(jobs, "build_prompt", lambda job_type, params: ("safe prompt", dict(params)))
    monkeypatch.setattr(jobs, "compose_cmd", lambda spec, prompt, params: ["codex", "exec"])
    monkeypatch.setattr(
        jobs,
        "engines",
        lambda: {"codex": {"available": True, "cmd": ["codex", "exec", "{prompt}"]}},
    )
    monkeypatch.setitem(jobs.CONFIG, "max_concurrent_jobs", 1)

    def popen(*args, **kwargs):
        proc = _HeldProcess()
        procs.append(proc)
        return proc

    monkeypatch.setattr(jobs.subprocess, "Popen", popen)
    jobs._PROCS.clear()
    return procs


def _wait_for(predicate, timeout=5.0):
    deadline = time.time() + timeout
    while time.time() < deadline:
        if predicate():
            return True
        time.sleep(0.02)
    return predicate()


def test_second_submit_queues_and_promotes_when_first_finishes(monkeypatch, tmp_path):
    procs = _prepare(monkeypatch, tmp_path)

    first = jobs.start_job("live_forecast", "codex", {"entity": "Micron", "security": "MU"})
    assert first["status"] == "running"

    second = jobs.start_job("live_forecast", "codex", {"entity": "NVIDIA", "security": "NVDA"})
    assert second["status"] == "queued"
    assert second["queue_position"] == 1
    assert len(procs) == 1

    procs[0].finish(0)
    assert _wait_for(lambda: len(procs) == 2), "queued job was not promoted after the slot freed"
    assert _wait_for(lambda: (jobs.get_job(second["id"]) or {}).get("status") == "running")
    assert (jobs.get_job(first["id"]) or {}).get("status") == "finished"

    procs[1].finish(0)
    assert _wait_for(lambda: not jobs._PROCS)


def test_same_company_is_rejected_outright_with_existing_job_info(monkeypatch, tmp_path):
    """One company, one job: repeat submits for a pending company bounce with
    a pointer to the existing job - never queue, never silently merge."""
    procs = _prepare(monkeypatch, tmp_path)

    first = jobs.start_job("live_forecast", "codex", {"entity": "Micron", "security": "MU"})
    with pytest.raises(jobs.CompanyBusyError, match="company busy: MU") as excinfo:
        jobs.start_job("live_forecast", "codex", {"entity": "Micron", "security": "MU"})
    assert excinfo.value.existing["id"] == first["id"]
    assert f"job {first['id']}" in str(excinfo.value)

    # Training for the same company is just as much a conflict as a forecast.
    with pytest.raises(jobs.CompanyBusyError, match="company busy: MU"):
        jobs.start_job(
            "training_case", "codex",
            {"entity": "Micron", "security": "MU", "as_of": "2020-01-31",
             "round_id": "round-1", "case_role": "development"},
        )
    assert len(procs) == 1

    procs[0].finish(0)
    assert _wait_for(lambda: not jobs._PROCS)


def test_cancel_then_resubmit_after_company_busy(monkeypatch, tmp_path):
    """The advertised escape hatch: stop the existing job, resubmit, accepted."""
    procs = _prepare(monkeypatch, tmp_path)

    first = jobs.start_job("live_forecast", "codex", {"entity": "Micron", "security": "MU"})
    with pytest.raises(jobs.CompanyBusyError):
        jobs.start_job("live_forecast", "codex", {"entity": "Micron", "security": "MU"})

    jobs.stop_job(first["id"])
    procs[0].finish(-15)
    assert _wait_for(lambda: not jobs._PROCS)

    second = jobs.start_job("live_forecast", "codex", {"entity": "Micron", "security": "MU"})
    assert second["id"] != first["id"]
    assert second["status"] == "running"
    procs[-1].finish(0)
    assert _wait_for(lambda: not jobs._PROCS)


def test_identical_pending_request_is_deduplicated(monkeypatch, tmp_path):
    """Content dedup still guards company-less types (suggest_watch)."""
    procs = _prepare(monkeypatch, tmp_path)

    first = jobs.start_job("suggest_watch", "codex", {"hint": "光模块"})
    dup = jobs.start_job("suggest_watch", "codex", {"hint": "光模块"})

    assert dup["id"] == first["id"]
    assert dup["deduplicated"] is True
    assert len(procs) == 1

    procs[0].finish(0)
    assert _wait_for(lambda: not jobs._PROCS)


def test_dedup_records_alias_so_bridge_lease_retry_replays_after_terminal(monkeypatch, tmp_path):
    """A hosted command retried by the bridge carries the SAME idempotency key
    it was collapsed under; once the collapsed-into job finishes, the retry
    must replay that job instead of paying for a fresh run."""
    procs = _prepare(monkeypatch, tmp_path)

    first = jobs.start_job("suggest_watch", "codex", {"hint": "存储上游"})
    collapsed = jobs.start_job(
        "suggest_watch", "codex", {"hint": "存储上游"},
        idempotency_key="11111111-2222-3333-4444-555555555555",
    )
    assert collapsed["deduplicated"] is True

    procs[0].finish(0)
    assert _wait_for(lambda: (jobs.get_job(first["id"]) or {}).get("status") == "finished")

    replay = jobs.start_job(
        "suggest_watch", "codex", {"hint": "存储上游"},
        idempotency_key="11111111-2222-3333-4444-555555555555",
    )
    assert replay["id"] == first["id"], "lease retry must replay, not start a duplicate run"
    assert len(procs) == 1


def test_delete_refuses_queued_records(monkeypatch, tmp_path):
    _prepare(monkeypatch, tmp_path)
    jobs._PROCS["already-running"] = _HeldProcess()
    queued = jobs.start_job("live_forecast", "codex", {"entity": "A", "security": "AAA"})
    with pytest.raises(PermissionError, match="queued"):
        jobs.delete_job(queued["id"])
    jobs._PROCS.clear()


def test_cancel_queued_job_is_a_cheap_dequeue(monkeypatch, tmp_path):
    procs = _prepare(monkeypatch, tmp_path)

    jobs.start_job("live_forecast", "codex", {"entity": "Micron", "security": "MU"})
    queued = jobs.start_job("live_forecast", "codex", {"entity": "NVIDIA", "security": "NVDA"})
    assert queued["status"] == "queued"

    stopped = jobs.stop_job(queued["id"])
    assert stopped["status"] == "stopped"
    assert len(procs) == 1

    procs[0].finish(0)
    assert _wait_for(lambda: not jobs._PROCS)
    # The cancelled job must never be promoted afterwards.
    assert len(procs) == 1
    assert (jobs.get_job(queued["id"]) or {}).get("status") == "stopped"


def test_queue_positions_are_fifo(monkeypatch, tmp_path):
    _prepare(monkeypatch, tmp_path)
    jobs._PROCS["already-running"] = _HeldProcess()

    a = jobs.start_job("live_forecast", "codex", {"entity": "A", "security": "AAA"})
    b = jobs.start_job("live_forecast", "codex", {"entity": "B", "security": "BBB"})
    assert (a["queue_position"], b["queue_position"]) == (1, 2)

    listed = {r["id"]: r for r in jobs.list_jobs()}
    assert listed[a["id"]]["queue_position"] == 1
    assert listed[b["id"]]["queue_position"] == 2
    jobs._PROCS.clear()


def test_bounded_queue_rejects_overflow(monkeypatch, tmp_path):
    _prepare(monkeypatch, tmp_path)
    monkeypatch.setitem(jobs.CONFIG, "max_queued_jobs", 1)
    jobs._PROCS["already-running"] = _HeldProcess()

    jobs.start_job("live_forecast", "codex", {"entity": "A", "security": "AAA"})
    with pytest.raises(jobs.QueueFullError, match="queue is full"):
        jobs.start_job("live_forecast", "codex", {"entity": "B", "security": "BBB"})
    jobs._PROCS.clear()


def test_detached_running_record_occupies_the_slot(monkeypatch, tmp_path):
    """A backend restart must not fail open: a running_detached record whose
    pid is still alive keeps the slot busy even though _PROCS is empty."""
    procs = _prepare(monkeypatch, tmp_path)

    detached = {
        "id": "20260101-000000-aaaa",
        "type": "live_forecast",
        "engine": "codex",
        "host": jobs.HOSTNAME,
        "params": {"entity": "Micron", "security": "MU"},
        "prompt": "safe prompt",
        "pid": 987654,
        "status": "running",
        "started_at": jobs.now(),
        "ended_at": None,
        "returncode": None,
        "log": str(tmp_path / "20260101-000000-aaaa.log"),
        "idempotency_key": None,
        "idempotency_fingerprint": "not-a-real-fingerprint",
    }
    (tmp_path / "20260101-000000-aaaa.json").write_text(
        json.dumps(detached), encoding="utf-8"
    )

    class _AliveProbe:
        stdout = "codex exec --something\n"

    monkeypatch.setattr(jobs.subprocess, "run", lambda *a, **k: _AliveProbe())

    record = jobs.start_job("live_forecast", "codex", {"entity": "NVIDIA", "security": "NVDA"})
    assert record["status"] == "queued", "detached running job must keep the slot occupied"
    assert procs == []


def test_jobs_run_in_parallel_up_to_the_concurrency_limit(monkeypatch, tmp_path):
    procs = _prepare(monkeypatch, tmp_path)
    monkeypatch.setitem(jobs.CONFIG, "max_concurrent_jobs", 2)

    a = jobs.start_job("live_forecast", "codex", {"entity": "A", "security": "AAA"})
    b = jobs.start_job("live_forecast", "codex", {"entity": "B", "security": "BBB"})
    c = jobs.start_job("live_forecast", "codex", {"entity": "C", "security": "CCC"})

    assert (a["status"], b["status"], c["status"]) == ("running", "running", "queued")
    assert len(procs) == 2

    procs[0].finish(0)
    assert _wait_for(lambda: len(procs) == 3), "third job was not promoted when a slot freed"
    procs[1].finish(0)
    procs[2].finish(0)
    assert _wait_for(lambda: not jobs._PROCS)


def test_same_workspace_never_runs_twice_concurrently(monkeypatch, tmp_path):
    """Workspace mutex is the floor for company-less jobs sharing output
    files: they serialize instead of racing (company-keyed jobs are already
    rejected outright by the company rule before reaching this)."""
    procs = _prepare(monkeypatch, tmp_path)
    monkeypatch.setitem(jobs.CONFIG, "max_concurrent_jobs", 3)

    a = jobs.start_job("suggest_watch", "codex", {"hint": "光模块", "workspace": "/runs/shared"})
    b = jobs.start_job("suggest_watch", "codex", {"hint": "存储上游", "workspace": "/runs/shared"})
    c = jobs.start_job("suggest_watch", "codex", {"hint": "先进封装", "workspace": "/runs/other"})

    assert a["status"] == "running"
    assert b["status"] == "queued", "same-workspace job must wait for the workspace to free"
    assert c["status"] == "running", "a different workspace may pass a blocked job"
    assert len(procs) == 2

    procs[0].finish(0)
    assert _wait_for(lambda: (jobs.get_job(b["id"]) or {}).get("status") == "running")
    procs[1].finish(0)
    procs[2].finish(0)
    assert _wait_for(lambda: not jobs._PROCS)


def test_training_jobs_take_the_runner_exclusively(monkeypatch, tmp_path):
    procs = _prepare(monkeypatch, tmp_path)
    monkeypatch.setitem(jobs.CONFIG, "max_concurrent_jobs", 5)

    forecast = jobs.start_job("live_forecast", "codex", {"entity": "A", "security": "AAA"})
    training = jobs.start_job("training_round", "codex", {"round_id": "round-9"})
    later = jobs.start_job("live_forecast", "codex", {"entity": "B", "security": "BBB"})

    # Training waits for the runner to drain, and nothing may jump past it.
    assert forecast["status"] == "running"
    assert training["status"] == "queued"
    assert later["status"] == "queued"
    assert len(procs) == 1

    procs[0].finish(0)
    assert _wait_for(lambda: (jobs.get_job(training["id"]) or {}).get("status") == "running")
    # While training runs, the later forecast must keep waiting.
    assert (jobs.get_job(later["id"]) or {}).get("status") == "queued"
    assert len(procs) == 2

    procs[1].finish(0)
    assert _wait_for(lambda: (jobs.get_job(later["id"]) or {}).get("status") == "running")
    procs[2].finish(0)
    assert _wait_for(lambda: not jobs._PROCS)


def test_submit_rate_limit_blocks_burst_but_not_dedup(monkeypatch, tmp_path):
    _prepare(monkeypatch, tmp_path)
    monkeypatch.setitem(jobs.CONFIG, "max_concurrent_jobs", 1)
    monkeypatch.setitem(jobs.CONFIG, "submit_rate_max", 3)
    monkeypatch.setitem(jobs.CONFIG, "submit_rate_window_s", 300)
    jobs._PROCS["already-running"] = _HeldProcess()

    jobs.start_job("live_forecast", "codex", {"entity": "A", "security": "AAA"})
    jobs.start_job("live_forecast", "codex", {"entity": "B", "security": "BBB"})
    jobs.start_job("live_forecast", "codex", {"entity": "C", "security": "CCC"})

    # A same-company repeat bounces on the company rule (before the rate
    # ceiling) and consumes no submission budget.
    with pytest.raises(jobs.CompanyBusyError):
        jobs.start_job("live_forecast", "codex", {"entity": "A", "security": "AAA"})

    with pytest.raises(jobs.RateLimitError, match="too many job submissions"):
        jobs.start_job("live_forecast", "codex", {"entity": "D", "security": "DDD"})
    jobs._PROCS.clear()


def test_engine_unavailable_at_promotion_fails_the_job_and_moves_on(monkeypatch, tmp_path):
    procs = _prepare(monkeypatch, tmp_path)
    jobs._PROCS["already-running"] = _HeldProcess()

    queued = jobs.start_job("live_forecast", "codex", {"entity": "A", "security": "AAA"})
    assert queued["status"] == "queued"

    monkeypatch.setattr(
        jobs, "engines",
        lambda: {"codex": {"available": False, "cmd": ["codex", "exec", "{prompt}"], "note": "codex is down"}},
    )
    jobs._PROCS.clear()
    with jobs._LOCK:
        jobs._promote_queued_locked()

    record = jobs.get_job(queued["id"])
    assert record["status"] == "failed"
    assert "codex is down" in (record.get("error") or "")
    assert procs == []
