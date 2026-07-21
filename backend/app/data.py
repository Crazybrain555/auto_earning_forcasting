"""Read-only views over the training-runs tree.

The dashboard data contract (see project CLAUDE.md / AGENTS.md): each case
workspace exposes run_manifest.json, forecast_snapshot.json,
forecast_seal.json, evaluation.json, delivery_validation.json, report.md and
model/model.xlsx; each round directory may carry round.json. Everything here
is tolerant: partial or in-progress workspaces must render, not crash.
"""
from __future__ import annotations

import copy
import csv
import datetime as dt
import json
import re
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


def read_csv_rows(path: Path) -> list[dict[str, str]]:
    try:
        with path.open(encoding="utf-8-sig", newline="") as handle:
            return list(csv.DictReader(handle))
    except Exception:
        return []


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
    detail["model_view"] = build_model_view(
        detail.get("forecast_snapshot"),
        read_json(case_dir / "model_graph.json"),
        read_csv_rows(case_dir / "driver_monitoring.csv"),
    )
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


# ---------- stable v1/v2 investment-model adapter ----------

def _contract_major(snapshot: dict) -> str:
    version = snapshot.get("forecast_contract_version") or snapshot.get("schema_version")
    if version not in (None, ""):
        return str(version).split(".", 1)[0]
    forecast_id = str(snapshot.get("forecast_id") or "")
    return "2" if forecast_id.endswith("/v2") else "1"


def _id_list(value) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item) for item in value if item not in (None, "")]


def _unique(items) -> list:
    out = []
    for item in items:
        if item not in out:
            out.append(item)
    return out


def _profit_causal_chain(graph: dict, carriers: list[str], targets: list[str]) -> dict:
    """Select equations and context nodes on carrier-to-profit paths."""
    nodes = graph.get("nodes") if isinstance(graph.get("nodes"), list) else []
    equations = (
        graph.get("equations") if isinstance(graph.get("equations"), list) else []
    )
    equations = [equation for equation in equations if isinstance(equation, dict)]
    node_by_id = {
        str(node.get("id")): node
        for node in nodes
        if isinstance(node, dict) and node.get("id") not in (None, "")
    }

    if not targets:
        targets = [
            node_id
            for node_id, node in node_by_id.items()
            if str(node.get("financial_role") or "").lower()
            in {"profit", "net_income", "free_cash_flow", "fcf"}
        ]
    if not carriers or not targets:
        return {"nodes": [], "equations": []}

    forward = set(carriers)
    changed = True
    while changed:
        changed = False
        for equation in equations:
            inputs = set(_id_list(equation.get("inputs")))
            output = equation.get("output")
            if output not in (None, "") and inputs & forward and output not in forward:
                forward.add(str(output))
                changed = True

    backward = set(targets)
    changed = True
    while changed:
        changed = False
        for equation in equations:
            output = str(equation.get("output") or "")
            if output in backward:
                for input_id in _id_list(equation.get("inputs")):
                    if input_id not in backward:
                        backward.add(input_id)
                        changed = True

    path_outputs = forward & backward
    selected_equations = [
        equation
        for equation in equations
        if str(equation.get("output") or "") in path_outputs
        and set(_id_list(equation.get("inputs"))) & forward
    ]
    selected_ids = set(carriers) | set(targets)
    for equation in selected_equations:
        selected_ids.add(str(equation.get("output")))
        selected_ids.update(_id_list(equation.get("inputs")))

    return {
        "nodes": [
            copy.deepcopy(node)
            for node_id, node in node_by_id.items()
            if node_id in selected_ids
        ],
        "equations": copy.deepcopy(selected_equations),
    }


