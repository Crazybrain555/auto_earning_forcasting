"""Durable run-version store (SQLite, WAL).

Design follows the MLflow local-tracking split: metadata and conclusions live
in SQLite; artifacts (report.md, model.xlsx, CSVs) stay in the workspace on
disk. Every delivered forecast becomes an immutable version row - the full
snapshot JSON is captured into the DB at ingest time, so a later workspace
overwrite (rerun, scaffold accident) can never destroy history again.

Version semantics per (round_id, case_id): a new row is inserted whenever the
snapshot content hash changes. Per security the dashboard shows the "effective"
version: the user-pinned one (is_active) if set, else the newest non-deleted
row that actually carries a valuation. Deletion is soft (deleted_at), like
MLflow's lifecycle_stage.
"""
from __future__ import annotations

import datetime as dt
import hashlib
import json
import sqlite3
import threading
import time
from pathlib import Path

from .config import CONFIG

DB_PATH = Path(CONFIG.get("_config_path", ".")).parent / "state" / "forecast.db"
DB_PATH.parent.mkdir(parents=True, exist_ok=True)

_LOCK = threading.Lock()
_LAST_SCAN = 0.0
_SCAN_TTL = 5.0          # seconds; portfolio requests trigger at most one scan per TTL

_SCHEMA = """
CREATE TABLE IF NOT EXISTS runs (
  id            INTEGER PRIMARY KEY AUTOINCREMENT,
  security      TEXT NOT NULL,
  entity        TEXT,
  round_id      TEXT NOT NULL,
  case_id       TEXT NOT NULL,
  workspace     TEXT,
  as_of         TEXT,
  run_mode      TEXT,
  method_commit TEXT,
  engine        TEXT,
  model         TEXT,
  effort        TEXT,
  sealed        INTEGER DEFAULT 0,
  delivery_passed INTEGER,
  has_valuation INTEGER DEFAULT 0,
  snapshot_json TEXT,
  valuation_json TEXT,
  outputs_json  TEXT,
  metrics_json  TEXT,
  content_hash  TEXT NOT NULL,
  captured_at   TEXT NOT NULL,
  is_active     INTEGER DEFAULT 0,
  deleted_at    TEXT
);
CREATE UNIQUE INDEX IF NOT EXISTS idx_runs_version ON runs(round_id, case_id, content_hash);
CREATE INDEX IF NOT EXISTS idx_runs_security ON runs(security, captured_at);
"""


def _sec_key(value) -> str:
    return str(value or "").upper().split(":")[-1].strip()


def _connect() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH, timeout=10)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA synchronous=NORMAL")
    return conn


def init() -> None:
    with _LOCK, _connect() as conn:
        conn.executescript(_SCHEMA)


def _now() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def _job_index() -> dict[str, dict]:
    """Map workspace -> {engine, model, effort} from job records (best effort)."""
    jobs_dir = Path(CONFIG["jobs_dir"])
    index: dict[str, dict] = {}
    try:
        for path in jobs_dir.glob("*.json"):
            try:
                rec = json.loads(path.read_text(encoding="utf-8"))
            except Exception:
                continue
            params = rec.get("params") or {}
            ws = params.get("workspace")
            if ws:
                index[str(ws)] = {"engine": rec.get("engine"),
                                  "model": params.get("model") or None,
                                  "effort": params.get("effort") or None}
    except OSError:
        pass
    return index


