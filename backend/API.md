# Backend API contract (for the dashboard webapp)

Base URL: `http://127.0.0.1:8787` (CORS open). All responses JSON unless noted.
The backend is read-only over case data; its only writes are
`training-runs/control.json` and job launch/stop.

## Data

- `GET /api/health` — `{status, runs_root, skills_repo, engines:[{engine, available, note}]}`
- `GET /api/rounds` — array of `{round_id, round: <round.json|null>, case_count, cases:[case-summary]}`
- `GET /api/cases` — flat array of case summaries:
  `{round_id, case_id, entity, security, as_of, run_mode, case_role, method_commit, phase, sealed, seal_status, sealed_at, evaluated, metrics, delivery_passed, has_report, has_model, last_activity}`. `seal_status` is `published`, `sealed_before_actuals`, `invalid`, or null; an arbitrary JSON file is never presented as a valid seal.
  where `metrics` = evaluation.json metrics: `{revenue_mape, profit_margin_mae_pp, revenue_coverage, profit_coverage, revenue_interval_score, profit_interval_score}` (nullable).
- `GET /api/cases/{round_id}/{case_id}` — full detail: summary fields plus raw
  `run_manifest`, `forecast_snapshot`, `forecast_seal` (files list replaced by `file_count`),
  `evaluation` (incl. per-period `scores` rows), `delivery_validation`, `training_state`,
  `mode_config`, `model_view`, and `files` (relative paths). The raw
  `forecast_snapshot` is returned unchanged; `model_view` is a read-only adapter with a
  stable shape across forecast contracts:
  - `{contract_version, mode, legacy, investment_case, main_line, value_creation,
    valuation, market_implied_expectations, monitoring, falsification,
    legacy_decomposition}`.
  - For v2, `main_line` combines `model_graph.json` with the snapshot's `driver_tree`
    and exposes `{carrier_node_ids, target_node_ids, thesis_carriers,
    profit_causal_chain:{nodes,equations}, competitor_response_node_ids}`.
    `valuation.summary` is the portfolio-compatible conclusion while
    `valuation.methods` preserves the structured DCF/residual-income/terminal and
    enterprise-to-equity model. `monitoring.drivers` carries the parsed
    `driver_monitoring.csv` rows (series, frequency, threshold and breach action).
  - For v1, `mode="legacy_decomposition"`, `legacy=true`, and
    `legacy_decomposition` contains component names and historical company lenses only.
    Legacy `mechanism_weights` are deliberately omitted because they are not causal
    reasoning. Missing v2 sections degrade to empty objects/lists rather than breaking
    the endpoint.
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

- `GET /api/status` — `{control, running_jobs, capacity: {max_concurrent_jobs, max_queued_jobs, submit_rate_max, submit_rate_window_s}, latest_case_activity}`.
- `POST /api/control` — body `{"auto_training": "run"|"pause", "note": "..."}`;
  writes `training-runs/control.json` (the pause switch training sessions obey).

## Jobs (launch agent runs)

- `GET /api/engines` — `[{engine: "claude", available: true}, {engine: "codex", available: true, note, models, default_model, default_effort}]` in local and hosted dual-engine deployments. An engine is available only when enabled and its executable is present; render availability from the response rather than hard-coding a policy.
- `POST /api/jobs` — body `{"type", "engine": "claude"|"codex", "params": {...}}` → 201 job record when a runner slot is free (`status: "running"`), or 202 + `Location`/`Retry-After` when all slots are busy (`status: "queued"`, with 1-based `queue_position`). A busy runner is never an error: queued jobs are promoted FIFO as slots free (on job completion plus a background scheduler tick that also covers backend restarts, detached-job completion and replica-pull end). Optional `X-Idempotency-Key` (8–128 safe characters) replays the original record instead of launching a second process. Independent of the key, an identical pending request (same type/engine/params fingerprint already queued or running locally) is returned with `"deduplicated": true` instead of creating a duplicate job; uniqueness lapses once the earlier job reaches a terminal state.
  - One company, one job: a `live_forecast`/`training_case` submit for a company (normalized security) that already has a queued or running job returns **409** `company busy: {SEC} ... (job {id}, {state}); cancel it first to rerun` — never queued or merged. The dashboard turns this into a cancel-and-resubmit prompt.
  - Scheduling: up to `max_concurrent_jobs` (config, currently 1) forecast/assistant jobs run in parallel; at most one job per workspace at a time. Training-lane types (`training_case`, `training_round`, `plan_round`) mutate the shared method state, so they run EXCLUSIVELY: a queued training job first drains the runner (nothing may jump past it), then runs alone.
  - Abuse guard: at most `submit_rate_max` job creations per `submit_rate_window_s` (config, default 20/60s) → 429 + `Retry-After`. Idempotent replays and dedup hits are never counted or blocked; a dedup hit additionally records the caller's key as an alias on the surviving job so later replays of the same command keep mapping to it after it finishes.
  - `type: "live_forecast"` — params `{entity, security?, as_of?, extra?}`; workspace `training-runs/live/<security>@<as_of>/`. Here `as_of` names the snapshot/workspace only: production research uses all current evidence available through bundle freeze.
  - `type: "training_case"` — params `{entity, security?, as_of, round_id, case_role: development|validation|regression, extra?}`. Historical training alone treats `as_of` as an evidence cutoff and seals before retrieving Actuals.
  - `type: "training_round"` — params `{round_id, group_a:[{entity, security?, as_of}...], group_b:[...], extra?}` — a case-selected autonomous round. Each group must contain at least one case; identities must be unique within and across groups. Omit both groups to load the saved round plan. "Stop" = POST pause + stop the job.
  - Errors: 422 bad params; 409 while a replica pull is in progress (retry after it
    finishes); 501 when the selected engine is disabled or not logged in on this
    runner; 429 + `Retry-After` on the submit-rate ceiling; 503 + `Retry-After` only
    when the bounded queue itself is full (`max_queued_jobs`, default 20).
    Capacity-full is NOT an error anymore — it queues.
