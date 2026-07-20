"""Read-only views over the training-runs tree.

The dashboard data contract (see project CLAUDE.md / AGENTS.md): each case
workspace exposes run_manifest.json, forecast_snapshot.json,
forecast_seal.json, evaluation.json, delivery_validation.json, report.md and
model/model.xlsx; each round directory may carry round.json. Everything here
is tolerant: partial or in-progress workspaces must render, not crash.
"""
from __future__ import annotations

import datetime as dt
import json
import shutil
from pathlib import Path

from .config import CONFIG

RUNS_ROOT = Path(CONFIG["runs_root"])

CASE_FILES = [
    "run_manifest.json",
    "forecast_snapshot.json",
    "forecast_seal.json",
    "evaluation.json",
    "delivery_validation.json",
    "training_state.json",
    "mode_config.json",
]


def read_json(path: Path):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def _safe_name(name: str) -> bool:
    return bool(name) and name not in {".", ".."} and "/" not in name and "\\" not in name and not name.startswith(".")


def safe_case_dir(round_id: str, case_id: str) -> Path | None:
    """Resolve a case dir and refuse anything that escapes the runs root."""
    if not _safe_name(round_id) or not _safe_name(case_id):
        return None
    candidate = (RUNS_ROOT / round_id / case_id).resolve()
    try:
        candidate.relative_to(RUNS_ROOT.resolve())
    except ValueError:
        return None
    return candidate if candidate.is_dir() else None


def case_summary(round_id: str, case_dir: Path) -> dict:
    manifest = read_json(case_dir / "run_manifest.json") or {}
    seal = read_json(case_dir / "forecast_seal.json")
    evaluation = read_json(case_dir / "evaluation.json") or read_json(case_dir / "evaluation" / "evaluation.json")
    validation = read_json(case_dir / "delivery_validation.json")
    state = read_json(case_dir / "training_state.json") or {}
    mtimes = [p.stat().st_mtime for p in case_dir.glob("*.json") if p.is_file()]
    return {
        "round_id": round_id,
        "case_id": case_dir.name,
        "entity": manifest.get("entity"),
        "security": manifest.get("security"),
        "as_of": manifest.get("as_of"),
        "run_mode": manifest.get("run_mode"),
        "case_role": manifest.get("training_case_role") or state.get("case_role"),
        "method_commit": manifest.get("method_commit") or state.get("method_commit"),
        "phase": state.get("phase"),
        "sealed": seal is not None,
        "sealed_at": (seal or {}).get("sealed_at"),
        "evaluated": evaluation is not None,
        "metrics": (evaluation or {}).get("metrics"),
        "delivery_passed": (validation or {}).get("passed"),
        "has_report": (case_dir / "report.md").is_file(),
        "has_model": (case_dir / "model" / "model.xlsx").is_file() or (case_dir / "model.xlsx").is_file(),
        "last_activity": max(mtimes) if mtimes else None,
    }


def is_case_dir(path: Path) -> bool:
    return path.is_dir() and (path / "run_manifest.json").is_file()


def list_rounds() -> list[dict]:
    rounds = []
    if not RUNS_ROOT.is_dir():
        return rounds
    for round_dir in sorted(RUNS_ROOT.iterdir()):
        if not round_dir.is_dir() or round_dir.name.startswith((".", "_")):
            continue
        cases = [case_summary(round_dir.name, c) for c in sorted(round_dir.iterdir()) if is_case_dir(c)]
        rounds.append({
            "round_id": round_dir.name,
            "round": read_json(round_dir / "round.json"),
            "case_count": len(cases),
            "cases": cases,
        })
    return rounds


def list_cases() -> list[dict]:
    return [case for rnd in list_rounds() for case in rnd["cases"]]


def case_detail(round_id: str, case_id: str) -> dict | None:
    case_dir = safe_case_dir(round_id, case_id)
    if case_dir is None:
        return None
    detail = case_summary(round_id, case_dir)
    for name in CASE_FILES:
        payload = read_json(case_dir / name)
        if name == "evaluation.json" and payload is None:
            payload = read_json(case_dir / "evaluation" / "evaluation.json")
        if name == "forecast_seal.json" and isinstance(payload, dict):
            payload = {k: v for k, v in payload.items() if k != "files"} | {"file_count": len(payload.get("files", []) or [])}
        detail[name.replace(".json", "")] = payload
    detail["outputs_normalized"] = normalize_outputs(detail.get("forecast_snapshot"))
    detail["files"] = sorted(
        str(p.relative_to(case_dir)) for p in case_dir.rglob("*") if p.is_file()
    )
    return detail




