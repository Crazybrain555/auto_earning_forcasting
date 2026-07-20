---
name: technology-company-forecasting-trainer
description: Train, evaluate, audit, and revise the companion technology-company-profit-forecasting skill through point-in-time historical cases inside a strict no-leakage time sandbox - sealed forecasts, error attribution, swap-fold (train/validate role swap) cross-checks, and git-based releases where a validated improvement is committed and pushed and a failed one is reverted. Use when the user wants to run a historical training round or backtest against a frozen cutoff, diagnose forecast errors, adjust the method and validate it on held-out companies, or rebuild the live production skill. Do not use for an ordinary current-company forecast, model, or valuation; use the technology-company-profit-forecasting skill for those.
---

# Technology Company Forecasting Trainer

Use one common forecasting system for technology companies. Do not create a separate Skill for each subsector. Select and combine mechanism modules inside this Skill.

All `references/`, `scripts/`, and `assets/` paths in this document are relative to this skill's own directory (in Claude Code, `${CLAUDE_SKILL_DIR}`). Run bundled scripts from the skill directory, or pass absolute paths.

## Companion production skill

This trainer maintains and improves the production skill `technology-company-profit-forecasting`. The two skills install side by side and divide the work:

- Ordinary company research, current forecasts, models, and valuations belong to `technology-company-profit-forecasting`. If a request is an ordinary live forecast and not a training or audit case, use that skill instead; if it is not installed, say so rather than improvising a live delivery here.
- Historical training rounds, error diagnosis, method revisions, validation and regression re-runs, and live-release builds belong to this trainer. The trainer retains a complete method snapshot so it can execute historical cases and test revisions without touching the installed production skill mid-run.
- Versions are git commits of the skills repository (see `references/companion-live-skill-contract.md`). A revision that passes validation is released by regenerating the production skill with `scripts/build_live_release.py --self-test` and committing and pushing both skills together; a revision that fails is reverted with git. Never hand-edit the installed production skill outside this flow.

## Operating modes

Select one mode at run initialization.

| Mode | Information boundary | Actuals and evaluation | Purpose |
|---|---|---|---|
| `historical_train` | Browse and research freely, but only forecast-use sources whose original publication/version time is at or before the frozen `as_of` | Actuals are blocked until the forecast is validated and sealed | iterative historical training and Skill improvement |
| `live_forecast` | Use the latest evidence available at the current `as_of` | future Actuals do not exist | live company research, forecasts and valuation |
| `audit_only` | read-only contract | no revision by default | model and package review |

Read `references/mode-router-and-time-boundary.md` before research. In `historical_train`, model memory is not admissible evidence, answer-bearing future queries are prohibited, unknown-date and post-cutoff sources are quarantined, and the forecast must be sealed before any target Actual is retrieved.

## Mandatory full-model execution contract

When the user asks for a full company forecast, three- to five-year model, valuation, or durable research package, do not stop at a chat narrative.

1. Read `references/codex-parity-execution.md` and `references/full-company-delivery-contract.md`.
2. Initialize a run workspace with `scripts/scaffold_delivery.py`; for training use `scripts/scaffold_training_run.py`.
3. Maintain `run_manifest.json`, `source_manifest.json`, `forward_signal_cards.csv`, `historical_query_log.csv`, `source_independence_map.csv`, `assumption_register.csv`, `red_team.md`, `report.md`, and `forecast_snapshot.json`.
4. Build a formula-driven workbook at `model/model.xlsx`.
5. Run an independent red team and save `red_team.md`.
6. Use the role decomposition in the Codex parity protocol when parallel agents are available; otherwise execute the roles sequentially.
7. Do not publish the final conclusion until the time-boundary validator (when applicable), research-completeness validator, and `scripts/validate_delivery.py --strict` pass. If it fails, either fix the run or deliver `not-decision-ready` with every failed gate.
8. Deliver both the workbook and source-backed report, plus the manifest/snapshot artifacts.

This contract is intentionally low freedom. It is designed to reduce variance across Claude, Codex, ChatGPT, and different reasoning modes. It does not guarantee identical numbers when tool access, market data, context, or analyst judgment differ.

## Universal principles

