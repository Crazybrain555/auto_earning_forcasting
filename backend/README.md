# Forecasting dashboard backend

FastAPI service the leadership dashboard calls. It has exactly three powers:

1. **Read** the `training-runs/` case tree and the skills git repo (per-company results, method-evolution timeline, live status).
2. **Write one file**: `training-runs/control.json` — the pause/resume switch training sessions obey.
3. **Launch/stop agent jobs**: spawn a headless agent to run a live forecast, one training case, or a full autonomous training round. The local console keeps both `claude` and `codex` active. Both resolve to the same canonical forecasting method through the project skill links; engine-specific CLI settings stay in `config.json`.

## Run

```bash
backend/run.sh          # first run creates backend/.venv and installs fastapi+uvicorn
# -> http://127.0.0.1:8787   (PORT=xxxx backend/run.sh to change)
```

API reference for the frontend: `API.md`.

The same port also serves the **local dashboard** (`webapp/` at the project
root, mounted at `/`): four Chinese-language views — 投资组合 (per-company
results with causal/value model, report and model download), 方法体系
(the canonical ten-stage method and git evolution), 训练控制, and 运行任务
(pause switch, dual-engine job launcher and live logs). Pure static
HTML/JS, no build step, works offline for presentations.

## Layout

- `config.json` — deployment config: paths, engines, prompt templates. This is the deployment layer; nothing here belongs in the skills repo.
- `app/` — service code (`data` runs-tree reader, `method` git timeline, `control` pause switch, `jobs` engine/job manager, `main` routes).
- `jobs/` — job records (`<id>.json`) and full logs (`<id>.log`). Gitignore-grade artifacts; safe to delete old ones.

## Security notes

- Binds to 127.0.0.1 only; no auth. Do not expose the port beyond localhost without adding auth.
- The configured headless engines run with unattended permissions so research/training rounds are not blocked by prompts. A launched job can therefore edit files and run commands in this project like an unattended operator. Tighten the engine arguments in `config.json` if a less autonomous deployment is required.
- Codex is deliberately launched without the stale localhost proxy variables recorded in older notes; the current direct configuration is the tested path.
- Jobs run with cwd = project root, so the project `CLAUDE.md` operating notes (runs root, control.json, "skills repo only via git") load automatically.

## Smoke test

```bash
PYTHONPATH=backend/.venv/lib/python3.13/site-packages python -m pytest -q backend/tests
FORECAST_BACKEND_CONFIG=/tmp/test-config.json backend/.venv/bin/uvicorn app.main:app --port 8791
curl -s http://127.0.0.1:8791/api/health
```