# ---------- snapshot output normalization (dialect -> canonical) ----------
# Snapshots produced before the canonical-keys contract use per-run dialects
# (revenue_M / revenue_base / revenue_p50_M, eps_bear / non_gaap_eps_bull, ...).
# Normalize once here so every consumer (dashboard, exports) reads one shape:
# outputs_normalized.<period> = {period, revenue: {point,low,high},
#                                profit: {...}, eps: {...}, extras: {...}}
_ROLE_SUFFIXES = {
    "point": ["", "_point", "_base", "_p50"],
    "low": ["_low", "_bear", "_p10"],
    "high": ["_high", "_bull", "_p90"],
}
_NESTED_ROLE_KEYS = {
    "point": ["point", "base", "p50", "mid"],
    "low": ["low", "bear", "p10"],
    "high": ["high", "bull", "p90"],
}
_MEASURE_BASES = {
    "revenue": ["revenue"],
    "profit": ["profit", "net_income", "gaap_net_income"],
    "eps": ["eps", "diluted_eps", "gaap_eps", "non_gaap_eps"],
}


def _is_num(value) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def _normalize_period(o: dict) -> dict:
    used: set[str] = set()

    def resolve(measure: str, role: str):
        for base in _MEASURE_BASES[measure]:
            for suffix in _ROLE_SUFFIXES[role]:
                for key in (base + suffix, base + suffix + "_M"):
                    value = o.get(key)
                    if _is_num(value):
                        used.add(key)
                        return value
            # 嵌套情景方言:revenue_M: {bear, base, bull} / {p10, p50, p90}
            for key in (base, base + "_M"):
                value = o.get(key)
                if isinstance(value, dict):
                    for nested_key in _NESTED_ROLE_KEYS[role]:
                        if _is_num(value.get(nested_key)):
                            used.add(key)
                            return value[nested_key]
        return None

    out = {"period": o.get("period")}
    used.add("period")
    for measure in ("revenue", "profit", "eps"):
        out[measure] = {role: resolve(measure, role) for role in ("point", "low", "high")}
    out["extras"] = {k: v for k, v in o.items()
                     if k not in used and k != "point_evaluable" and v is not None and not isinstance(v, (dict, list))}
    return out


def normalize_outputs(snapshot: dict | None) -> dict:
    outputs = (snapshot or {}).get("outputs") or {}
    norm = {key: _normalize_period(value) for key, value in outputs.items() if isinstance(value, dict) and value}

    # 净利推导:快照只给 EPS 没给净利总额时,净利 ≈ EPS × 摊薄股数(标 derived)。
    # 股数优先级:本期 diluted_shares_M > year_1 的 diluted_shares_M > year_1 净利/EPS 隐含。
    y1_raw = outputs.get("year_1") or {}
    y1 = norm.get("year_1") or {}

    def _implied_shares(period_raw: dict):
        for candidate in (period_raw.get("diluted_shares_M"), y1_raw.get("diluted_shares_M")):
            if _is_num(candidate) and candidate > 0:
                return candidate
        p_point = (y1.get("profit") or {}).get("point")
        e_point = (y1.get("eps") or {}).get("point")
        if _is_num(p_point) and _is_num(e_point) and e_point:
            return p_point / e_point
        return None

    for key, o in norm.items():
        profit, eps = o.get("profit") or {}, o.get("eps") or {}
        if any(_is_num(profit.get(r)) for r in ("point", "low", "high")):
            continue
        if not any(_is_num(eps.get(r)) for r in ("point", "low", "high")):
            continue
        shares = _implied_shares(outputs.get(key) or {})
        if not shares:
            continue
        for role in ("point", "low", "high"):
            if _is_num(eps.get(role)):
                profit[role] = round(eps[role] * shares)
        profit["derived"] = True
    return norm



