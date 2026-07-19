# Backend API contract (for the dashboard webapp)

Base URL: `http://127.0.0.1:8787` (CORS open). All responses JSON unless noted.
The backend is read-only over case data; its only writes are
`training-runs/control.json` and job launch/stop.

## Data

- `GET /api/health` — `{status, runs_root, skills_repo, engines:[{engine, available, note}]}`
- `GET /api/rounds` — array of `{round_id, round: <round.json|null>, case_count, cases:[case-summary]}`
- `GET /api/cases` — flat array of case summaries:
  `{round_id, case_id, entity, security, as_of, run_mode, case_role, method_commit, phase, sealed, sealed_at, evaluated, metrics, delivery_passed, has_report, has_model, last_activity}`
  where `metrics` = evaluation.json metrics: `{revenue_mape, profit_margin_mae_pp, revenue_coverage, profit_coverage, revenue_interval_score, profit_interval_score}` (nullable).
- `GET /api/cases/{round_id}/{case_id}` — full detail: summary fields plus raw
  `run_manifest`, `forecast_snapshot`, `forecast_seal` (files list replaced by `file_count`),
  `evaluation` (incl. per-period `scores` rows), `delivery_validation`, `training_state`,
  `mode_config`, and `files` (relative paths).
- `GET /api/cases/{round_id}/{case_id}/report` — `text/plain` report.md.
- `GET /api/cases/{round_id}/{case_id}/model` — model.xlsx download.

## Export (for the hosted Sites dashboard)

- `GET /api/export/snapshot` — sanitized full bundle
  `{generated_at, source, method, skills, rounds (cases incl. report_md, capped 200KB each), status}`.
  A local sync agent pushes exactly this JSON to the Site's ingest endpoint;
  the hosted Site never reaches into the private network (unsupported by Sites).

## Method progress

- `GET /api/method/timeline` — `{head, branch, dirty, remote, commits:[{hash, short, date, subject, body}]}` from the skills git repo (each commit = one method revision).
- `GET /api/method/skills` — installed skills: `[{dir, name, description, body_lines}]`.

## Status and control

- `GET /api/status` — `{control, running_jobs, latest_case_activity}`.
- `POST /api/control` — body `{"auto_training": "run"|"pause", "note": "..."}`;
  writes `training-runs/control.json` (the pause switch training sessions obey).

## Jobs (launch agent runs)

- `GET /api/engines` — `[{engine: "claude", available: true}, {engine: "codex", available: false, note}]`.
  Render codex as a disabled option until available flips.
- `POST /api/jobs` — body `{"type", "engine": "claude", "params": {...}}` → 201 job record.
  - `type: "live_forecast"` — params `{entity, security?, as_of?, extra?}`; workspace `training-runs/live/<security>@<as_of>/`.
  - `type: "training_case"` — params `{entity, security?, as_of, round_id, case_role: development|validation|regression, extra?}`.
  - `type: "training_round"` — params `{round_id, group_a:[{entity, security?, as_of}...], group_b:[...], extra?}` — the full autonomous round (this is the "start auto-optimization" button; "stop" = POST pause + stop the job).
  - Errors: 422 bad params, 501 engine not available (codex until wired).
- `GET /api/jobs` — newest-first job records `{id, type, engine, params, pid, status: running|finished|failed|stopped|running_detached|interrupted, started_at, ended_at, returncode}`.
- `GET /api/jobs/{id}` — one record.
- `GET /api/jobs/{id}/log?tail=200` — `text/plain` log tail (poll this for live progress).
- `POST /api/jobs/{id}/stop` — SIGTERM the process group.

## Watchlist & portfolio (投资看板)

- `GET /api/watchlist` / `POST /api/watchlist` `{entity, security?, note?}` / `DELETE /api/watchlist/{security}`.
- `GET /api/portfolio` — watchlist joined with cases: each row adds `case_count`, `latest`, `latest_live`, `valuation` (the snapshot's `valuation_summary`: current_price, price_as_of, current_valuation_note, fair_value{bear,base,bull}, recommended_buy_price, action, one_line_thesis), `job_running`, `cases[]`.
- `GET /api/quotes?symbols=MU,NVDA` — best-effort live quotes (Yahoo; config `quotes.proxy` if blocked). Values: `{price, currency, market_time, previous_close}` or `{error}` — always fall back to `valuation.current_price` + `price_as_of`.

## Curriculum & round plans (自训练)

- `GET /api/curriculum` — trainer skill's bundled plan: `[{wave, pairs:[{pair_id, cases:[{company, security, proposed_as_of, role, mechanism, case_key}]}]}]`. A default round = two pairs (2 development -> Group A, 2 holdouts -> Group B).
- `POST /api/rounds` `{round_id, group_a[], group_b[], notes?}` — save/update a round plan (writes `round.json`, status `planned`); group entries need `entity` + `as_of` (+`security`).
- `DELETE /api/rounds/{round_id}` / `DELETE /api/cases/{round_id}/{case_id}` — soft delete: moves into `training-runs/_trash/` (recoverable by hand).
- Job type `plan_round` (POST /api/jobs) — an agent reads the curriculum + past rounds and writes the next planned round.json itself.
- Job type `training_round` now accepts `params:{round_id}` alone — groups load from the saved round plan.
- `DELETE /api/jobs/{job_id}` — remove a finished job record+log (409 while running).

## Conventions

- Empty `training-runs/` is a valid state: render empty lists gracefully.
- Poll `GET /api/status` (and job logs) every few seconds for the live view; no websockets in v0.1.
- Artifact names/shapes are stable interfaces owned by the skills; coordinate before requesting changes.