def build_model_view(
    snapshot: dict | None,
    model_graph: dict | None = None,
    driver_monitoring: list[dict] | None = None,
) -> dict:
    """Adapt immutable forecast artifacts to one dashboard-facing model view.

    v2 exposes the typed causal and value model.  v1 remains readable but is
    explicitly labelled as legacy decomposition metadata; historical weights
    are never copied into the reasoning view.
    """
    snapshot = snapshot if isinstance(snapshot, dict) else {}
    from . import db

    valuation_summary = db.extract_valuation(snapshot)
    if _contract_major(snapshot) != "2":
        legacy_components = snapshot.get("mechanism_weights")
        legacy_components = (
            sorted(str(key) for key in legacy_components)
            if isinstance(legacy_components, dict)
            else []
        )
        summary_thesis = valuation_summary.get("one_line_thesis") or None
        market_implied = (snapshot.get("outputs") or {}).get("market_implied")
        return {
            "contract_version": "legacy-v1",
            "mode": "legacy_decomposition",
            "legacy": True,
            "investment_case": {
                "decision_question": None,
                "variant_view": None,
                "one_line_thesis": summary_thesis,
                "margin_of_safety_pct": None,
                "permanent_loss_paths": [],
            },
            "main_line": {
                "id": None,
                "carrier_node_ids": [],
                "target_node_ids": [],
                "thesis_carriers": [],
                "profit_causal_chain": {"nodes": [], "equations": []},
                "competitor_response_node_ids": [],
            },
            "value_creation": {},
            "valuation": {"summary": valuation_summary, "methods": {}},
            "market_implied_expectations": copy.deepcopy(market_implied)
            if isinstance(market_implied, dict)
            else {},
            "monitoring": {},
            "falsification": {
                "ids": [],
                "triggers": [],
                "breakpoints": copy.deepcopy(snapshot.get("breakpoints") or []),
            },
            "legacy_decomposition": {
                "label": "legacy decomposition metadata",
                "components": legacy_components,
                "company_lenses": copy.deepcopy(snapshot.get("company_lenses") or []),
            },
        }

    graph = model_graph if isinstance(model_graph, dict) else snapshot.get("model_graph")
    graph = graph if isinstance(graph, dict) else {}
    graph_main_line = graph.get("main_line")
    graph_main_line = graph_main_line if isinstance(graph_main_line, dict) else {}
    investment = snapshot.get("investment_case")
    investment = investment if isinstance(investment, dict) else {}
    driver_tree = snapshot.get("driver_tree")
    driver_tree = driver_tree if isinstance(driver_tree, dict) else {}

    carriers = _id_list(graph_main_line.get("carrier_node_ids")) or _id_list(
        investment.get("main_line_node_ids")
    )
    targets = _id_list(graph_main_line.get("target_node_ids"))
    if not targets:
        graph_nodes = graph.get("nodes") if isinstance(graph.get("nodes"), list) else []
        targets = [
            str(node.get("id"))
            for node in graph_nodes
            if isinstance(node, dict)
            and node.get("id") not in (None, "")
            and str(node.get("financial_role") or "").lower()
            in {"profit", "net_income", "free_cash_flow", "fcf"}
        ]

    falsification_ids = _unique(
        _id_list(investment.get("falsification_ids"))
        + _id_list(graph_main_line.get("falsification_ids"))
    )
    graph_nodes = graph.get("nodes") if isinstance(graph.get("nodes"), list) else []
    trigger_texts = []
    for node in graph_nodes:
        if not isinstance(node, dict) or str(node.get("id")) not in falsification_ids:
            continue
        for key in ("trigger", "condition", "description", "label"):
            if isinstance(node.get(key), str) and node[key].strip():
                trigger_texts.append(node[key].strip())
                break
    market_implied = snapshot.get("market_implied_expectations")
    market_implied = market_implied if isinstance(market_implied, dict) else {}
    if isinstance(market_implied.get("falsification_trigger"), str):
        trigger_texts.append(market_implied["falsification_trigger"])

    valuation = snapshot.get("valuation")
    valuation = valuation if isinstance(valuation, dict) else {}
    return {
        "contract_version": str(
            snapshot.get("forecast_contract_version")
            or snapshot.get("schema_version")
            or "2.0"
        ),
        "mode": "causal_value_model",
        "legacy": False,
        "investment_case": copy.deepcopy(investment),
        "main_line": {
            "id": driver_tree.get("main_line_id"),
            "carrier_node_ids": carriers,
            "target_node_ids": targets,
            "thesis_carriers": copy.deepcopy(driver_tree.get("thesis_carriers") or []),
            "profit_causal_chain": _profit_causal_chain(graph, carriers, targets),
            "competitor_response_node_ids": _id_list(
                graph_main_line.get("competitor_response_node_ids")
            ),
        },
        "value_creation": copy.deepcopy(snapshot.get("value_creation") or {}),
        "valuation": {
            "summary": valuation_summary,
            "methods": copy.deepcopy(valuation),
        },
        "market_implied_expectations": copy.deepcopy(market_implied),
        "monitoring": {
            **copy.deepcopy(
                snapshot.get("monitoring")
                if isinstance(snapshot.get("monitoring"), dict)
                else {}
            ),
            "drivers": copy.deepcopy(driver_monitoring or []),
        },
        "falsification": {
            "ids": falsification_ids,
            "triggers": _unique(trigger_texts),
            "breakpoints": copy.deepcopy(snapshot.get("breakpoints") or []),
        },
        "legacy_decomposition": None,
    }



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