def case_file(round_id: str, case_id: str, kind: str) -> Path | None:
    case_dir = safe_case_dir(round_id, case_id)
    if case_dir is None:
        return None
    if kind == "report":
        path = case_dir / "report.md"
    elif kind == "model":
        path = case_dir / "model" / "model.xlsx"
        if not path.is_file():
            path = case_dir / "model.xlsx"
    else:
        return None
    return path if path.is_file() else None


def latest_activity() -> float | None:
    stamps = [c["last_activity"] for c in list_cases() if c["last_activity"]]
    return max(stamps) if stamps else None


# ---------- mutations the dashboard is allowed (soft, reversible) ----------

TRASH_DIR = RUNS_ROOT / "_trash"


def _trash_move(path: Path) -> str:
    import secrets
    TRASH_DIR.mkdir(parents=True, exist_ok=True)
    stamp = dt.datetime.now().strftime("%Y%m%d-%H%M%S")
    target = TRASH_DIR / f"{stamp}-{secrets.token_hex(3)}-{path.parent.name}-{path.name}"
    while target.exists():
        target = TRASH_DIR / f"{stamp}-{secrets.token_hex(3)}-{path.parent.name}-{path.name}"
    shutil.move(str(path), str(target))
    return str(target)


def delete_case(round_id: str, case_id: str) -> str | None:
    """Soft-delete: move the case workspace into training-runs/_trash/."""
    case_dir = safe_case_dir(round_id, case_id)
    if case_dir is None:
        return None
    return _trash_move(case_dir)


RESERVED_ROUNDS = {"live"}


def delete_round(round_id: str) -> str | None:
    if round_id in RESERVED_ROUNDS:
        raise PermissionError("the live round holds every live forecast; delete individual cases instead")
    if not _safe_name(round_id):
        return None
    round_dir = (RUNS_ROOT / round_id).resolve()
    try:
        round_dir.relative_to(RUNS_ROOT.resolve())
    except ValueError:
        return None
    if round_dir == RUNS_ROOT.resolve() or not round_dir.is_dir() or round_dir.name.startswith(("_", ".")):
        return None
    return _trash_move(round_dir)