1. Freeze `as_of`, entity, fiscal calendar, currency, security, reporting basis, and forecast horizons.
2. Build a point-in-time Source Pack and a dated forward-evidence layer. Preserve full documents or substantial anchored extracts, not just one-paragraph summaries. Do not use information published after `as_of`; repeated reports from one original source count as one independence cluster.
3. Preserve evidence permissions: E0/E1 may anchor; measured E3 may change a driver only after independent corroboration; E2 papers set technical bounds or regime tails; E4 only triggers monitoring.
4. Separate reported facts, derived facts, analyst assumptions, scenarios, and unknowns.
5. Normalize historical financials, segments, enterprise perimeter, share count, net debt, and accounting basis before forecasting.
6. Model customers, demand, supply/delivery, quantity, price, mix, cost, accounting, cash flow, and capital allocation separately where material. Also review products, technology roadmap, papers/standards/patents, management, governance, company quality and moat; map each accepted claim to a financial permission.
7. A platform deployment is not a supplier order. A design win is not revenue. Backlog is not recognized revenue. RPO is not price or margin protection.
8. Use product and program stage gates. Research, sample, qualification, production award, shipment, acceptance, and material revenue have different permissions.
9. Show GAAP bridges. Do not hide acquisition amortization, inventory step-up, restructuring, SBC, under-utilization, NRV, tax, working capital, off-balance-sheet capital obligations, or accounting-estimate changes such as useful-life extensions. Show reported and normalized profit when estimate changes are material. Separate recurring tax, bounded discrete GAAP accounting states and cash taxes; reverse non-cash benefits in FCF.
10. Use horizon-specific outputs: one-year points, two-year scenarios, three-year distributions/regime tails, and long-term normalized value.
11. In `historical_train`, the sandbox is absolute: no data leakage across the `as_of` boundary, no answer-bearing queries, and every forecast sealed before its target Actuals are retrieved. Method versions are git commits; a validated round is released by rebuilding the live skill and pushing, a failed round is reverted, and a case whose seal was broken can still train but can never again count as validation.
12. If no validated module covers the economics, or conclusion-critical data cannot be verified, mark `human-required` and cap readiness.

## Start here

1. Read `references/companion-live-skill-contract.md`, then `references/mode-router-and-time-boundary.md` and select the run mode. For a full-company delivery, first read `references/codex-parity-execution.md` and `references/full-company-delivery-contract.md`, then scaffold the run workspace.
2. Read `references/core-source-and-evidence.md`, `references/forward-evidence-and-signal-validation.md`, and `references/research-completeness-and-company-quality.md`.
3. Read `references/core-forecast-workflow.md`.
4. Read `references/driver-tree-modeling.md` first (the modeling constitution: historical base -> terminal-demand anchors -> driver tree with volume x price leaves -> explicit main line 主线 -> unit economics -> three statements), then `references/mechanism-router.md` to pick the decomposition template for each branch. Segments must sum to total revenue; the snapshot carries `driver_tree` (mechanism weights are retired - a model is one arithmetic tree, not a weighted blend). Model integrity is mechanical: `references/model-mechanical-integrity.md` (quarterly spine for FY+1, Check rows that tie the three statements, diagnostic qoq/yoy/%rev rails, two independent revenue decompositions). For any FY+2+ horizon read `references/technology-trend-evidence.md` and build the technology lane (papers/standards/patents -> driver parameter -> falsification condition) - filings are backward-looking and cannot answer which transition lands when.
5. Read only the selected module references and any relevant validated lens.
6. Read `references/core-output-and-valuation.md`.
7. For historical training or method changes, read `references/historical-training-loop.md` (the git-flow round: sandbox, train, validate, swap fold, push or revert) and `references/training-curriculum.md`, then run the bundled scripts.
8. In `historical_train`, run `scripts/validate_time_boundary.py --workspace <run> --strict` before sealing. Before delivery, run `scripts/validate_research_completeness.py --workspace <run> --strict`, then `scripts/validate_delivery.py --strict`. A formula-correct run must still fail if its research pack is insufficient.

## Mechanism selection

Select mechanisms, not industries. One company may combine several.

| Mechanism | Primary equation | Typical use |
|---|---|---|
| Unit-volume-price-mix-cost | Units or bits × ASP × mix; unit cost bridge | Memory, chips, components, materials |
| Capacity-utilization-yield | Capacity × utilization × yield × blended ASP | Foundries, OSAT, manufacturing |
| Orders-backlog-delivery-recognition | Orders × survival × delivery × installation/acceptance | Equipment, power/cooling, projects |
| Installed-base-service | Installed base × utilization × attach/renewal × service ASP | Equipment support, maintenance |
| Program-stage-conversion | Deployments × content × share × ASP × stage probability | Custom silicon, optics, design wins |
| Platform-usage-adoption | Usage/workloads × price × mix × share, constrained by infrastructure | Cloud and internet platforms |
| Subscriber-ARPU-churn-content | Subscribers × ARPU, churn, acquisition, content cash/amortization | Subscription/content platforms |
| Enterprise-perimeter-and-accounting | Organic + acquired − disposed + FX/recast; GAAP bridge | M&A, segment changes, carve-outs |
| Discrete accounting-event distribution | Eligible amount × event-state probability × recognition fraction, with cash/normalization bridge | DTA/valuation allowance, impairment, restructuring, litigation, acquisition accounting |
| Recurring-contract state and recognition | Beginning recurring base / contract stock × renewal, expansion/new-logo, stage and recognition timing | SaaS, term license, maintenance, usage and hybrid software |
| Contracts-RPO-JV-capital | Quantity, price protection, execution, recognition, JV capital | Long-term contracts and joint ventures |
| Cycle-state-regime | Recovery/expansion/late cycle/contraction/trough/regime break | Cyclical and platform businesses |

