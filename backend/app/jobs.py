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
import subprocess
import sys
import threading
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

JOB_TYPES = {"live_forecast", "training_case", "training_round", "plan_round", "suggest_watch"}
ROUND_ID_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9_-]{0,63}")
IDEMPOTENCY_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9._:-]{7,127}")


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


def _find_idempotent_job(key: str) -> dict | None:
    for path in JOBS_DIR.glob("*.json"):
        try:
            record = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            continue
        if record.get("idempotency_key") == key:
            return record
    return None


def _concurrency_limit() -> int:
    try:
        return max(1, int(CONFIG.get("max_concurrent_jobs", 1)))
    except (TypeError, ValueError):
        return 1


def _managed_running_count() -> int:
    return sum(1 for proc in _PROCS.values() if proc.poll() is None)


def start_job(job_type: str, engine: str, params: dict, idempotency_key: str = "") -> dict:
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
    cmd = compose_cmd(spec, prompt, params)
    fingerprint = _request_fingerprint(job_type, engine, normalized)

    env = dict(os.environ)
    env.update(spec.get("env") or {})
    if engine == "claude":
        token = _claude_oauth_token()
        if token:
            env.setdefault("CLAUDE_CODE_OAUTH_TOKEN", token)
    with _LOCK:
        if idempotency_key:
            existing = _find_idempotent_job(idempotency_key)
            if existing is not None:
                if existing.get("idempotency_fingerprint") != fingerprint:
                    raise ValueError("Idempotency-Key was already used for a different job request")
                return existing

        if _managed_running_count() >= _concurrency_limit():
            raise PermissionError("runner capacity is full; wait for the active job to finish")

        job_id = dt.datetime.now().strftime("%Y%m%d-%H%M%S") + "-" + secrets.token_hex(2)
        log_handle = _log_path(job_id).open("w", encoding="utf-8")
        log_handle.write(f"# job {job_id} | {job_type} | engine={engine}\n# prompt:\n{prompt}\n\n")
        log_handle.flush()

        try:
            proc = subprocess.Popen(
                cmd,
                cwd=str(PROJECT_ROOT),
                env=env,
                stdin=subprocess.DEVNULL,   # codex exec reads stdin when it is a pipe and blocks forever
                stdout=log_handle,
                stderr=subprocess.STDOUT,
                start_new_session=True,
            )
        except Exception:
            log_handle.close()
            _log_path(job_id).unlink(missing_ok=True)
            raise

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
            "idempotency_key": idempotency_key or None,
            "idempotency_fingerprint": fingerprint if idempotency_key else None,
        }
        _PROCS[job_id] = proc
        _save(record)

    def reap() -> None:
        returncode = proc.wait()
        log_handle.close()
        try:  # capture the delivered version into the durable store right away
            from . import data as _data, db as _db
            _db.scan(_data.list_cases, _data.read_json, _data.normalize_outputs, force=True)
        except Exception:
            pass
        usage = _parse_result_json(_log_path(job_id))
        with _LOCK:
            current = _load(job_id) or record
            if current["status"] == "running":
                current["status"] = "finished" if returncode == 0 else "failed"
            current["returncode"] = returncode
            current["ended_at"] = now()
            if usage:
                current.update(usage)
            _save(current)
            _PROCS.pop(job_id, None)

    threading.Thread(target=reap, daemon=True).start()
    return record


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
    """Reconcile records that predate this backend process.

    running/running_detached records without a live managed process are
    re-checked every listing: pid alive (and still our engine binary - pids
    recycle) -> running_detached; pid gone -> finished when the log tail shows
    a normal completion, else interrupted. Completed detached work is ingested
    into the durable store immediately.
    """
    status = record.get("status")
    if status not in {"running", "running_detached"} or record["id"] in _PROCS:
        return record
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
    return records


def get_job(job_id: str) -> dict | None:
    record = _load(job_id)
    return _refresh(record) if record else None


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
    return [r for r in list_jobs() if r["status"] in {"running", "running_detached"}]