- `GET /api/jobs` — newest-first job records `{id, type, engine, params, pid, status: queued|running|finished|failed|stopped|running_detached|interrupted, created_at, started_at, ended_at, returncode, error?}`. Queued records carry a live `queue_position`; a job that could not launch (engine gone at promotion time) becomes `failed` with the reason in `error`.
- `GET /api/jobs/{id}` — one record.
- `GET /api/jobs/{id}/log?tail=200` — `text/plain` log tail (poll this for live progress). Add `safe=1` for remote synchronization: the backend removes the exact stored prompt prefix and fails closed if it cannot verify that boundary.
- `POST /api/jobs/{id}/stop` — SIGTERM the process group; on a `queued` job this is a cheap dequeue (record becomes `stopped`, nothing was started).
- `DELETE /api/jobs/{job_id}` — refused (409) while running OR queued; cancel queued jobs via stop first.

## Replica (local mirror mode only)

- `GET /api/replica` — `{mode, snapshot:{snapshot_id, created_at, root_commit, site_commit}|null, pulling, started_at, finished_at, error}`. `mode` is true only when the backend was started by `backend/run-replica.sh`; the production runner and the hosted Site always report `mode: false`.
- `POST /api/replica/pull` — start a background pull of a fresh verified production replica (`deploy/forecast_runner/pull_and_prune.sh`), then poll `GET /api/replica` until `pulling` clears. Errors: 409 when a pull is already running or a job is running (pull and job launch are mutually exclusive so data is never swapped under a running agent); 404 outside replica mode or when the backend is pinned to one snapshot via `FORECAST_REPLICA_CURRENT`.

## Watchlist & portfolio (投资看板)

- `GET /api/watchlist` / `POST /api/watchlist` `{entity, security?, note?}` / `DELETE /api/watchlist/{security}`.
- `GET /api/portfolio` — watchlist joined with cases: each row adds `case_count`, `latest`, `latest_live`, `valuation` (`{current_price, price_as_of, price_currency, current_valuation_note, fair_value{bear,base,bull}, recommended_buy_price, action, one_line_thesis}`), `job_running`, `job_queued`/`queued_job_id`/`queue_position` (a queued forecast for that security, cancellable via the stop endpoint), `cases[]`. For v2, structured `valuation.per_share`, `market_implied_expectations`, and `investment_case` take priority over the compatibility `valuation_summary`; v1 continues to use `valuation_summary` unchanged.
- `GET /api/quotes?symbols=MU,NVDA` — best-effort live quotes (Yahoo; config `quotes.proxy` if blocked). Values: `{price, currency, market_time, previous_close}` or `{error}` — always fall back to `valuation.current_price` + `price_as_of`.

## Curriculum & round plans (自训练)

- `GET /api/curriculum` — trainer skill's candidate library: `[{wave, pairs:[{pair_id, cases:[{company, security, proposed_as_of, role, mechanism, case_key}]}]}]`. Planners select the smallest sufficient development/untouched-validation set for the named failure hypothesis; curriculum pairing is context, not a fixed quota.
- `POST /api/rounds` `{round_id, group_a[], group_b[], notes?}` — save/update a case-selected round plan (writes `round.json`, status `planned`; re-planning an abandoned round reopens it). Group entries need `entity` + `as_of` (+`security`); each group needs at least one case and case identities must be unique within/across groups. Identity is `UPPER(security or entity)@trim(as_of)`. Re-planning preserves unrelated top-level fields and retained cases' extension fields.
- `DELETE /api/rounds/{round_id}` / `DELETE /api/cases/{round_id}/{case_id}` — soft delete: moves into `training-runs/_trash/` (recoverable by hand).
- Job type `plan_round` (POST /api/jobs) — an agent reads the curriculum + past rounds and writes the next case-selected `round.json`, including its failure hypothesis, rival explanations and stopping rule.
- Job type `training_round` now accepts `params:{round_id}` alone — groups load from the saved round plan.
- `DELETE /api/jobs/{job_id}` — remove a finished job record+log (409 while running).

## Conventions

- Empty `training-runs/` is a valid state: render empty lists gracefully.
- Poll `GET /api/status` (and job logs) every few seconds for the live view; no websockets in v0.1.
- Artifact names/shapes are stable interfaces owned by the skills; coordinate before requesting changes.
