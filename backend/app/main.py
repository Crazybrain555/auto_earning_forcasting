"""Forecasting dashboard backend.

Read-only data API over the training-runs tree and the skills git repo, plus
the controlled dashboard mutations and Codex job lifecycle endpoints.
"""
from __future__ import annotations

from pathlib import Path
from typing import Literal

from fastapi import Depends, FastAPI, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse, PlainTextResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from . import control, curriculum, data, jobs, method, quotes, state
from .config import CONFIG

app = FastAPI(title="Technology Company Forecasting Backend", version="0.1.0")
# Same-origin dashboard needs no CORS; the allowlist exists only for the dev
# fixture instance. Never "*": with an unauthenticated localhost API that
# launches bypass-permission agents, "*" is a drive-by RCE vector.
app.add_middleware(
    CORSMiddleware,
    allow_origins=[f"http://{h}:{p}" for h in ("localhost", "127.0.0.1") for p in (8787, 8791)],
    allow_methods=["*"],
    allow_headers=["*"],
)


def require_dashboard(x_dashboard: str | None = Header(None)):
    """CSRF guard for mutating routes: cross-origin pages cannot attach this
    custom header without passing the (now restrictive) CORS preflight."""
    if x_dashboard != "1":
        raise HTTPException(403, "missing X-Dashboard header (use the dashboard or add 'X-Dashboard: 1')")


MUTATING = dict(dependencies=[Depends(require_dashboard)])


class ControlRequest(BaseModel):
    auto_training: str
    note: str = ""


class JobRequest(BaseModel):
    type: str
    # CONTRACT (user requirement): both engines are selectable from the dashboard.
    engine: Literal["claude", "codex"] = "claude"
    params: dict = {}


class WatchRequest(BaseModel):
    entity: str
    security: str = ""
    note: str = ""


class RoundPlanRequest(BaseModel):
    round_id: str
    group_a: list
    group_b: list
    notes: str = ""


@app.get("/api")
def index():
    return {
        "service": "technology-company-forecasting backend",
        "endpoints": [
            "GET  /api/health",
            "GET  /api/engines",
            "GET  /api/rounds",
            "GET  /api/cases",
            "GET  /api/cases/{round_id}/{case_id}",
            "GET  /api/cases/{round_id}/{case_id}/report",
            "GET  /api/cases/{round_id}/{case_id}/model",
            "GET  /api/method/timeline",
            "GET  /api/method/skills",
            "GET  /api/export/snapshot",
            "GET  /api/status",
            "POST /api/control",
            "GET  /api/jobs",
            "POST /api/jobs",
            "GET  /api/jobs/{job_id}",
            "GET  /api/jobs/{job_id}/log",
            "POST /api/jobs/{job_id}/stop",
            "DELETE /api/jobs/{job_id}",
            "GET  /api/watchlist",
            "POST /api/watchlist",
            "DELETE /api/watchlist/{security}",
            "GET  /api/portfolio",
            "GET  /api/curriculum",
            "GET  /api/quotes?symbols=A,B",
            "GET  /api/symbol-search?q=lam",
            "GET  /api/watch-suggestions",
            "POST /api/rounds  (save round plan)",
            "DELETE /api/rounds/{round_id}",
            "DELETE /api/cases/{round_id}/{case_id}",
        ],
    }


@app.get("/api/health")
def health():
    return {
        "status": "ok",
        "runs_root": CONFIG["runs_root"],
        "skills_repo": CONFIG["skills_repo"],
        "engines": jobs.engine_status(),
    }


@app.get("/api/engines")
def engines():
    return jobs.engine_status()


@app.get("/api/rounds")
def rounds():
    return data.list_rounds()


@app.get("/api/cases")
def cases():
    return data.list_cases()


@app.get("/api/cases/{round_id}/{case_id}")
def case_detail(round_id: str, case_id: str):
    detail = data.case_detail(round_id, case_id)
    if detail is None:
        raise HTTPException(404, "case not found")
    return detail


@app.get("/api/cases/{round_id}/{case_id}/report", response_class=PlainTextResponse)
def case_report(round_id: str, case_id: str):
    path = data.case_file(round_id, case_id, "report")
    if path is None:
        raise HTTPException(404, "report not found")
    return path.read_text(encoding="utf-8", errors="replace")


@app.get("/api/cases/{round_id}/{case_id}/model")
def case_model(round_id: str, case_id: str):
    path = data.case_file(round_id, case_id, "model")
    if path is None:
        raise HTTPException(404, "model workbook not found")
    return FileResponse(
        path,
        filename=f"{case_id}-model.xlsx",
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )


@app.get("/api/history/{security}")
def security_history(security: str):
    """Per-security version trail from the durable store (survives overwrites)."""
    from . import db
    db.scan(data.list_cases, data.read_json, data.normalize_outputs)
    return db.history(security)


@app.post("/api/runs/{run_id}/activate", **MUTATING)
def activate_run(run_id: int):
    from . import db
    if not db.activate(run_id):
        raise HTTPException(404, "run version not found")
    return {"ok": True}


@app.post("/api/history/{security}/auto", **MUTATING)
def auto_version(security: str):
    from . import db
    db.deactivate(security)
    return {"ok": True}


@app.delete("/api/runs/{run_id}", **MUTATING)
def delete_run(run_id: int):
    from . import db
    if not db.soft_delete(run_id):
        raise HTTPException(404, "run version not found (or already deleted)")
    return {"ok": True}


@app.post("/api/runs/{run_id}/restore", **MUTATING)
def restore_run(run_id: int):
    from . import db
    if not db.restore(run_id):
        raise HTTPException(404, "run version not found")
    return {"ok": True}


@app.get("/api/method/timeline")
def method_timeline():
    return method.timeline()


@app.get("/api/method/progress")
def method_progress():
    return data.method_progress()


@app.get("/api/method/evolution")
def method_evolution():
    return method.evolution()


@app.get("/api/method/skill-map")
def method_skill_map():
    return method.skill_map()


@app.get("/api/method/file", response_class=PlainTextResponse)
def method_file(path: str):
    result = method.skill_file(path)
    if result is None:
        raise HTTPException(404, "file not found in live skill")
    return result[1]


@app.get("/api/method/skills")
def method_skills():
    return method.skills()


@app.get("/api/export/snapshot")
def export_snapshot():
    """Sanitized bundle a sync agent pushes to the hosted Sites dashboard.

    Sites cannot reach private networks, so data flows outbound only:
    local backend -> (this export) -> POST to the Site's ingest endpoint.
    """
    running = []
    for job in jobs.running_jobs():
        job = dict(job)
        job.pop("prompt", None)
        running.append(job)
    rounds = data.list_rounds()
    for rnd in rounds:
        for case in rnd["cases"]:
            path = data.case_file(case["round_id"], case["case_id"], "report")
            if path is not None:
                text = path.read_text(encoding="utf-8", errors="replace")
                case["report_md"] = text[:200_000]
    import datetime as _dt
    return {
        "generated_at": _dt.datetime.now(_dt.timezone.utc).isoformat(),
        "source": "forecast-backend/0.1.0",
        "method": method.timeline(),
        "skills": method.skills(),
        "rounds": rounds,
        "status": {
            "control": control.read_control(),
            "running_jobs": running,
            "latest_case_activity": data.latest_activity(),
        },
    }


@app.get("/api/status")
def status():
    return {
        "control": control.read_control(),
        "running_jobs": jobs.running_jobs(),
        "latest_case_activity": data.latest_activity(),
    }


@app.post("/api/control", **MUTATING)
def set_control(req: ControlRequest):
    try:
        return control.write_control(req.auto_training, req.note)
    except ValueError as exc:
        raise HTTPException(422, str(exc))


@app.get("/api/jobs")
def all_jobs():
    return jobs.list_jobs()


@app.post("/api/jobs", status_code=201, **MUTATING)
def create_job(req: JobRequest, x_idempotency_key: str | None = Header(None)):
    try:
        return jobs.start_job(
            req.type,
            req.engine,
            req.params,
            idempotency_key=x_idempotency_key or "",
        )
    except PermissionError as exc:
        raise HTTPException(501, str(exc))
    except ValueError as exc:
        raise HTTPException(422, str(exc))


@app.get("/api/jobs/{job_id}")
def job_detail(job_id: str):
    record = jobs.get_job(job_id)
    if record is None:
        raise HTTPException(404, "job not found")
    return record


@app.get("/api/jobs/{job_id}/log", response_class=PlainTextResponse)
def job_log(job_id: str, tail: int = 200, safe: bool = False):
    log = jobs.job_log(job_id, tail=max(1, min(tail, 5000)), safe=safe)
    if log is None:
        raise HTTPException(404, "log not found")
    return log


@app.post("/api/jobs/{job_id}/stop", **MUTATING)
def stop_job(job_id: str):
    record = jobs.stop_job(job_id)
    if record is None:
        raise HTTPException(404, "job not found")
    return record


