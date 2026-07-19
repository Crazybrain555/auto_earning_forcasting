# Codex parity execution protocol

## Purpose

Reduce quality variance between an interactive GPTPro research run and a Codex run. The Skill cannot force identical reasoning, tools, or market-data access, but it can force the same evidence, artifact, model, red-team, and validation contract.

Use this protocol whenever the user asks for a full company model, five-year forecast, valuation, historical backtest, or durable investment-research package.

## Non-negotiable rule

Do **not** deliver a final investment conclusion from chat-only reasoning. Create a run workspace and complete the phase gates below. The final response is allowed only after `validate_delivery.py` passes or the output is explicitly downgraded to `not-decision-ready` with the failed gates listed.

## Initialize the run

```bash
# Run from this skill's own directory (${CLAUDE_SKILL_DIR} in Claude Code)
python3 scripts/scaffold_delivery.py \
  --workspace ./forecast-runs/SNDK-20260718 \
  --entity SNDK \
  --as-of 2026-07-18 \
  --purpose "five-year operating model and valuation"
```

This creates:

```text
run_manifest.json
source_manifest.json
forward_signal_cards.csv
historical_query_log.csv
source_independence_map.csv
assumption_register.csv
red_team.md
report.md
forecast_snapshot.json
model/
```

Keep these files current during the run. They are not optional administrative files; they are the durable state and validation surface.

## Required phase gates

### Phase 0 — Contract

Freeze entity, security, `as_of`, fiscal calendar, currency, accounting basis, horizons, intended decision, artifact list, selected mechanisms, and readiness target. Do not start modeling with an ambiguous perimeter.

### Phase 1 — Source Pack

Collect and record the latest relevant filing, recent earnings releases/calls, product/customer/contract disclosures, historical filings needed for comparability, current market price with timestamp, and any E2/E3 evidence. A full-company forecast normally requires at least six official E0/E1 sources, including at least one filing and one current earnings source.

### Phase 2 — Fact and perimeter normalization

Create comparable historical financials, segments, KPIs, share count, debt/cash, acquisitions/divestitures, recasts, and accounting-estimate bridges. Facts, derived values, assumptions, and unknowns must remain distinguishable.

### Phase 3 — Mechanism routing

Map 100% of material economics to mechanisms at segment level. Do not route solely from the company label. Write `applies_to`, `does_not_apply_to`, binding constraints, and human-required gaps.

### Phase 4 — Formula model

Build the one-year quarterly model first, then two-year scenarios, three-year distribution, five-year operating statements/cash, normalized value, and market-implied reverse model. Use formulas and linked assumptions; do not hardcode calculated forecast outputs.

### Phase 5 — Independent red team

The red team must identify at least five substantive issues across evidence, double counting, customer/order inference, supply/capacity, accounting/cash, valuation, leakage, and overfitting. It must not merely restate risks from management.

### Phase 6 — Validation

Run:

```bash
python3 scripts/validate_delivery.py \
  --workspace ./forecast-runs/SNDK-20260718 --strict
```

Also run relevant historical and non-target regression scripts when changing the method.

### Phase 7 — Delivery

Deliver at minimum:

- formula-driven `.xlsx` model;
- source-backed `.md` report;
- run manifest;
- source manifest;
- assumption register;
- red-team memo;
- immutable forecast snapshot.

The user-facing response must state model readiness and the most material unresolved assumptions.

## Codex Ultra role decomposition

When parallel agents or subagents are available, split responsibilities. Each role writes files into the same run workspace and may not overwrite another role's files silently.

| Role | Responsibilities | Prohibited |
|---|---|---|
| Filings and accounting | filings, financial normalization, contracts, GAAP and cash bridges | choosing forecast points |
| Customer and demand | payer/user, deployments, usage/units, channel, customer concentration, demand cross-check | claiming unconfirmed customer share |
| Supply and technology | capacity, yield, packaging, product/program stage, cost, JV/capital | treating samples as production |
| Model and valuation | formulas, statements, scenarios, FCF, valuation, reverse model | back-solving to a target price |
| Red team | leakage, double counting, overfitting, unsupported inference, valuation stress | changing Base to make the thesis attractive |
| Integrator | resolves conflicts, runs validators, publishes final artifacts | skipping failed gates |

If parallel agents are unavailable, execute the same roles sequentially and preserve their outputs.

## Freedom calibration

Use low freedom for fragile tasks:

- filing extraction and period/unit mapping;
- formula construction and statement tie-outs;
- scenario probability sums;
- source-date cutoff checks;
- regression and package validation.

Use higher freedom only for:

- mechanism hypotheses;
- scenario narratives;
- red-team challenge generation;
- interpretation of conflicting evidence.

Any high-freedom conclusion must point to facts, assumptions, and a model cell or schedule.

## Gold-standard example

`assets/examples/sandisk_v73/` demonstrates the required artifact depth and structure. Use it for layout, evidence discipline, scenario/normalization separation, and delivery completeness only. Do not copy its assumptions, valuation multiples, or company-specific logic into another company. Freeze the new company's Source Pack before reading the example in detail.


## Forward-evidence execution
After official sources, execute a dated forward-evidence review. Require at least three material SignalCards across two independent source clusters unless the run documents that all candidates were rejected. The strict validator checks dates, source diversity, paper/E4 permissions, query contamination, independence mapping, report synthesis and red-team source-chain review.


## Research-parity role decomposition

Before model construction, execute these roles even when they are sequential:

1. **Source-depth curator:** retains full documents/substantial anchored extracts and records source depth/coverage metadata.
2. **Business/customer analyst:** maps products, revenue units, customers, channels, demand and competition.
3. **Technology/IP analyst:** reviews roadmaps, specifications, papers, standards, patents, competing routes and commercialization stages.
4. **Company-quality analyst:** reviews management, governance, incentives, capital allocation, R&D cadence, switching costs, distribution, cost/scale and balance-sheet resilience.
5. **Model/valuation analyst:** links accepted evidence to material assumptions and formula schedules.
6. **Research-sufficiency reviewer:** runs `validate_research_completeness.py --strict` independently of formula/delivery validation.

Do not allow the model/valuation role to compensate for missing research by inventing a dense assumption table.
