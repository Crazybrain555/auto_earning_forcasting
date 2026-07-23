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
import os
import sqlite3
import threading
import time
from pathlib import Path

from .config import CONFIG

_DB_OVERRIDE = os.environ.get("FORECAST_DB_PATH")
DB_PATH = (
    # Keep the replica/current symlink intact so a pull swaps the database for
    # the next connection; every query opens its own connection (see _connect).
    Path(os.path.abspath(os.path.expanduser(_DB_OVERRIDE)))
    if _DB_OVERRIDE
    else (Path(CONFIG.get("_config_path", ".")).parent / "state" / "forecast.db").resolve()
)
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


def _present(value) -> bool:
    return value is not None and value != ""


def _first_present(*values):
    return next((value for value in values if _present(value)), None)


def _contract_major(snapshot: dict) -> str:
    version = snapshot.get("forecast_contract_version") or snapshot.get("schema_version")
    if _present(version):
        return str(version).split(".", 1)[0]
    forecast_id = str(snapshot.get("forecast_id") or "")
    return "2" if forecast_id.endswith("/v2") else "1"


def _scenario_values(payload) -> dict:
    """Read scenario values without assuming one producer-specific nesting."""
    if not isinstance(payload, dict):
        return {}
    for key in ("fair_value", "scenarios", "scenario_values"):
        nested = payload.get(key)
        if isinstance(nested, dict):
            return {role: nested.get(role) for role in ("bear", "base", "bull")}
    return {role: payload.get(role) for role in ("bear", "base", "bull")}


def _extract_valuation_reference(snapshot: dict, summary: dict) -> dict:
    """Portfolio view for the reference-scenario valuation dialect.

    This dialect values only a named reference scenario by DCF and leaves the
    other scenarios deliberately unvalued, so there is no bear/base/bull triple
    to report.  The reference fair value is surfaced on its own key while the
    bear/base/bull slots stay empty, so nothing downstream mistakes the single
    reference number for a symmetric scenario range.
    """
    valuation = snapshot.get("valuation")
    valuation = valuation if isinstance(valuation, dict) else {}
    market = snapshot.get("market_implied_expectations")
    market = market if isinstance(market, dict) else {}
    investment = snapshot.get("investment_case")
    investment = investment if isinstance(investment, dict) else {}

    by_scenario = summary.get("fair_value_by_scenario_id")
    by_scenario = dict(by_scenario) if isinstance(by_scenario, dict) else {}
    reference_scenario_id = summary.get("reference_scenario_id")
    reference_fair_value = (
        by_scenario.get(reference_scenario_id) if _present(reference_scenario_id) else None
    )
    if not _present(reference_fair_value):
        valued = [value for value in by_scenario.values() if _present(value)]
        reference_fair_value = valued[0] if len(valued) == 1 else None
    not_valued = summary.get("not_valued_scenario_ids")
    not_valued = list(not_valued) if isinstance(not_valued, (list, tuple)) else []

    note = summary.get("current_valuation_note", "")
    return {
        "current_price": _first_present(
            market.get("observed_price"), summary.get("current_price")
        ),
        "price_currency": _first_present(
            valuation.get("currency"), summary.get("price_currency")
        ),
        "price_as_of": _first_present(
            market.get("price_as_of"), summary.get("price_as_of")
        ),
        "current_valuation_note": note,
        "valuation_note": note,
        # No symmetric scenario range exists in this dialect; keep the triple
        # empty instead of promoting the reference DCF into a fake base.
        "fair_value": {"bear": None, "base": None, "bull": None},
        "reference_scenario_id": reference_scenario_id,
        "reference_fair_value": reference_fair_value,
        "fair_value_by_scenario_id": by_scenario,
        "not_valued_scenario_ids": not_valued,
        "market_implied": {
            "observed_price": market.get("observed_price"),
            "named_driver": market.get("named_driver"),
            "implied_driver_value": market.get("implied_driver_value"),
            "model_driver_value": market.get("model_driver_value"),
            "unit": market.get("unit"),
        },
        "recommended_buy_price": summary.get("recommended_buy_price"),
        "action": summary.get("action", "watch"),
        "one_line_thesis": _first_present(
            investment.get("one_line_thesis"), summary.get("one_line_thesis")
        )
        or "",
    }