@app.delete("/api/jobs/{job_id}", **MUTATING)
def delete_job(job_id: str):
    try:
        ok = jobs.delete_job(job_id)
    except PermissionError as exc:
        raise HTTPException(409, str(exc))
    if not ok:
        raise HTTPException(404, "job not found")
    return {"deleted": job_id}


@app.get("/api/watchlist")
def get_watchlist():
    return state.load_watchlist()


@app.post("/api/watchlist", status_code=201, **MUTATING)
def add_watchlist(req: WatchRequest):
    try:
        return state.add_watch(req.entity, req.security, req.note)
    except ValueError as exc:
        raise HTTPException(422, str(exc))


@app.delete("/api/watchlist/{security}", **MUTATING)
def remove_watchlist(security: str):
    return state.remove_watch(security)


@app.get("/api/portfolio")
def portfolio():
    return data.portfolio(state.load_watchlist(), jobs.running_jobs())


@app.get("/api/curriculum")
def get_curriculum():
    return curriculum.waves()


@app.get("/api/symbol-search")
def symbol_search(q: str = ""):
    return quotes.search_symbols(q[:60])


@app.get("/api/watch-suggestions")
def watch_suggestions():
    return state.load_suggestions()


@app.delete("/api/watch-suggestions", **MUTATING)
def clear_watch_suggestions():
    state.clear_suggestions()
    return {"ok": True}


@app.get("/api/quotes")
def get_quotes(symbols: str = ""):
    requested = [s.strip() for s in symbols.split(",") if s.strip()]
    result = quotes.get_quotes(requested[:100])
    for sym in requested[100:]:
        result[sym.upper()] = {"symbol": sym.upper(), "error": "truncated: too many symbols in one request"}
    return result


@app.post("/api/rounds", status_code=201, **MUTATING)
def save_round(req: RoundPlanRequest):
    try:
        return data.save_round_plan(req.round_id, req.group_a, req.group_b, req.notes, method.git("rev-parse", "HEAD"))
    except ValueError as exc:
        raise HTTPException(422, str(exc))


@app.delete("/api/rounds/{round_id}", **MUTATING)
def delete_round(round_id: str):
    try:
        moved = data.delete_round(round_id)
    except PermissionError as exc:
        raise HTTPException(403, str(exc))
    if moved is None:
        raise HTTPException(404, "round not found")
    return {"trashed_to": moved}


@app.delete("/api/cases/{round_id}/{case_id}", **MUTATING)
def delete_case(round_id: str, case_id: str):
    moved = data.delete_case(round_id, case_id)
    if moved is None:
        raise HTTPException(404, "case not found")
    return {"trashed_to": moved}


# Serve the local dashboard (webapp/ at project root) from the same port.
# Mounted last so /api/* routes keep precedence.

@app.middleware("http")
async def _static_no_cache(request, call_next):
    """Dashboard js/css/html must revalidate on every load (ETag 304s still apply);
    without this browsers heuristically cache app.js and users see stale UI."""
    response = await call_next(request)
    if request.url.path.startswith("/api"):
        response.headers["Cache-Control"] = "no-store"   # 状态接口永远实时,禁止启发式缓存
    else:
        response.headers["Cache-Control"] = "no-cache"
    return response


WEBAPP_DIR = Path(CONFIG["project_root"]) / "webapp"


def _asset_version(name: str) -> str:
    """Content version for a webapp asset: changes only when the file changes."""
    try:
        stat = (WEBAPP_DIR / name).stat()
        return f"{int(stat.st_mtime)}-{stat.st_size}"
    except OSError:
        return "0"


@app.get("/", response_class=HTMLResponse)
@app.get("/index.html", response_class=HTMLResponse)
def dashboard_index():
    """Serve index.html with versioned asset URLs.

    Browsers heuristically cache style.css/app.js and then show a stale UI after
    an edit; a content-derived query string makes a changed file a new URL, so a
    plain refresh always picks up edits while unchanged files still cache.
    """
    html = (WEBAPP_DIR / "index.html").read_text(encoding="utf-8")
    for name in ("style.css", "app.js"):
        html = html.replace(f'"{name}"', f'"{name}?v={_asset_version(name)}"')
    return HTMLResponse(html)


if WEBAPP_DIR.is_dir():
    app.mount("/", StaticFiles(directory=str(WEBAPP_DIR), html=True), name="dashboard")
