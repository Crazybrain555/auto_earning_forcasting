"""Launch, track, and stop project-scoped Codex runs."""
from __future__ import annotations

import datetime as dt
import hashlib
import json
import re
import os
import secrets
import signal
import shutil
import socket
import subprocess
import sys
import threading
import time
from pathlib import Path

from .config import CONFIG
from . import data as run_data
from . import state as ui_state

JOBS_DIR = Path(CONFIG["jobs_dir"])
JOBS_DIR.mkdir(parents=True, exist_ok=True)
PROJECT_ROOT = Path(CONFIG["project_root"])
RUNS_ROOT = Path(CONFIG["runs_root"])

_LOCK = threading.Lock()
_PROCS: dict[str, subprocess.Popen] = {}

HOSTNAME = socket.gethostname()

JOB_TYPES = {"live_forecast", "training_case", "training_round", "plan_round", "suggest_watch"}
ROUND_ID_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9_-]{0,63}")
IDEMPOTENCY_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9._:-]{7,127}")

# Jobs waiting for the runner slot vs. actually occupying it. "queued" is a
# first-class success state (GitHub Actions / Jenkins queue-item model), never
# an error: submits are accepted and promoted FIFO as capacity frees up.
ACTIVE_STATUSES = {"running", "running_detached"}
PENDING_STATUSES = {"queued"} | ACTIVE_STATUSES

# Training-lane jobs mutate shared method state (the skills git checkout,
# round plans, regenerated packages), so they own the whole runner: an
# exclusive job starts only when nothing else runs, and nothing starts
# beside it. Forecast/assistant jobs parallelize up to max_concurrent_jobs,
# with at most one job per case workspace (two agents writing one case dir
# would corrupt it).
EXCLUSIVE_TYPES = {"training_case", "training_round", "plan_round"}


class QueueFullError(Exception):
    """Bounded-queue overflow - a submit-time capacity rejection."""


class CompanyBusyError(Exception):
    """One company, one job: a second forecast/training for a company that
    already has a pending job is rejected outright (never queued behind it) -
    the caller is told to cancel the current job first. Doubles as strong
    mis-click protection: repeat clicks on the same company always bounce."""

    def __init__(self, message: str, existing: dict):
        super().__init__(message)
        self.existing = existing


class RateLimitError(Exception):
    """Submit-rate ceiling - guards against runaway or malicious clicking."""


def _check_round_id(round_id: str, required: bool) -> str:
    round_id = (round_id or "").strip()
    if not round_id:
        if required:
            raise ValueError("params.round_id is required")
        return ""
    if not ROUND_ID_RE.fullmatch(round_id) or round_id == "live":
        raise ValueError("round_id must be alphanumeric/dash/underscore (and not 'live')")
    return round_id


def now() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def engines() -> dict:
    return CONFIG.get("engines", {})


def _claude_token_path() -> Path:
    return Path.home() / ".claude" / "oauth-token"


def _claude_oauth_token() -> str:
    # A 0600 operator-written file (claude setup-token output). Injected only
    # into claude jobs so codex processes never see the subscription token.
    try:
        return _claude_token_path().read_text(encoding="utf-8").strip()
    except OSError:
        return ""


def _claude_login_missing() -> bool:
    # macOS keeps Claude Code credentials in the keychain; Linux runners expose
    # login state as the credentials file or the operator-provided token file.
    if sys.platform == "darwin":
        return False
    if (Path.home() / ".claude" / ".credentials.json").is_file():
        return False
    return not _claude_oauth_token()


def engine_status() -> list[dict]:
    status = []
    for name, spec in engines().items():
        command = str((spec.get("cmd") or [name])[0])
        installed = bool(shutil.which(command))
        configured = bool(spec.get("available"))
        note = spec.get("note", "")
        if configured and not installed:
            note = f"{command} is not installed on this runner."
        available = configured and installed
        if available and name == "claude" and _claude_login_missing():
            available = False
            note = "claude is not logged in on this runner (run: claude setup-token)."
        status.append({
            "engine": name,
            "available": available,
            "note": note,
            "default_model": spec.get("default_model"),
            "models": spec.get("models") or [],
        })
    return status


