"""Local read-only replica: status and on-demand pull.

Only active when the backend was started by run-replica.sh (which exports
FORECAST_REPLICA_MODE=1). The production runner never sets it, so the pull
endpoint does not exist there — and the Sites command whitelist has no action
that could reach it either.

Known limitation (by design): requests racing the atomic replica/current swap
can transiently read a mixed view across two snapshots. The replica is a
disposable mirror; the UI reloads after a completed pull, and job launches are
mutually exclusive with pulls (see start_pull / jobs.start_job).
"""
from __future__ import annotations

import datetime as dt
import json
import os
import signal
import subprocess
import threading
from pathlib import Path

from .config import CONFIG

PROJECT_ROOT = Path(CONFIG["project_root"])
PULL_SCRIPT = PROJECT_ROOT / "deploy" / "forecast_runner" / "pull_and_prune.sh"
_CURRENT_OVERRIDE = os.environ.get("FORECAST_REPLICA_CURRENT")
REPLICA_CURRENT = (
    Path(os.path.abspath(os.path.expanduser(_CURRENT_OVERRIDE)))
    if _CURRENT_OVERRIDE
    else PROJECT_ROOT / "replica" / "current"
)
PULL_TIMEOUT_S = 900
_KILL_GRACE_S = 10

_LOCK = threading.Lock()
_STATE: dict = {"pulling": False, "started_at": None, "finished_at": None, "error": None}


def _now() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def enabled() -> bool:
    return bool(CONFIG.get("replica_mode"))


def is_pulling() -> bool:
    with _LOCK:
        return bool(_STATE["pulling"])


def snapshot_info() -> dict | None:
    """Identity of the snapshot replica/current points at, or None."""
    try:
        manifest = json.loads((REPLICA_CURRENT / "manifest.json").read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    if not isinstance(manifest, dict):
        return None
    return {
        key: manifest.get(key)
        for key in ("snapshot_id", "created_at", "root_commit", "site_commit")
    }


def status() -> dict:
    with _LOCK:
        state = dict(_STATE)
    return {"mode": enabled(), "snapshot": snapshot_info(), **state}


def _tail(text: str, lines: int = 3, limit: int = 300) -> str:
    kept = [line for line in (text or "").strip().splitlines() if line.strip()][-lines:]
    return "\n".join(kept)[:limit]


def _terminate_group(proc: subprocess.Popen) -> None:
    """SIGTERM the whole pull process group (the script's traps clean partial
    state and prevent the snapshot swap), escalate to SIGKILL after a grace."""
    for sig, wait_s in ((signal.SIGTERM, _KILL_GRACE_S), (signal.SIGKILL, 5)):
        try:
            os.killpg(proc.pid, sig)
        except ProcessLookupError:
            return
        try:
            proc.wait(timeout=wait_s)
            return
        except subprocess.TimeoutExpired:
            continue


def _run_pull() -> None:
    error: str | None = None
    try:
        # start_new_session puts the script and every child (pull_replica.sh,
        # ssh, tar) in one process group, so a timeout kills the whole tree
        # instead of orphaning a grandchild that would later swap
        # replica/current behind the state machine's back.
        proc = subprocess.Popen(
            [str(PULL_SCRIPT)],
            cwd=str(PROJECT_ROOT),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            stdin=subprocess.DEVNULL,
            start_new_session=True,
        )
        try:
            stdout, stderr = proc.communicate(timeout=PULL_TIMEOUT_S)
        except subprocess.TimeoutExpired:
            _terminate_group(proc)
            stdout, stderr = proc.communicate()
            error = f"pull exceeded {PULL_TIMEOUT_S}s and was terminated"
        if error is None and proc.returncode != 0:
            error = _tail(stderr) or _tail(stdout) or f"pull exited with code {proc.returncode}"
    except OSError as exc:
        error = str(exc)
    except Exception as exc:  # a stuck 'pulling' flag would block every future pull
        error = f"unexpected pull failure: {exc}"
    finally:
        with _LOCK:
            _STATE.update(pulling=False, finished_at=_now(), error=error)


def start_pull() -> dict:
    """Start a background pull. Raises when unavailable, busy, or unsafe."""
    if not enabled():
        raise PermissionError("replica pulls require replica mode (run-replica.sh)")
    if _CURRENT_OVERRIDE:
        raise PermissionError(
            "FORECAST_REPLICA_CURRENT pins this backend to one snapshot; a pull would not affect it"
        )
    if not PULL_SCRIPT.is_file():
        raise FileNotFoundError(f"pull script is missing: {PULL_SCRIPT}")

    # Arm the pull under jobs._LOCK — the same lock start_job holds while it
    # spawns — so pull-vs-job is fully serialized: whichever enters first, the
    # other sees it and refuses. Lock order is jobs._LOCK -> replica._LOCK on
    # both paths, so there is no deadlock.
    from . import jobs

    with jobs._LOCK:
        if is_pulling():
            raise RuntimeError("a pull is already in progress")
        if jobs.running_jobs():
            raise RuntimeError("a job is running; wait for it so the pull cannot swap data under it")
        with _LOCK:
            _STATE.update(pulling=True, started_at=_now(), finished_at=None, error=None)

    threading.Thread(target=_run_pull, name="replica-pull", daemon=True).start()
    return status()