def extract_valuation(snapshot: dict | None) -> dict:
    """Return the stable portfolio valuation view for either snapshot contract.

    Legacy snapshots already publish ``valuation_summary`` and are returned
    unchanged.  For v2, structured valuation and market-implied fields are the
    source of truth; the summary remains a fallback for optional presentation
    fields and scenario values that the detailed model does not publish.  The
    reference-scenario dialect (scenario-keyed fair values with the rest left
    unvalued) is surfaced through its own view without a synthesized triple.
    """
    snapshot = snapshot if isinstance(snapshot, dict) else {}
    summary = snapshot.get("valuation_summary")
    summary = dict(summary) if isinstance(summary, dict) else {}
    if "fair_value_by_scenario_id" in summary or "reference_scenario_id" in summary:
        return _extract_valuation_reference(snapshot, summary)
    if _contract_major(snapshot) != "2":
        return summary

    valuation = snapshot.get("valuation")
    valuation = valuation if isinstance(valuation, dict) else {}
    per_share = valuation.get("per_share")
    per_share = per_share if isinstance(per_share, dict) else {}
    market = snapshot.get("market_implied_expectations")
    market = market if isinstance(market, dict) else {}
    investment = snapshot.get("investment_case")
    investment = investment if isinstance(investment, dict) else {}

    legacy_fair = summary.get("fair_value")
    legacy_fair = legacy_fair if isinstance(legacy_fair, dict) else {}
    detailed_fair: dict = {}
    for candidate in (
        _scenario_values(valuation),
        _scenario_values(per_share),
    ):
        for role, value in candidate.items():
            if _present(value):
                detailed_fair[role] = value
    detailed_base = _first_present(
        per_share.get("value_per_share"),
        per_share.get("base_value_per_share"),
        (valuation.get("dcf") or {}).get("value_per_share")
        if isinstance(valuation.get("dcf"), dict)
        else None,
    )
    if _present(detailed_base):
        detailed_fair["base"] = detailed_base
    fair_value = {
        role: _first_present(detailed_fair.get(role), legacy_fair.get(role))
        for role in ("bear", "base", "bull")
    }

    margin_of_safety = investment.get("margin_of_safety_pct")
    recommended_buy_price = _first_present(
        per_share.get("recommended_buy_price"),
        valuation.get("recommended_buy_price"),
    )
    if (
        not _present(recommended_buy_price)
        and isinstance(fair_value.get("base"), (int, float))
        and not isinstance(fair_value.get("base"), bool)
        and isinstance(margin_of_safety, (int, float))
        and not isinstance(margin_of_safety, bool)
    ):
        recommended_buy_price = round(
            fair_value["base"] * (1.0 - margin_of_safety / 100.0), 6
        )
    if not _present(recommended_buy_price):
        recommended_buy_price = summary.get("recommended_buy_price")

    return {
        "current_price": _first_present(
            market.get("observed_price"), summary.get("current_price")
        ),
        "price_currency": _first_present(
            valuation.get("currency"), summary.get("price_currency")
        ),
        "price_as_of": _first_present(
            market.get("price_as_of"), summary.get("price_as_of")
        ),
        "current_valuation_note": summary.get("current_valuation_note", ""),
        "fair_value": fair_value,
        "recommended_buy_price": recommended_buy_price,
        "action": summary.get("action", "watch"),
        "one_line_thesis": _first_present(
            investment.get("one_line_thesis"), summary.get("one_line_thesis")
        )
        or "",
    }


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
    valuation = extract_valuation(snapshot)
    has_val = bool(
        (valuation.get("fair_value") or {}).get("base") is not None
        or _present(valuation.get("reference_fair_value"))
    )
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
    """The version the dashboard should show: pinned first, else the newest
    delivered one. In-progress workspaces are ingested for history, but a
    half-built snapshot must never surface as the board's conclusion - not even
    when a user pins it active (a version switch can activate an unsealed
    intermediate snapshot). Both the pinned and the fallback path therefore
    require the same completion predicate; an unsealed active version is skipped
    and the newest genuinely delivered version surfaces instead."""
    sec = _sec_key(security)
    # Board-eligible = a completed delivery carrying a valuation. Applied to the
    # pinned (is_active) path too, so activating a half-built run cannot put it
    # on the board; it stays visible in version history only.
    eligible = ("deleted_at IS NULL AND has_valuation = 1 "
                "AND (sealed = 1 OR delivery_passed = 1)")
    with _connect() as conn:
        row = conn.execute(
            f"""SELECT valuation_json FROM runs
               WHERE security = ? AND is_active = 1 AND {eligible}
               ORDER BY captured_at DESC LIMIT 1""", (sec,)).fetchone()
        if row is None:
            row = conn.execute(
                f"""SELECT valuation_json FROM runs
                   WHERE security = ? AND {eligible}
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