Detailed selection rules are in `references/mechanism-router.md`.

## Universal workflow

### 1. Define the forecast contract

Record entity, security, `as_of`, intended use, fiscal periods, accounting basis, horizons, artifacts, and readiness target. Stop if the perimeter or cutoff is ambiguous.

### 2. Build and freeze the Source Pack

Record source IDs, publication and retrieval times, evidence tier, content hash, period, units, location, claim, and allowed use. Preserve conflicts.

### 3. Review forward evidence and research completeness

Search conclusion-critical investor dialogue, cross-company official read-through, measured industry research, named experts/deep research, news/event discovery, product documentation, technology roadmaps, papers/standards/patents, management/governance and capital-allocation evidence. Create SignalCards, a research-coverage matrix, company-quality/moat register, technology-commercialization register, product/customer driver schedule, material-assumption support table, historical query log, and source-independence clusters. A Source Pack made of short summaries is not complete merely because the source count passes.

### 4. Normalize historicals and perimeter

Build reported financials, segment schedules, KPIs, share count, debt/cash, and comparability bridges. Separate organic growth, acquisitions, divestitures, recasts, FX, and discontinued operations.

### 5. Map segments to mechanisms

Do not route the whole company by label alone. Map each material segment to one or more mechanisms, then consolidate corporate costs, eliminations, tax, financing, and capital allocation.

### 6. Classify state and regime

Use observable signals: price, inventory, utilization, orders, backlog, customer usage, churn, capacity, product stage, capital spending, and competitive response. Use probability mixtures when signals conflict. Distinguish observable state transitions from unforecastable exogenous shocks; for the latter use distribution-only contracts rather than rewriting the Base after the fact.

### 7. Build company-quality, technology, customer and demand schedules

Assess management execution, governance, capital allocation, R&D cadence, technology/IP, standards position, switching costs, ecosystem, distribution, cost/scale advantage, competition and balance-sheet resilience. Route technology through paper/patent/standard to production and material revenue. Then build customer and demand schedules.

Identify payer, user, deployment unit, workload, usage, units, content, attach rate, price, and serviceable share. Mark unconfirmed customers and supplier shares as assumptions. For recurring-contract businesses, require product × customer group × contract type × quarter and a beginning-base / renewal / expansion-new-logo / contract-stock / recognition bridge. ARR, billings, backlog, deferred revenue, RPO and revenue are cross-checks, not additive outputs.

### 8. Build supply, delivery, or content capacity

Depending on selected modules, model manufacturing capacity, yield, packaging, components, labor, project delivery, software capacity, data-center assets, content production, or licensing constraints.

### 9. Build operating economics and material-assumption support

Use selected module equations. Avoid generic revenue CAGR assumptions. Keep quantity, usage, price, mix, cost, recognition timing, perimeter, and accounting bridges separate. Record materiality, sensitivity, support status and evidence-cluster count for every conclusion-critical assumption. When a revenue-recognition basis or contract model changes, model the transition state separately from organic demand.

### 10. Build statements and cash flow

Connect revenue and operating drivers to GAAP P&L, working capital, capex/economic capital, debt, cash, share count, and free cash flow. For incomplete segment disclosures, state allocation methods and uncertainty. Split recurring pretax profit, recurring tax, discrete GAAP state effects and cash taxes; show reported and normalized profit and reverse non-cash state benefits in cash flow.

### 11. Apply stage gates and scenarios

Route immature products, programs, regions, or business models to options or tails until evidence permits Base inclusion. Generate Bear/Base/Bull and discrete regime branches. Attribute interval width to named operating or accounting states; indiscriminate widening is prohibited.

### 12. Run cross-checks

At minimum compare:

1. Product/segment operating model.
2. Customer demand or usage model.
3. Supply/delivery/content-capacity model.
4. Long-term normalized-value model.
5. Market-implied reverse model.