def save_round_plan(round_id: str, group_a: list, group_b: list, notes: str, base_commit: str) -> dict:
    import re
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{0,63}", round_id or ""):
        raise ValueError("round_id must be alphanumeric/dash/underscore")
    def norm(group, role):
        out = []
        for item in group:
            entity = str(item.get("entity", "")).strip()
            security = str(item.get("security", "") or entity).strip().upper()
            as_of = str(item.get("as_of", "")).strip()
            if not entity or not as_of:
                raise ValueError(f"each {role} case needs entity and as_of")
            out.append({"entity": entity, "security": security, "as_of": as_of,
                        "case_id": f"{security}@{as_of}", "role": role})
        return out
    plan_a, plan_b = norm(group_a, "development"), norm(group_b, "validation")
    if len(plan_a) != 2 or len(plan_b) != 2:
        raise ValueError(f"a round is 2 training + 2 validation companies (got {len(plan_a)}+{len(plan_b)})")
    if round_id in RESERVED_ROUNDS:
        raise ValueError("'live' is reserved for live forecasts")
    round_dir = RUNS_ROOT / round_id
    round_dir.mkdir(parents=True, exist_ok=True)
    existing = read_json(round_dir / "round.json") or {}
    if existing.get("status") not in (None, "planned", "abandoned"):
        raise ValueError(f"round {round_id} is '{existing.get('status')}'; only planned/abandoned rounds can be re-planned")
    plan = {
        **existing,
        "round_id": round_id,
        "base_method_commit": existing.get("base_method_commit") or base_commit,
        "group_a": plan_a,
        "group_b": plan_b,
        "status": existing.get("status") or "planned",
        "notes": notes or existing.get("notes", ""),
        "planned_at": dt.datetime.now(dt.timezone.utc).isoformat(),
    }
    (round_dir / "round.json").write_text(json.dumps(plan, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return plan


# ---------- portfolio join (watchlist x latest cases x valuation) ----------

def case_valuation(round_id: str, case_id: str) -> dict | None:
    case_dir = safe_case_dir(round_id, case_id)
    if case_dir is None:
        return None
    snap = read_json(case_dir / "forecast_snapshot.json") or {}
    return snap.get("valuation_summary")


def _sec_key(value) -> str:
    """Normalize a security id for matching: agents sometimes write NASDAQ:MU."""
    return str(value or "").upper().split(":")[-1].strip()


def portfolio(watchlist: list[dict], running_jobs: list[dict]) -> list[dict]:
    from . import db
    cases = list_cases()
    db.scan(lambda: cases, read_json, normalize_outputs)
    running_map: dict[str, str] = {}
    for job in running_jobs:
        sec = _sec_key((job.get("params") or {}).get("security") or (job.get("params") or {}).get("entity"))
        if sec:
            running_map.setdefault(sec, job.get("id"))
    running_secs = set(running_map)
    rows = []
    for item in watchlist:
        if not isinstance(item, dict) or not (item.get("security") or item.get("entity")):
            continue
        item = {"entity": item.get("entity") or item.get("security"), "security": (item.get("security") or item.get("entity")).upper(),
                "note": item.get("note", ""), "added_at": item.get("added_at")}
        sec = item["security"]
        mine = [c for c in cases
                if _sec_key(c.get("security")) == _sec_key(sec) or c.get("entity") == item["entity"]]
        mine.sort(key=lambda c: c.get("last_activity") or 0, reverse=True)
        latest = mine[0] if mine else None
        latest_live = next((c for c in mine if c.get("run_mode") == "live_forecast"), None)
        primary = latest_live or latest
        # DB effective version first (pinned or newest good one - survives workspace
        # overwrites); live file only as fallback for anything not yet captured.
        valuation = db.effective_valuation(sec) or (case_valuation(primary["round_id"], primary["case_id"]) if primary else None)
        rows.append({
            **item,
            "case_count": len(mine),
            "latest": latest,
            "latest_live": latest_live,
            "job_id": running_map.get(sec),
            "valuation": valuation,
            "job_running": sec in running_secs,
            "cases": mine,
        })
    return rows


def security_history(security: str) -> list[dict]:
    """Every run of one security, newest first, with its valuation conclusion -
    the version trail of the watchboard as the method evolves."""
    sec = _sec_key(security)
    entries = []
    for c in list_cases():
        if _sec_key(c.get("security")) != sec:
            continue
        case_dir = safe_case_dir(c["round_id"], c["case_id"])
        snap = read_json(case_dir / "forecast_snapshot.json") if case_dir else None
        fy1 = ((snap or {}).get("outputs") or {}).get("year_1") or {}
        entries.append({
            "round_id": c["round_id"], "case_id": c["case_id"], "as_of": c.get("as_of"),
            "run_mode": c.get("run_mode"), "method_commit": c.get("method_commit"),
            "last_activity": c.get("last_activity"), "sealed": c.get("sealed"),
            "valuation": (snap or {}).get("valuation_summary"),
            "fy1_revenue_point": fy1.get("revenue_point"), "fy1_profit_point": fy1.get("profit_point"),
            "metrics": c.get("metrics"),
        })
    entries.sort(key=lambda e: e.get("last_activity") or 0, reverse=True)
    return entries


def method_progress() -> list[dict]:
    """Is the skill getting better? Aggregate evaluated cases per method commit."""
    buckets: dict[str, dict] = {}
    for c in list_cases():
        m = c.get("metrics")
        commit = (c.get("method_commit") or "unknown")[:7]
        if not m:
            continue
        b = buckets.setdefault(commit, {"method_commit": commit, "cases": 0, "first_seen": None,
                                          "_mape": [], "_mae": [], "_cov": []})
        b["cases"] += 1
        stamp = c.get("last_activity") or 0
        b["first_seen"] = min(b["first_seen"], stamp) if b["first_seen"] else stamp
        if m.get("revenue_mape") is not None: b["_mape"].append(m["revenue_mape"])
        if m.get("profit_margin_mae_pp") is not None: b["_mae"].append(m["profit_margin_mae_pp"])
        if m.get("revenue_coverage") is not None: b["_cov"].append(m["revenue_coverage"])
    out = []
    for b in sorted(buckets.values(), key=lambda x: x["first_seen"] or 0):
        mean = lambda v: sum(v) / len(v) if v else None
        out.append({"method_commit": b["method_commit"], "cases": b["cases"], "first_seen": b["first_seen"],
                    "avg_revenue_mape": mean(b["_mape"]), "avg_margin_mae_pp": mean(b["_mae"]),
                    "avg_revenue_coverage": mean(b["_cov"])})
    return out