def _record_path(job_id: str) -> Path:
    return JOBS_DIR / f"{job_id}.json"


def _log_path(job_id: str) -> Path:
    return JOBS_DIR / f"{job_id}.log"


def _save(record: dict) -> None:
    _record_path(record["id"]).write_text(
        json.dumps(record, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )


def _load(job_id: str) -> dict | None:
    path = _record_path(job_id)
    if not path.is_file():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def build_prompt(job_type: str, params: dict) -> tuple[str, dict]:
    """Return (prompt, normalized_params). Raises ValueError on bad input."""
    prompts = CONFIG.get("prompts", {})
    template = prompts.get(job_type)
    if not template:
        raise ValueError(f"no prompt template configured for job type {job_type}")

    entity = (params.get("entity") or "").strip()
    security = (params.get("security") or entity).strip()
    if job_type in {"live_forecast", "training_case"} and not entity:
        raise ValueError("params.entity is required")

    if job_type == "live_forecast":
        as_of = (params.get("as_of") or dt.date.today().isoformat()).strip()
        round_id = "live"
        case_id = f"{security}@{as_of}"
    elif job_type == "training_case":
        as_of = (params.get("as_of") or "").strip()
        round_id = _check_round_id(params.get("round_id"), required=True)
        case_role = (params.get("case_role") or "").strip()
        if not as_of:
            raise ValueError("params.as_of is required")
        if case_role not in {"development", "validation", "regression"}:
            raise ValueError("params.case_role must be development|validation|regression")
        case_id = f"{security}@{as_of}"
    elif job_type == "training_round":
        round_id = _check_round_id(params.get("round_id"), required=True)
        # Groups come either fully inline or from the saved round plan. The
        # shared normalizer is the single contract for planner and runner.
        saved_plan = None
        if "group_a" not in params and "group_b" not in params:
            plan_path = RUNS_ROOT / round_id / "round.json"
            if not plan_path.is_file():
                raise ValueError("params.group_a and params.group_b are required inline or in the saved round plan")
            try:
                saved_plan = json.loads(plan_path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError) as exc:
                raise ValueError(f"saved round plan is unreadable: {exc}") from exc
            params = {
                **params,
                "group_a": saved_plan.get("group_a"),
                "group_b": saved_plan.get("group_b"),
            }
        plan_a, plan_b = run_data.normalize_round_groups(
            params.get("group_a"), params.get("group_b"), saved_plan
        )
        params = {**params, "group_a": plan_a, "group_b": plan_b}
        as_of, case_id, case_role = "", "", ""
    elif job_type == "suggest_watch":  # assistant: recommend watchlist candidates, no forecasting
        round_id, as_of, case_id, case_role = "", "", "", ""
    else:  # plan_round: agent arranges the next round from the curriculum
        round_id = _check_round_id(params.get("round_id"), required=False)
        as_of, case_id, case_role = "", "", ""

    workspace = RUNS_ROOT / round_id / case_id if case_id else RUNS_ROOT / round_id
    fields = {
        "entity": entity,
        "security": security,
        "as_of": as_of,
        "round_id": round_id,
        "case_id": case_id,
        "case_role": params.get("case_role", ""),
        "workspace": str(workspace),
        "runs_root": str(RUNS_ROOT),
        "group_a": json.dumps(params.get("group_a", []), ensure_ascii=False),
        "group_b": json.dumps(params.get("group_b", []), ensure_ascii=False),
        "extra": (params.get("extra") or "").strip(),
        "hint": (params.get("hint") or "").strip(),
        "watchlist": json.dumps(
            [{"entity": i.get("entity"), "security": i.get("security")} for i in ui_state.load_watchlist()],
            ensure_ascii=False),
        "suggestions_path": str(ui_state.SUGGESTIONS_PATH),
    }
    prompt = template.format(**fields)
    normalized = {**params, "round_id": round_id, "case_id": case_id, "workspace": str(workspace)}
    return prompt, normalized


def compose_cmd(spec: dict, prompt: str, params: dict) -> list[str]:
    """Engine cmd with optional model/effort overrides from params.

    Overrides are validated against the engine's model registry and spliced in
    BEFORE the prompt argument (codex exec wants options before the positional).
    Absent overrides FALL BACK to the engine's default_model/default_effort so
    every job runs an explicitly chosen tier - never the CLI's ambient default
    (which once silently dropped a forecast onto haiku).
    """
    registry = {m.get("id"): m for m in spec.get("models") or []}
    model = (params.get("model") or "").strip() or str(spec.get("default_model") or "")
    effort = (params.get("effort") or "").strip() \
        or str((registry.get(model) or {}).get("default_effort") or spec.get("default_effort") or "")
    extra: list[str] = []
    if model or effort:
        if model:
            if registry and model not in registry:
                raise ValueError(f"unknown model {model} for this engine (choose from {sorted(registry)})")
            extra += [str(a).replace("{model}", model) for a in spec.get("model_args") or []]
        if effort:
            allowed = (registry.get(model or spec.get("default_model")) or {}).get("efforts")
            if allowed and effort not in allowed:
                raise ValueError(f"effort {effort} not supported by {model or spec.get('default_model')} (choose from {allowed})")
            extra += [str(a).replace("{effort}", effort) for a in spec.get("effort_args") or []]
    cmd: list[str] = []
    for part in spec["cmd"]:
        part = str(part)
        if "{prompt}" in part and extra:
            cmd += extra
            extra = []
        cmd.append(part.replace("{prompt}", prompt))
    return cmd + extra


def _request_fingerprint(job_type: str, engine: str, params: dict) -> str:
    payload = json.dumps(
        {"type": job_type, "engine": engine, "params": params},
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _all_records() -> list[dict]:
    records = []
    for path in JOBS_DIR.glob("*.json"):
        try:
            record = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            continue
        if isinstance(record, dict) and record.get("id"):
            records.append(record)
    return records


def _find_idempotent_job(key: str) -> dict | None:
    for record in _all_records():
        if record.get("idempotency_key") == key or key in (record.get("idempotency_aliases") or []):
            return record
    return None


def _concurrency_limit() -> int:
    try:
        return max(1, int(CONFIG.get("max_concurrent_jobs", 1)))
    except (TypeError, ValueError):
        return 1


def _queue_limit() -> int:
    try:
        return max(1, int(CONFIG.get("max_queued_jobs", 20)))
    except (TypeError, ValueError):
        return 20


def _rate_limit() -> tuple[int, int]:
    """(max submits, window seconds); either <= 0 disables the limiter."""
    try:
        max_submits = int(CONFIG.get("submit_rate_max", 20))
    except (TypeError, ValueError):
        max_submits = 20
    try:
        window_s = int(CONFIG.get("submit_rate_window_s", 60))
    except (TypeError, ValueError):
        window_s = 60
    return max_submits, window_s


def _submit_rate_exceeded_locked() -> int:
    """Seconds to wait when the submit-rate ceiling is hit, else 0.

    Counts locally created records inside the window - a durable sliding
    window that survives restarts and also catches submit-cancel churn
    (cancelled records still count until they age out). Idempotent replays and
    dedup hits never reach this check, so honest retries are not punished.
    """
    max_submits, window_s = _rate_limit()
    if max_submits <= 0 or window_s <= 0:
        return 0
    cutoff = dt.datetime.now(dt.timezone.utc) - dt.timedelta(seconds=window_s)
    recent = 0
    for record in _all_records():
        if _foreign(record):
            continue
        stamp = record.get("created_at") or record.get("started_at") or ""
        try:
            created = dt.datetime.fromisoformat(stamp)
        except (TypeError, ValueError):
            continue
        if created >= cutoff:
            recent += 1
    return window_s if recent >= max_submits else 0


def capacity() -> dict:
    """Queue/runner limits for dashboards; safe to publish."""
    max_submits, window_s = _rate_limit()
    return {
        "max_concurrent_jobs": _concurrency_limit(),
        "max_queued_jobs": _queue_limit(),
        "submit_rate_max": max_submits,
        "submit_rate_window_s": window_s,
    }


def _managed_running_count() -> int:
    return sum(1 for proc in _PROCS.values() if proc.poll() is None)


def _active_jobs_locked() -> list[dict]:
    """Records occupying runner slots, from durable state - not just this
    process's children. Counting only _PROCS silently fails open after a
    backend restart: a still-running detached agent would be invisible and a
    second job would spawn beside it. Foreign (replica-pulled) records never
    occupy local slots.
    """
    active: list[dict] = []
    seen: set[str] = set()
    for job_id, proc in list(_PROCS.items()):
        seen.add(job_id)
        if proc.poll() is None:
            # A live child ALWAYS occupies a slot, even if its record file is
            # momentarily unreadable - failing open here would over-spawn.
            record = _load(job_id)
            active.append(record if record is not None
                          else {"id": job_id, "status": "running", "type": "", "params": {}})
    for record in _all_records():
        if record["id"] in seen or _foreign(record):
            continue
        if record.get("status") in ACTIVE_STATUSES and _refresh(record, ingest=False).get("status") in ACTIVE_STATUSES:
            active.append(record)
    return active


def _workspace_of(record: dict) -> str:
    return str((record.get("params") or {}).get("workspace") or "")


def _foreign(record: dict) -> bool:
    """True for job records this machine must never signal or reconcile.

    A replica pull copies the production runner's job records here; their pids
    belong to the runner's pid space, so probing or killing them would hit
    unrelated local processes. Only enforced in replica mode: legacy local
    records predate the host field and stay fully owned in normal mode.
    """
    if not CONFIG.get("replica_mode"):
        return False
    return record.get("host") != HOSTNAME


def _job_env(engine: str, spec: dict) -> dict:
    env = dict(os.environ)
    env.update(spec.get("env") or {})
    if engine == "claude":
        token = _claude_oauth_token()
        if token:
            env.setdefault("CLAUDE_CODE_OAUTH_TOKEN", token)
    return env


def _fifo_key(record: dict) -> tuple[str, str]:
    """Submission order. Job ids only resolve to the second, so rapid submits
    would tie and the random suffix would shuffle them; created_at carries
    microseconds. Pre-queue records without created_at sort by id."""
    return (record.get("created_at") or record["id"], record["id"])


def _queued_locked() -> list[dict]:
    """Local queued records in FIFO order."""
    return sorted(
        (r for r in _all_records() if r.get("status") == "queued" and not _foreign(r)),
        key=_fifo_key,
    )


def _queued_position(job_id: str) -> int | None:
    """1-based FIFO position among local queued jobs."""
    for index, record in enumerate(_queued_locked()):
        if record["id"] == job_id:
            return index + 1
    return None


def _with_queue_position(record: dict) -> dict:
    """Annotate a COPY with its live queue position; never saved to disk."""
    out = dict(record)
    if out.get("status") == "queued":
        out["queue_position"] = _queued_position(out["id"])
    return out


def _mark_failed_locked(record: dict, error: str) -> None:
    record["status"] = "failed"
    record["error"] = str(error)[:500]
    record["ended_at"] = now()
    _save(record)
    try:
        with _log_path(record["id"]).open("a", encoding="utf-8") as handle:
            handle.write(f"\n# launch failed: {record['error']}\n")
    except OSError:
        pass


def _reap(job_id: str, proc: subprocess.Popen, log_handle) -> None:
    returncode = proc.wait()
    log_handle.close()
    try:  # capture the delivered version into the durable store right away
        from . import data as _data, db as _db
        _db.scan(_data.list_cases, _data.read_json, _data.normalize_outputs, force=True)
    except Exception:
        pass
    usage = _parse_result_json(_log_path(job_id))
    with _LOCK:
        current = _load(job_id) or {"id": job_id, "status": "running"}
        if current.get("status") == "running":
            current["status"] = "finished" if returncode == 0 else "failed"
        current["returncode"] = returncode
        current["ended_at"] = now()
        if usage:
            current.update(usage)
        _save(current)
        _PROCS.pop(job_id, None)
        _promote_queued_locked()   # the freed slot immediately pulls the next queued job


def _try_spawn_locked(record: dict) -> bool:
    """Promote one queued record to running. Called under _LOCK.

    Failures (engine gone, binary missing, bad model override after a config
    change) mark the record failed with the reason instead of retrying forever,
    then let the caller move on to the next queued job.
    """
    spec = engines().get(record.get("engine"))
    if spec is None or not spec.get("available"):
        _mark_failed_locked(record, (spec or {}).get("note") or f"engine {record.get('engine')} is not available")
        return False
    try:
        cmd = compose_cmd(spec, record["prompt"], record.get("params") or {})
    except (ValueError, KeyError) as exc:
        _mark_failed_locked(record, f"cannot compose engine command: {exc}")
        return False
    try:
        log_handle = _log_path(record["id"]).open("a", encoding="utf-8")
    except OSError as exc:
        _mark_failed_locked(record, f"cannot open job log: {exc}")
        return False
    try:
        proc = subprocess.Popen(
            cmd,
            cwd=str(PROJECT_ROOT),
            env=_job_env(record["engine"], spec),
            stdin=subprocess.DEVNULL,   # codex exec reads stdin when it is a pipe and blocks forever
            stdout=log_handle,
            stderr=subprocess.STDOUT,
            start_new_session=True,
        )
    except Exception as exc:
        log_handle.close()
        _mark_failed_locked(record, str(exc))
        return False

    record["pid"] = proc.pid
    record["status"] = "running"
    record["started_at"] = now()
    record["error"] = None
    _PROCS[record["id"]] = proc
    _save(record)
    threading.Thread(target=_reap, args=(record["id"], proc, log_handle), daemon=True).start()
    return True


def _promote_queued_locked() -> None:
    """Fill free runner slots from the FIFO queue. Called under _LOCK.

    Scheduling rules, in order:
    - nothing promotes during a replica pull (same exclusion start_pull arms
      under this lock) and foreign records are never touched;
    - while an EXCLUSIVE (training-lane) job runs, nothing else starts;
    - an exclusive job at the queue head drains the runner first: it waits for
      active jobs to finish and blocks later jobs from jumping it, then runs
      alone;
    - other jobs start FIFO up to max_concurrent_jobs, except that a job whose
      case workspace is already being written by an active job stays queued
      (later jobs with free workspaces may pass it - no starvation: it starts
      when its case frees).
    """
    from . import replica
    if replica.is_pulling():
        return
    limit = _concurrency_limit()
    active = _active_jobs_locked()
    if any(r.get("type") in EXCLUSIVE_TYPES for r in active):
        return
    busy_workspaces = {ws for ws in (_workspace_of(r) for r in active) if ws}
    for record in _queued_locked():
        if record.get("type") in EXCLUSIVE_TYPES:
            if active:
                return                      # drain, and let nothing jump the queue
            if _try_spawn_locked(record):
                return                      # exclusive job runs alone
            continue                        # marked failed; consider the next job
        if len(active) >= limit:
            return
        workspace = _workspace_of(record)
        if workspace and workspace in busy_workspaces:
            continue                        # its case is busy; it waits, others may pass
        if _try_spawn_locked(record):
            active.append(record)
            if workspace:
                busy_workspaces.add(workspace)


def start_job(job_type: str, engine: str, params: dict, idempotency_key: str = "") -> dict:
    from . import replica
    if job_type not in JOB_TYPES:
        raise ValueError(f"job type must be one of {sorted(JOB_TYPES)}")
    spec = engines().get(engine)
    if spec is None:
        raise ValueError(f"unknown engine {engine}")
    if not spec.get("available"):
        raise PermissionError(spec.get("note") or f"engine {engine} is not available yet")

    idempotency_key = (idempotency_key or "").strip()
    if idempotency_key and not IDEMPOTENCY_RE.fullmatch(idempotency_key):
        raise ValueError("Idempotency-Key must be 8-128 safe characters")

    prompt, normalized = build_prompt(job_type, params)
    compose_cmd(spec, prompt, params)   # validate model/effort overrides before accepting
    fingerprint = _request_fingerprint(job_type, engine, normalized)

    with _LOCK:
        # Same lock replica.start_pull holds while arming a pull, so a job can
        # never spawn while a pull swaps replica/current (and vice versa).
        if replica.is_pulling():
            raise RuntimeError("a replica pull is in progress; start the job after it finishes")
        if idempotency_key:
            existing = _find_idempotent_job(idempotency_key)
            if existing is not None:
                if existing.get("idempotency_fingerprint") != fingerprint:
                    raise ValueError("Idempotency-Key was already used for a different job request")
                return _with_queue_position(existing)

        # One company, one job (user rule): a forecast or per-company training
        # submit for a company that already has a queued/running job is
        # REJECTED - not queued, not merged - and the caller is pointed at the
        # existing job so they can cancel it and resubmit. Company identity is
        # the normalized security symbol.
        if job_type in {"live_forecast", "training_case"}:
            company = run_data._sec_key(normalized.get("security") or normalized.get("entity"))
            if company:
                for candidate in _all_records():
                    if _foreign(candidate) or candidate.get("status") not in PENDING_STATUSES:
                        continue
                    cand_params = candidate.get("params") or {}
                    if run_data._sec_key(cand_params.get("security") or cand_params.get("entity")) != company:
                        continue
                    refreshed = _refresh(candidate, ingest=False)
                    if refreshed.get("status") in PENDING_STATUSES:
                        state_label = "queued" if refreshed.get("status") == "queued" else "running"
                        raise CompanyBusyError(
                            f"company busy: {company} already has a {refreshed.get('type')} job "
                            f"(job {refreshed['id']}, {state_label}); cancel it first to rerun",
                            {"id": refreshed["id"], "status": refreshed.get("status"),
                             "type": refreshed.get("type")},
                        )

        # Active-set dedup: an identical request (same type/engine/params) that
        # is already waiting or running is returned instead of stacked - rapid
        # multi-clicks and transport retries collapse into one job. Uniqueness
        # lapses once the earlier job reaches a terminal state.
        for candidate in _all_records():
            if _foreign(candidate) or candidate.get("status") not in PENDING_STATUSES:
                continue
            if candidate.get("idempotency_fingerprint") != fingerprint:
                continue
            refreshed = _refresh(candidate, ingest=False)
            if refreshed.get("status") in PENDING_STATUSES:
                # Record the caller's idempotency key as an alias so a later
                # replay of the SAME command (bridge lease retry) still maps
                # to this job even after it reaches a terminal state -
                # otherwise the retry would start a duplicate paid run.
                if idempotency_key and idempotency_key != refreshed.get("idempotency_key"):
                    aliases = refreshed.get("idempotency_aliases") or []
                    if idempotency_key not in aliases and len(aliases) < 64:
                        refreshed["idempotency_aliases"] = aliases + [idempotency_key]
                        _save(refreshed)
                out = _with_queue_position(refreshed)
                out["deduplicated"] = True
                return out

        retry_after = _submit_rate_exceeded_locked()
        if retry_after:
            max_submits, window_s = _rate_limit()
            raise RateLimitError(
                f"too many job submissions ({max_submits} in {window_s}s); wait a moment and retry"
            )

        queued_count = sum(
            1 for r in _all_records()
            if r.get("status") == "queued" and not _foreign(r)
        )
        if queued_count >= _queue_limit():
            raise QueueFullError(
                f"job queue is full ({queued_count} waiting); cancel a queued job or try again later"
            )

        job_id = dt.datetime.now().strftime("%Y%m%d-%H%M%S") + "-" + secrets.token_hex(2)
        with _log_path(job_id).open("w", encoding="utf-8") as log_handle:
            log_handle.write(f"# job {job_id} | {job_type} | engine={engine}\n# prompt:\n{prompt}\n\n")

        record = {
            "id": job_id,
            "type": job_type,
            "engine": engine,
            "host": HOSTNAME,
            "params": normalized,
            "prompt": prompt,
            "pid": None,
            "status": "queued",
            "created_at": now(),
            "started_at": None,
            "ended_at": None,
            "returncode": None,
            "error": None,
            "log": str(_log_path(job_id)),
            "idempotency_key": idempotency_key or None,
            "idempotency_fingerprint": fingerprint,
        }
        _save(record)
        # Promote immediately: with a free slot the new job starts right away
        # (status comes back "running"); otherwise it stays queued and later
        # promotions (reap / scheduler tick) pick it up FIFO.
        _promote_queued_locked()
        return _with_queue_position(_load(job_id) or record)


def _parse_result_json(log_path: Path) -> dict | None:
    """With --output-format json the engine's stdout ends in one JSON object;
    extract cost/usage/result. Tolerant: plain-text logs return None."""
    try:
        text = log_path.read_text(encoding="utf-8", errors="replace")
        start = text.rfind("\n{")
        if start < 0:
            return None
        payload = json.loads(text[start + 1:])
        usage = payload.get("usage") or {}
        out = {
            "cost_usd": payload.get("total_cost_usd"),
            "engine_duration_ms": payload.get("duration_ms"),
            "tokens_out": usage.get("output_tokens"),
            "result_summary": str(payload.get("result", ""))[:600],
        }
        # append readable result to the log for the dashboard log viewer
        with log_path.open("a", encoding="utf-8") as handle:
            handle.write("\n# result summary:\n" + str(payload.get("result", ""))[:2000] + "\n")
        return out
    except Exception:
        return None


def stop_job(job_id: str) -> dict | None:
    record = _load(job_id)
    if record is None:
        return None
    if _foreign(record):
        raise PermissionError(
            "this job record came from the production runner; it cannot be stopped from the replica"
        )
    if record.get("status") == "queued":
        # Cancelling a queued job is a cheap dequeue: no process ever started,
        # so there is nothing to signal and no capacity to release.
        with _LOCK:
            current = _load(job_id) or record
            if current.get("status") == "queued":
                current["status"] = "stopped"
                current["ended_at"] = now()
                _save(current)
                return current
            record = current
    with _LOCK:
        proc = _PROCS.get(job_id)
    if proc is not None and proc.poll() is None:
        try:
            os.killpg(os.getpgid(proc.pid), signal.SIGTERM)
        except ProcessLookupError:
            pass
        # Re-load and save under _LOCK: _reap may have already written the
        # terminal record (returncode/usage) between the kill and this save -
        # overwriting it with the pre-kill snapshot would lose that data.
        with _LOCK:
            current = _load(job_id) or record
            if current.get("status") in PENDING_STATUSES:
                current["status"] = "stopped"
            current["ended_at"] = current.get("ended_at") or now()
            _save(current)
            return current
    # Not our child (backend restarted): verify the pid still looks like ours
    # before signalling - pids get recycled.
    if record.get("status") in {"running", "running_detached"} and record.get("pid"):
        probe = subprocess.run(["ps", "-p", str(record["pid"]), "-o", "command="],
                                capture_output=True, text=True)
        command = probe.stdout.strip()
        engine_cmd = (engines().get(record.get("engine"), {}).get("cmd") or [""])[0]
        if not command:
            record["status"] = "interrupted"
        elif engine_cmd and engine_cmd.split("/")[-1] not in command:
            record["status"] = "interrupted"  # pid recycled by an unrelated process; do not signal
        else:
            try:
                os.killpg(os.getpgid(record["pid"]), signal.SIGTERM)
                record["status"] = "stopped"
            except ProcessLookupError:
                record["status"] = "interrupted"
        record["ended_at"] = now()
        _save(record)
    return record


def delete_job(job_id: str) -> bool:
    """Soft-remove a job record + log into jobs/_trash.

    Refused for running AND queued records - a queued record passing the old
    guard could be promoted by the scheduler between the check and the rename,
    leaving an unmanaged child whose record just vanished. Cancel queued jobs
    through stop_job first. Check + move happen under _LOCK so promotion can
    never interleave.
    """
    with _LOCK:
        record = _load(job_id)
        if record is None:
            return False
        proc = _PROCS.get(job_id)
        if record.get("status") == "queued":
            raise PermissionError("job is queued; cancel it (stop) before deleting the record")
        if (proc is not None and proc.poll() is None) or _refresh(dict(record)).get("status") in ACTIVE_STATUSES:
            raise PermissionError("job is running; stop it first")
        trash = JOBS_DIR / "_trash"
        trash.mkdir(exist_ok=True)
        for path in (_record_path(job_id), _log_path(job_id)):
            if path.is_file():
                path.rename(trash / path.name)
    return True


def _refresh(record: dict, ingest: bool = True) -> dict:
    """Reconcile records that predate this backend process.

    running/running_detached records without a live managed process are
    re-checked every listing: pid alive (and still our engine binary - pids
    recycle) -> running_detached; pid gone -> finished when the log tail shows
    a normal completion, else interrupted. Completed detached work is ingested
    into the durable store immediately - except with ingest=False, used by
    paths that hold _LOCK (a full runs-tree db.scan under the job lock would
    stall every submit/stop for seconds; the next unlocked listing ingests).
    """
    status = record.get("status")
    if status not in {"running", "running_detached"} or record["id"] in _PROCS:
        return record
    if _foreign(record):
        return record  # production pids mean nothing here; show what the pull captured
    pid = record.get("pid")
    alive = False
    if pid:
        probe = subprocess.run(["ps", "-p", str(pid), "-o", "command="],
                                capture_output=True, text=True)
        command = probe.stdout.strip()
        engine_cmd = (engines().get(record.get("engine"), {}).get("cmd") or [""])[0]
        alive = bool(command) and (not engine_cmd or engine_cmd.split("/")[-1] in command)
    if alive:
        if status != "running_detached":
            record["status"] = "running_detached"
            _save(record)
        return record
    tail = ""
    try:
        with open(_log_path(record["id"]), "rb") as fh:
            fh.seek(0, 2)
            size = fh.tell()
            fh.seek(max(0, size - 8192))
            tail = fh.read().decode("utf-8", "replace")
    except OSError:
        pass
    ok_markers = ('"subtype":"success"', '"subtype": "success"', "tokens used")
    record["status"] = "finished" if any(m in tail for m in ok_markers) else "interrupted"
    record["ended_at"] = record.get("ended_at") or now()
    _save(record)
    if ingest:
        try:  # capture whatever the detached run delivered
            from . import data as _data, db as _db
            _db.scan(_data.list_cases, _data.read_json, _data.normalize_outputs, force=True)
        except Exception:
            pass
    return record


def list_jobs() -> list[dict]:
    records = []
    for path in sorted(JOBS_DIR.glob("*.json"), reverse=True):
        try:
            records.append(_refresh(json.loads(path.read_text(encoding="utf-8"))))
        except Exception:
            continue
    order = sorted(
        (r for r in records if r.get("status") == "queued" and not _foreign(r)),
        key=_fifo_key,
    )
    positions = {record["id"]: index + 1 for index, record in enumerate(order)}
    return [
        {**r, "queue_position": positions[r["id"]]} if r["id"] in positions else r
        for r in records
    ]


def get_job(job_id: str) -> dict | None:
    record = _load(job_id)
    if record is None:
        return None
    return _with_queue_position(_refresh(record))


def job_log(job_id: str, tail: int = 200, safe: bool = False) -> str | None:
    path = _log_path(job_id)
    if not path.is_file():
        return None
    text = path.read_text(encoding="utf-8", errors="replace")
    if safe:
        record = _load(job_id)
        prompt = record.get("prompt") if isinstance(record, dict) else None
        if not isinstance(prompt, str):
            return None
        marker = f"\n# prompt:\n{prompt}\n\n"
        marker_at = text.find(marker)
        if marker_at < 0:
            # Never return an uncertain prefix to a remote synchronizer.
            return None
        text = text[marker_at + len(marker):]
    lines = text.splitlines()
    return "\n".join(lines[-tail:])


def running_jobs() -> list[dict]:
    return [r for r in list_jobs() if r["status"] in ACTIVE_STATUSES]


def queued_jobs() -> list[dict]:
    return [r for r in list_jobs() if r["status"] == "queued" and not _foreign(r)]


_SCHEDULER_STARTED = False


def start_scheduler(interval_s: float = 7.0) -> None:
    """Background promotion tick, started once from the API startup hook.

    Completion of a managed job already promotes inline (_reap); the tick
    covers the edges reap cannot see: queued records surviving a backend
    restart, detached jobs finishing, and a replica pull ending.
    """
    global _SCHEDULER_STARTED
    if _SCHEDULER_STARTED:
        return
    _SCHEDULER_STARTED = True

    def tick() -> None:
        while True:
            try:
                with _LOCK:
                    _promote_queued_locked()
            except Exception:
                pass
            time.sleep(interval_s)

    threading.Thread(target=tick, name="job-queue-scheduler", daemon=True).start()