Do not mechanically add cross-check outputs to reported revenue.

### 13. Value and state posture

Show current price, implied operating assumptions, scenario values, normalized value, first failure points, upgrade/kill evidence, and readiness.

### 14. Freeze the Forecast Snapshot

Use `scripts/freeze_snapshot.py`. Published snapshots are immutable. New evidence, assumptions, and methods create new versions.

## Full-company artifact standard

For a full forecast, the required hero artifacts are a formula-driven `.xlsx` model and a source-backed `.md` report. Supporting manifests, assumptions, red-team findings, and the immutable snapshot are mandatory audit artifacts. Use `assets/examples/sandisk_v73/` as a structure and quality reference only after the new company's Source Pack is frozen. Never copy its assumptions into another company. In `forecast_snapshot.json`, every `outputs` block carries the canonical evaluable keys `revenue_point/revenue_low/revenue_high` and `profit_point/profit_low/profit_high` (GAAP net income) plus `point_evaluable` - for scenario periods map base→point, bear→low, bull→high; additional metrics (segments, margins, EPS, FCF) are welcome as extra keys. SignalCards use the controlled `source_family` slugs from `references/forward-evidence-and-signal-validation.md`; a full delivery needs at least six cards across three families including one independent (non-official) family.

## Module validation status

Read `references/validated-coverage.md` before claiming readiness.

- Hardware, semiconductor, equipment, storage, foundry, packaging, materials, networking, servers, power/cooling, optical/custom silicon: retrospectively validated to varying degrees. AMD multi-platform/acquisition-accounting and Intel IDM/foundry-transition cases now extend coverage, but exact impairment and regime-break tails remain distribution-only.
- Cloud-infrastructure platform: retrospectively validated for segment revenue and segment operating income. Standalone segment FCF/ROIC/complete valuation remain `screen-grade` and `human-required` without explicit allocation bridges.
- Subscription/content platform: retrospectively validated for revenue and operating income using Netflix multi-cutoff holdouts. Gross-add/churn cohort precision, title-level content ROI, and full cash-content valuation remain `screen-grade` and `human-required` when not disclosed.
- Other internet, SaaS, marketplaces, biotech, finance, and unrelated industries: `human-required` unless separately validated.

Do not describe provisional modules as research-grade.

## Horizon contracts

- **1 year:** quarterly point forecast plus interval and KPI bridge.
- **2 years:** scenario-weighted midpoint, Bear/Base/Bull, state transition, and breakpoints.
- **3 years:** distribution, program/product options, regime tail, and normalized profit; point values are secondary.
- **Long term:** normalized margin, FCF, ROIC, capital intensity, terminal sensitivity, and market-implied requirements.

## Training rounds and git release

The full procedure is `references/historical-training-loop.md`. The shape of one round:

