"""Forecasting dashboard backend.

Read-only data API over the training-runs tree and the skills git repo, plus
the two write paths the dashboard is allowed: training-runs/control.json and
launching/stopping agent jobs (engine: claude now, codex slot reserved).
"""
from __future__ import annotations

from pathlib import Path

from fastapi import Depends, FastAPI, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, PlainTextResponse
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
    engine: str = "claude"
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
    """Per-security forecast version history (the watchboard's version trail)."""
    return data.security_history(security)


@app.get("/api/method/timeline")
def method_timeline():
    return method.timeline()


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
def create_job(req: JobRequest):
    try:
        return jobs.start_job(req.type, req.engine, req.params)
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
def job_log(job_id: str, tail: int = 200):
    log = jobs.job_log(job_id, tail=max(1, min(tail, 5000)))
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
WEBAPP_DIR = Path(CONFIG["project_root"]) / "webapp"
if WEBAPP_DIR.is_dir():
    app.mount("/", StaticFiles(directory=str(WEBAPP_DIR), html=True), name="dashboard")
