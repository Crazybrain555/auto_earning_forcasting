"""Job manager: launch, track, and stop agent runs.

An engine is a headless agent CLI. `claude` is live today (skills auto-load
from .claude/skills and the project CLAUDE.md supplies the operating notes).
`codex` is a reserved slot: it stays available=false in config.json until the
Codex skill port is finalized, then flipping it on (plus its proxy env) is the
only change needed — job types, prompts, and the API do not change.
"""
from __future__ import annotations

import datetime as dt
import json
import re
import os
import secrets
import signal
import subprocess
import threading
from pathlib import Path

from .config import CONFIG

JOBS_DIR = Path(CONFIG["jobs_dir"])
JOBS_DIR.mkdir(parents=True, exist_ok=True)
PROJECT_ROOT = Path(CONFIG["project_root"])
RUNS_ROOT = Path(CONFIG["runs_root"])

_LOCK = threading.Lock()
_PROCS: dict[str, subprocess.Popen] = {}

JOB_TYPES = {"live_forecast", "training_case", "training_round", "plan_round"}
ROUND_ID_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9_-]{0,63}")


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


def engine_status() -> list[dict]:
    return [
        {"engine": name, "available": bool(spec.get("available")), "note": spec.get("note", "")}
        for name, spec in engines().items()
    ]


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
        # groups may come inline or from a saved round plan (round.json)
        if not params.get("group_a") or not params.get("group_b"):
            plan_path = RUNS_ROOT / round_id / "round.json"
            if plan_path.is_file():
                plan = json.loads(plan_path.read_text(encoding="utf-8"))
                params = {**params, "group_a": plan.get("group_a"), "group_b": plan.get("group_b")}
        for group in ("group_a", "group_b"):
            if not isinstance(params.get(group), list) or len(params[group]) != 2:
                raise ValueError(f"params.{group} must have exactly 2 companies (2+2 round; inline or in the round plan)")
        as_of, case_id, case_role = "", "", ""
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
    }
    prompt = template.format(**fields)
    normalized = {**params, "round_id": round_id, "case_id": case_id, "workspace": str(workspace)}
    return prompt, normalized


def start_job(job_type: str, engine: str, params: dict) -> dict:
    if job_type not in JOB_TYPES:
        raise ValueError(f"job type must be one of {sorted(JOB_TYPES)}")
    spec = engines().get(engine)
    if spec is None:
        raise ValueError(f"unknown engine {engine}")
    if not spec.get("available"):
        raise PermissionError(spec.get("note") or f"engine {engine} is not available yet")

    prompt, normalized = build_prompt(job_type, params)
    cmd = [str(part).replace("{prompt}", prompt) for part in spec["cmd"]]
    job_id = dt.datetime.now().strftime("%Y%m%d-%H%M%S") + "-" + secrets.token_hex(2)

    env = dict(os.environ)
    env.update(spec.get("env") or {})
    log_handle = _log_path(job_id).open("w", encoding="utf-8")
    log_handle.write(f"# job {job_id} | {job_type} | engine={engine}\n# prompt:\n{prompt}\n\n")
    log_handle.flush()

    proc = subprocess.Popen(
        cmd,
        cwd=str(PROJECT_ROOT),
        env=env,
        stdout=log_handle,
        stderr=subprocess.STDOUT,
        start_new_session=True,
    )

    record = {
        "id": job_id,
        "type": job_type,
        "engine": engine,
        "params": normalized,
        "prompt": prompt,
        "pid": proc.pid,
        "status": "running",
        "started_at": now(),
        "ended_at": None,
        "returncode": None,
        "log": str(_log_path(job_id)),
    }
    with _LOCK:
        _PROCS[job_id] = proc
        _save(record)

    def reap() -> None:
        returncode = proc.wait()
        log_handle.close()
        with _LOCK:
            current = _load(job_id) or record
            if current["status"] == "running":
                current["status"] = "finished" if returncode == 0 else "failed"
            current["returncode"] = returncode
            current["ended_at"] = now()
            _save(current)
            _PROCS.pop(job_id, None)

    threading.Thread(target=reap, daemon=True).start()
    return record


def stop_job(job_id: str) -> dict | None:
    record = _load(job_id)
    if record is None:
        return None
    with _LOCK:
        proc = _PROCS.get(job_id)
    if proc is not None and proc.poll() is None:
        try:
            os.killpg(os.getpgid(proc.pid), signal.SIGTERM)
        except ProcessLookupError:
            pass
        record["status"] = "stopped"
        record["ended_at"] = now()
        _save(record)
        return record
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
    """Soft-remove a job record + log into jobs/_trash. Refused while running."""
    record = _load(job_id)
    if record is None:
        return False
    with _LOCK:
        proc = _PROCS.get(job_id)
    if (proc is not None and proc.poll() is None) or _refresh(dict(record)).get("status") in {"running", "running_detached"}:
        raise PermissionError("job is running; stop it first")
    trash = JOBS_DIR / "_trash"
    trash.mkdir(exist_ok=True)
    for path in (_record_path(job_id), _log_path(job_id)):
        if path.is_file():
            path.rename(trash / path.name)
    return True


def _refresh(record: dict) -> dict:
    """Reconcile records that predate this backend process."""
    if record.get("status") == "running" and record["id"] not in _PROCS:
        pid = record.get("pid")
        alive = False
        if pid:
            try:
                os.kill(pid, 0)
                alive = True
            except (ProcessLookupError, PermissionError):
                alive = False
        record["status"] = "running_detached" if alive else "interrupted"
        _save(record)
    return record


def list_jobs() -> list[dict]:
    records = []
    for path in sorted(JOBS_DIR.glob("*.json"), reverse=True):
        try:
            records.append(_refresh(json.loads(path.read_text(encoding="utf-8"))))
        except Exception:
            continue
    return records


def get_job(job_id: str) -> dict | None:
    record = _load(job_id)
    return _refresh(record) if record else None


def job_log(job_id: str, tail: int = 200) -> str | None:
    path = _log_path(job_id)
    if not path.is_file():
        return None
    lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    return "\n".join(lines[-tail:])


def running_jobs() -> list[dict]:
    return [r for r in list_jobs() if r["status"] in {"running", "running_detached"}]