def _round_case_key(item: dict) -> str | None:
    """Return the stable case identity used by plans and runners."""
    if not isinstance(item, dict):
        return None
    entity = str(item.get("entity", "")).strip()
    security = str(item.get("security", "") or entity).strip().upper()
    as_of = str(item.get("as_of", "")).strip()
    if not entity or not security or not as_of:
        return None
    return f"{security}@{as_of}"


def normalize_round_groups(group_a: list, group_b: list, existing: dict | None = None) -> tuple[list, list]:
    """Normalize one case-selected development/validation split.

    Group size is intentionally not a quality proxy: each side needs evidence,
    while uniqueness protects holdout independence. When a planned round is
    edited, case-level diagnostics and curriculum metadata survive unchanged.
    """
    if not isinstance(group_a, list) or not isinstance(group_b, list):
        raise ValueError("group_a and group_b must be lists")
    if not group_a or not group_b:
        raise ValueError("a round needs at least one development and at least one validation case")

    prior_by_case: dict[str, dict] = {}
    if isinstance(existing, dict):
        for group_name in ("group_a", "group_b"):
            prior_group = existing.get(group_name)
            if not isinstance(prior_group, list):
                continue
            for item in prior_group:
                key = _round_case_key(item)
                if key:
                    prior_by_case[key] = copy.deepcopy(item)

    def normalize(group: list, role: str) -> list:
        normalized = []
        seen: set[str] = set()
        for item in group:
            if not isinstance(item, dict):
                raise ValueError(f"each {role} case must be an object")
            entity = str(item.get("entity", "")).strip()
            security = str(item.get("security", "") or entity).strip().upper()
            as_of = str(item.get("as_of", "")).strip()
            if not entity or not security or not as_of:
                raise ValueError(f"each {role} case needs entity and as_of")
            case_id = f"{security}@{as_of}"
            if case_id in seen:
                raise ValueError(f"duplicate case {case_id} in the {role} group")
            seen.add(case_id)
            merged = {
                **prior_by_case.get(case_id, {}),
                **copy.deepcopy(item),
                "entity": entity,
                "security": security,
                "as_of": as_of,
                "case_id": case_id,
                "role": role,
            }
            normalized.append(merged)
        return normalized

    plan_a = normalize(group_a, "development")
    plan_b = normalize(group_b, "validation")
    overlap = {item["case_id"] for item in plan_a} & {item["case_id"] for item in plan_b}
    if overlap:
        case_id = sorted(overlap)[0]
        raise ValueError(f"case {case_id} cannot appear in both development and validation groups")
    return plan_a, plan_b


def save_round_plan(round_id: str, group_a: list, group_b: list, notes: str, base_commit: str) -> dict:
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{0,63}", round_id or ""):
        raise ValueError("round_id must be alphanumeric/dash/underscore")
    if round_id in RESERVED_ROUNDS:
        raise ValueError("'live' is reserved for live forecasts")
    round_dir = RUNS_ROOT / round_id
    existing = read_json(round_dir / "round.json") or {}
    if existing.get("status") not in (None, "planned", "abandoned"):
        raise ValueError(f"round {round_id} is '{existing.get('status')}'; only planned/abandoned rounds can be re-planned")
    plan_a, plan_b = normalize_round_groups(group_a, group_b, existing)
    round_dir.mkdir(parents=True, exist_ok=True)
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
    from . import db
    return db.extract_valuation(snap) or None


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
    from . import db
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
            "valuation": db.extract_valuation(snap),
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
