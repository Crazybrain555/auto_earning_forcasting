# Forecasting dashboard backend

FastAPI service the leadership dashboard calls. It has exactly three powers:

1. **Read** the `training-runs/` case tree and the skills git repo (per-company results, method-evolution timeline, live status).
2. **Write one file**: `training-runs/control.json` — the pause/resume switch training sessions obey.
3. **Launch/stop agent jobs**: spawn a headless agent to run a live forecast, one training case, or a full autonomous training round. Engine is selectable per job: `claude` (active) or `codex` (reserved slot, returns 501 until the Codex skill port is finalized — flip `engines.codex.available` in `config.json` then, and make sure the v2rayN proxy it needs is running).

## Run

```bash
backend/run.sh          # first run creates backend/.venv and installs fastapi+uvicorn
# -> http://127.0.0.1:8787   (PORT=xxxx backend/run.sh to change)
```

API reference for the frontend: `API.md`.

The same port also serves the **local dashboard** (`webapp/` at the project
root, mounted at `/`): three Chinese-language pages — 公司成果 (per-company
results with metrics, scenario bar, report and model download), 方法与理念
(self-training philosophy, loop diagram, git method timeline), 运行与控制
(pause switch, job launcher with engine picker, live job logs). Pure static
HTML/JS, no build step, works offline for presentations.

## Layout

- `config.json` — deployment config: paths, engines, prompt templates. This is the deployment layer; nothing here belongs in the skills repo.
- `app/` — service code (`data` runs-tree reader, `method` git timeline, `control` pause switch, `jobs` engine/job manager, `main` routes).
- `jobs/` — job records (`<id>.json`) and full logs (`<id>.log`). Gitignore-grade artifacts; safe to delete old ones.

## Security notes

- Binds to 127.0.0.1 only; no auth. Do not expose the port beyond localhost without adding auth.
- The `claude` engine runs with `--permission-mode bypassPermissions` so autonomous research/training runs are not blocked by permission prompts. That means a launched job can edit files and run commands in this project like an unattended operator. Tighten to `acceptEdits` in `config.json` if you want file-edit-only autonomy, at the cost of training rounds not being able to git-commit on their own.
- Jobs run with cwd = project root, so the project `CLAUDE.md` operating notes (runs root, control.json, "skills repo only via git") load automatically.

## Smoke test

```bash
backend/.venv/bin/python -m pytest ...   # (no unit tests yet; use the curl smoke below)
FORECAST_BACKEND_CONFIG=/tmp/test-config.json backend/.venv/bin/uvicorn app.main:app --port 8791
curl -s http://127.0.0.1:8791/api/health
```
