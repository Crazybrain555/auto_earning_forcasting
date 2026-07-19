# AI_stock_framework — agent operating notes

## Forecasting system operations (deployment config — not method)

The two forecasting skills in `.claude/skills/` (`technology-company-profit-forecasting`, `technology-company-forecasting-trainer`) are a git checkout of https://github.com/Crazybrain555/auto_earning_forcasting. Change them only via git (edit -> run tests -> commit -> push); never write machine-specific or generated content into the skill directories — deployment configuration lives in this file instead.

- **Runs root:** training/forecast case workspaces go under `training-runs/<round-id>/<case-id>/` at this project root. Never commit them into the skills repo.
- **Dashboard writes (allowed set):** `training-runs/control.json`, round plans (`training-runs/<round-id>/round.json` for planned rounds), and soft-deletes that move case/round directories into `training-runs/_trash/` (never hard-delete). Backend UI state lives in `backend/state/`. Everything else in the runs tree is written only by forecasting/training sessions.
- **Pause control:** before starting each training case (and between swap-fold phases), read `training-runs/control.json` if it exists: `{"auto_training": "run"|"pause", "note": "...", "updated_at": "..."}`. On `pause`, finish the current step, record the pause in that round's `round.json`, and stop until it returns to `run`. The dashboard webapp owns and writes this one file; training sessions only read it.
- **Dashboard:** the webapp under `webapp/` reads case artifacts read-only (`run_manifest.json`, `forecast_snapshot.json`, `forecast_seal.json`, `evaluation.json`, `delivery_validation.json`, `round.json`, `report.md`, `model/model.xlsx`). Treat these artifact names and shapes as stable interfaces; coordinate before changing them.

- **Backend service:** `backend/` (FastAPI, start with `backend/run.sh`, http://127.0.0.1:8787). The dashboard webapp calls it — API contract in `backend/API.md`. It reads the runs tree and skills git history, writes only `training-runs/control.json`, and launches/stops headless agent jobs (engine `claude` active; engine `codex` is a reserved slot in `backend/config.json` until the Codex port is finalized). Job records/logs live in `backend/jobs/`.