1. Pick Group A (2 training companies with frozen cutoffs) and Group B (2 validation companies, untouched until their turn) - four companies per round by default. Record `round.json` and the base method commit (`git rev-parse HEAD`).
2. Run Group A in the sandbox: point-in-time research, sealed forecast (`scripts/freeze_training_forecast.py`) before Actuals, then score (`scripts/score_training_forecast.py`).
3. Improve on Group A: attribute errors (DATA, PERIMETER, STATE, PARAM, STRUCTURE, TIMING, REGIME, ACCOUNTING, EXOGENOUS), change the reusable mechanism rule — never tune a number to a known actual — and confirm the right-reason: the forecast moved for the cause claimed. Commit locally.
4. Validate on Group B, sealed before Actuals. No big problem (target error type does not recur, no new systematic bias, intervals not silently widened, one regression spot-check on a previously used non-target company when relevant) → rebuild the live skill with `scripts/build_live_release.py --self-test`, run `scripts/package_self_test.py` and the test suite, commit and push. Released.
5. If B fails → swap fold: adjust the rule using B as training, then re-run Group A as validation (a consistency check, since A's actuals are already exposed). If the A-trained and B-trained versions agree in direction and scope and both groups look acceptable, merge and release.
6. If it still fails → revert to the base commit, record the round as abandoned with its diagnosis, and start the next round with a new group of training companies; this round's companies join the regression pool, not the next validation set.

## Readiness labels

- `not-decision-ready`: missing critical data, failed formulas, contaminated cutoff, or no valid mechanism.
- `screen-grade`: useful for triage; material assumptions remain unvalidated.
- `research-grade`: relevant mechanisms passed retrospective holdouts and regression gates.
- `decision-support`: also passed multiple locked forward quarters.
- `decision-grade`: requires larger samples, 8–12 quarters of forward validation, and independent review.

## Human-required output

When routing to humans, produce a TODO with:

- unresolved economic equation;
- missing source/field and likely owner;
- required accounting or perimeter bridge;
- candidate historical cutoffs and holdout;
- blocked conclusions;
- maximum allowed readiness;
- next evidence that would unblock the model.

## Bundled scripts

Delivery and validation:

- `scripts/scaffold_delivery.py`
- `scripts/validate_time_boundary.py`
- `scripts/validate_research_completeness.py`
- `scripts/validate_forward_evidence_workspace.py`
- `scripts/validate_point_in_time_sources.py`
- `scripts/validate_delivery.py`
- `scripts/freeze_snapshot.py`

Training loop:

- `scripts/scaffold_training_run.py`
- `scripts/freeze_training_forecast.py`
- `scripts/score_training_forecast.py`
- `scripts/score_mechanism_outcomes.py`
- `scripts/scaffold_case.py`
- `scripts/validate_case.py`

Regression pool (re-running previously used companies):

- `scripts/run_backtest.py`
- `scripts/run_equipment_backtest.py`
- `scripts/run_marvell_backtest.py`
- `scripts/run_aws_backtest.py`
- `scripts/run_netflix_backtest.py`
- `scripts/run_nvidia_backtest.py`
- `scripts/run_forward_evidence_backtest.py`
- `scripts/run_amd_intel_backtest.py`
- `scripts/validate_amd_intel_point_in_time.py`
- `scripts/regression_check.py`
- `scripts/scope_regression_check.py`

Release:

- `scripts/build_live_release.py`
- `scripts/package_self_test.py`

## Reference map

- `references/companion-live-skill-contract.md`
- `references/codex-parity-execution.md`
- `references/full-company-delivery-contract.md`
- `references/gold-standard-example.md`
- `references/core-source-and-evidence.md`
- `references/research-completeness-and-company-quality.md`
- `references/forward-evidence-and-signal-validation.md`
- `references/core-forecast-workflow.md`
- `references/core-output-and-valuation.md`
- `references/historical-training-loop.md`
- `references/driver-tree-modeling.md`
- `references/model-mechanical-integrity.md`
- `references/technology-trend-evidence.md`
- `references/mechanism-router.md`
- `references/module-unit-volume-price-cost.md`
- `references/module-capacity-utilization-yield.md`
- `references/module-orders-backlog-recognition.md`
- `references/module-platform-usage-adoption.md`
- `references/module-recurring-contract-revenue.md`
- `references/module-subscriber-content-economics.md`
- `references/module-program-stage-conversion.md`
- `references/module-contracts-jv-capital.md`
- `references/module-perimeter-and-accounting.md`
- `references/module-discrete-accounting-events.md`
- `references/submodule-dta-valuation-allowance.md`
- `references/validated-coverage.md`
- `references/validated-benchmarks.md`
- `references/schemas.md`
- `references/skill-compatibility.md`
- `references/mode-router-and-time-boundary.md`
- `references/training-curriculum.md`
- `references/live-mode-release.md`
- `references/lens-memory-storage.md`
- `references/lens-equipment-process-control.md`
- `references/lens-networking-optics-custom-silicon.md`
- `references/lens-foundry-packaging-materials.md`
- `references/lens-compute-platforms.md`
- `references/lens-cloud-infrastructure-platform.md`
- `references/lens-subscription-content-platform.md`
- `references/lens-enterprise-recurring-software.md`

## Gold-standard reproducibility gate

The Skill must reproduce the analytical chain, not merely the artifact shape. A delivery cannot claim `screen-grade` or parity with a strong analyst workflow when:

- accepted sources are only short summaries;
- products, customers, competitors, technology/IP, management or moat are absent;
- material assumptions are predominantly analyst-only;
- the chosen mechanism lacks its conclusion-critical direct measurement;
- FY+2/FY+3 point forecasts are emitted despite a missing critical customer/channel driver.

Keep separate labels for `process_integrity` and `research_sufficiency`. A sealed package may have high process integrity and still be `research-pack-insufficient`.

## Live release

The production skill is a live-only profile that removes trainer-only training and evaluation assets while keeping all research, evidence, mechanism, GAAP/cash, uncertainty, valuation, red-team and delivery rules. See `references/live-mode-release.md`. The maintained live SKILL.md and metadata live in `assets/live_release/` — when a method change alters anything the production skill states, update `assets/live_release/SKILL.md` in the same commit. `scripts/build_live_release.py` assembles and verifies the production artifact; release = git commit + push of both skills together.