def ingest_case(case: dict, snapshot: dict | None, outputs_normalized: dict | None,
                jobs_by_workspace: dict[str, dict] | None = None, conn=None) -> None:
    """Capture one case's current delivered state as a version row (idempotent)."""
    if not snapshot:
        return
    canonical = json.dumps(snapshot, sort_keys=True, ensure_ascii=False)
    content_hash = "sha256:" + hashlib.sha256(canonical.encode()).hexdigest()
    valuation = snapshot.get("valuation_summary") or {}
    has_val = bool((valuation.get("fair_value") or {}).get("base") is not None)
    job = (jobs_by_workspace or {}).get(str(case.get("workspace") or "")) or \
          (jobs_by_workspace or {}).get(str(Path(CONFIG["runs_root"]) / case["round_id"] / case["case_id"])) or {}
    own = conn is None
    if own:
        conn = _connect()
    try:
        conn.execute(
            """INSERT OR IGNORE INTO runs
               (security, entity, round_id, case_id, workspace, as_of, run_mode, method_commit,
                engine, model, effort, sealed, delivery_passed, has_valuation,
                snapshot_json, valuation_json, outputs_json, metrics_json, content_hash, captured_at)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (_sec_key(case.get("security")), case.get("entity"), case["round_id"], case["case_id"],
             str(case.get("workspace") or ""), case.get("as_of"), case.get("run_mode"),
             case.get("method_commit"), job.get("engine"), job.get("model"), job.get("effort"),
             1 if case.get("sealed") else 0,
             None if case.get("delivery_passed") is None else (1 if case.get("delivery_passed") else 0),
             1 if has_val else 0,
             canonical, json.dumps(valuation, ensure_ascii=False),
             json.dumps(outputs_normalized or {}, ensure_ascii=False),
             json.dumps(case.get("metrics") or {}, ensure_ascii=False),
             content_hash, _now()))
        if own:
            conn.commit()
    finally:
        if own:
            conn.close()


def scan(list_cases_fn, read_json_fn, normalize_fn, force: bool = False) -> None:
    """Walk the runs tree and capture any new snapshot versions. TTL-throttled."""
    global _LAST_SCAN
    now = time.time()
    if not force and now - _LAST_SCAN < _SCAN_TTL:
        return
    with _LOCK:
        if not force and now - _LAST_SCAN < _SCAN_TTL:
            return
        _LAST_SCAN = now
        jobs_ix = _job_index()
        conn = _connect()
        try:
            for case in list_cases_fn():
                case_dir = Path(CONFIG["runs_root"]) / case["round_id"] / case["case_id"]
                snap = read_json_fn(case_dir / "forecast_snapshot.json")
                if not snap:
                    continue
                case = {**case, "workspace": str(case_dir)}
                ingest_case(case, snap, normalize_fn(snap), jobs_ix, conn=conn)
            conn.commit()
        finally:
            conn.close()


def history(security: str) -> list[dict]:
    sec = _sec_key(security)
    with _connect() as conn:
        rows = conn.execute(
            """SELECT id, security, entity, round_id, case_id, as_of, run_mode, method_commit,
                      engine, model, effort, sealed, delivery_passed, has_valuation,
                      valuation_json, outputs_json, metrics_json, captured_at, is_active,
                      deleted_at IS NOT NULL AS deleted
               FROM runs WHERE security = ? ORDER BY captured_at DESC, id DESC""", (sec,)).fetchall()
    out = []
    for r in rows:
        d = dict(r)
        d["valuation"] = json.loads(d.pop("valuation_json") or "{}") or None
        d["outputs_normalized"] = json.loads(d.pop("outputs_json") or "{}") or None
        d["metrics"] = json.loads(d.pop("metrics_json") or "{}") or None
        out.append(d)
    return out


def effective_valuation(security: str) -> dict | None:
    """The version the dashboard should show: pinned first, else newest good one."""
    sec = _sec_key(security)
    with _connect() as conn:
        row = conn.execute(
            """SELECT valuation_json FROM runs
               WHERE security = ? AND deleted_at IS NULL AND is_active = 1
               ORDER BY captured_at DESC LIMIT 1""", (sec,)).fetchone()
        if row is None:
            row = conn.execute(
                """SELECT valuation_json FROM runs
                   WHERE security = ? AND deleted_at IS NULL AND has_valuation = 1
                   ORDER BY captured_at DESC, id DESC LIMIT 1""", (sec,)).fetchone()
    if row is None:
        return None
    try:
        val = json.loads(row["valuation_json"] or "{}")
        return val or None
    except Exception:
        return None


def activate(run_id: int) -> bool:
    with _LOCK, _connect() as conn:
        row = conn.execute("SELECT security FROM runs WHERE id = ? AND deleted_at IS NULL", (run_id,)).fetchone()
        if row is None:
            return False
        conn.execute("UPDATE runs SET is_active = 0 WHERE security = ?", (row["security"],))
        conn.execute("UPDATE runs SET is_active = 1 WHERE id = ?", (run_id,))
        conn.commit()
        return True


def deactivate(security: str) -> None:
    with _LOCK, _connect() as conn:
        conn.execute("UPDATE runs SET is_active = 0 WHERE security = ?", (_sec_key(security),))
        conn.commit()


def soft_delete(run_id: int) -> bool:
    with _LOCK, _connect() as conn:
        cur = conn.execute("UPDATE runs SET deleted_at = ?, is_active = 0 WHERE id = ? AND deleted_at IS NULL",
                           (_now(), run_id))
        conn.commit()
        return cur.rowcount > 0


def restore(run_id: int) -> bool:
    with _LOCK, _connect() as conn:
        cur = conn.execute("UPDATE runs SET deleted_at = NULL WHERE id = ?", (run_id,))
        conn.commit()
        return cur.rowcount > 0


init()
