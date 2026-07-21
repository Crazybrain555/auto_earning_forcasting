# Core Output and Valuation Contracts

Read references/valuation-and-market-expectations.md for the method. This file
defines what the deliverable must show.

## Route before rendering

The machine handoff remains complete under the shared schemas; the human answer
is the minimum sufficient view for the requested decision. Activate joint
scenarios/probabilities, competitive fade, a second valuation method or
technology/IP gates only when explicitly requested, material to the requested
profit or valuation output, or needed to distinguish a named rival. An inactive
module is omitted rather than rendered as a page of unknown placeholders.

Author a missing-input blocker once at the earliest failing handoff. Downstream
tables reference that blocker and state the affected outputs; they do not repeat
the same explanation row by row. When the earliest blocker prevents any
calculation, a compact dependency map is more truthful than a multi-period grid
whose every cell says `human-required`.

## Decision summary

For an investment-decision or valuation request, lead with:

- entity, security, automatic snapshot timestamp, current price with its own
  timestamp and intended decision;
- the smallest causally sufficient set of thesis carriers and the exact
  variables carrying the call (often one or two, never capped by a validator);
- reference-path value, and probability-weighted value only when a supported
  probabilistic scenario set is active, plus required return and margin of safety;
- material downside state, time horizon and first failure point;
- process, research, model and decision-readiness status.

The reader must be able to disagree by changing a named operating input.

## Minimum decision-memo tables

For a full-company forecast or valuation, persist every applicable machine
schedule below. Render in the human answer only the schedules needed to support
the requested conclusion and the material checks a reader must inspect. A
genuinely narrow audit may limit both machine and human scope after it states
scope, applies the named materiality test in
`references/model-mechanical-integrity.md`, and blocks all omitted full-company
conclusions. When facts are insufficient, preserve machine rows as unknown,
show the earliest blocked formula/model cell and name the missing evidence once.
A worksheet title by itself is never an output.

### Integrated three-statement minimum

This schedule is mandatory in the machine model for every full-company decision
memo and every three-year-or-longer forecast or valuation. In the human answer,
show the material rows and check residuals needed for the requested conclusion.
Use one row per period and show, at minimum,
`period | opening balance | movements | P&L link | CFS link | closing balance-sheet amount | check residual | source/status`
for each required roll.

The minimum rolls and identities are:

```text
net PPE: opening + capex - depreciation - disposals/impairments +/- perimeter/FX = closing
operating working capital: opening + change = closing
debt: opening + borrowings - repayments +/- non-cash/perimeter/FX = closing
ending basic shares: opening basic shares + basic issuance - repurchases +/- other basic-share changes = ending basic shares
period weighted-average basic/diluted EPS shares: time-weighted in-period basic shares + GAAP incremental dilution for the period
valuation-date fully diluted shares: valuation-date basic shares + economically dilutive awards/options/convertibles on the stated basis
cash: opening + CFO + CFI + CFF + FX = closing = balance-sheet cash
balance sheet: assets = liabilities + equity
free cash flow: CFO - capex - other capitalized investment = FCF
```

Show receivables, inventory, payables and other material working-capital
components rather than only a net ratio. Link depreciation and interest to
P&L; capex, working-capital cash effects, borrowings, repayments, issuance and
repurchases to CFS; and every closing stock to the balance sheet. The financing and dilution
row includes cash/equity funding and ending basic shares. Show period
weighted-average basic and diluted denominators for EPS separately; when
valuation is active, show valuation-date fully diluted shares separately. Never
reuse one basis for another. Display the CFS-to-BS cash residual and the
`assets - liabilities - equity` residual for every period.

If a value is unavailable, keep the machine period and row, write
`human-required`, reference the originating blocker, and block the dependent
conclusion. Do not reproduce a human-facing table of identical unknown cells
when a compact dependency statement communicates the same limitation. A worksheet
title, proposed tab, field list or generic formula without populated or
explicitly blocked period rows is not a completed schedule. The only exception
is a genuinely narrow review that passes the materiality route in
`references/model-mechanical-integrity.md` and disclaims full-company
forecasting and valuation conclusions.

### Patent / IP diligence

When patents or IP are material, show one row per material family with:

- `patent_evidence_status`, source IDs and family IDs;
- independent-claim scope and the product/process feature it may cover;
- filing, examination, grant, expiry and jurisdiction status;
- inventor-to-assignee chain, current owner, liens, licenses and disputes;
- family members and forward citations, separating examiner from applicant
  citations where available;
- freedom-to-operate search status, possible blocking rights, design-arounds
  and complementary trade-secret or manufacturing know-how;
- the named driver and model cell affected through the exact chain
  `claim -> existing driver_node_id -> price|unit_cost|yield|share|capex|qualification_lag|fade`; and
- present model permission, next legal evidence and falsifier.

Unknown claim text, ownership, family, citation or FTO evidence is recorded as
an explicit diligence gap; a filing count never substitutes for the table.

### Conditional value-creation identity

Activate this schedule when normalized earning power, capital allocation,
competitive persistence or valuation is material to the request. Then, for
every relevant historical and forecast period, show `reported_nopat`, after-tax
normalization adjustments, `normalized_nopat`, beginning/ending/average
invested capital, average ROIC, prior and incremental NOPAT, incremental
invested capital, incremental ROIC, return lag, organic/acquired reinvestment,
capital bridge adjustment, reinvestment rate and fundamental growth. Display
and calculate these identities:

```text
normalized NOPAT = reported NOPAT + after-tax normalization adjustments
average invested capital = (beginning + ending invested capital) / 2
average ROIC = normalized NOPAT / average invested capital
ending invested capital = beginning invested capital + reinvestment + bridge adjustment
incremental NOPAT = normalized NOPAT - prior normalized NOPAT
incremental ROIC = incremental NOPAT / incremental invested capital
reinvestment rate = reinvestment / normalized NOPAT
fundamental growth = reinvestment rate × incremental ROIC
```

The next period begins at the prior period's ending capital unless an explicit
perimeter/accounting bridge says otherwise. When competitive persistence is a
material forecast driver, render a dated fade schedule
with period, average/incremental ROIC, reinvestment rate, fundamental growth,
competition or obsolescence driver-node IDs and the erosion/renewal event.
The last row ties to terminal ROIC. Fade need not be mechanically monotonic,
but every period needs a causal event. Missing tax, capital or adjustment data
leaves explicit unknown cells and a blocked identity. If fade is immaterial to
the requested horizon, omit the module rather than inventing a reference class
or placeholder schedule.

### Earnings power and conditional persistence

For every historical and forecast period render revenue, core operating profit,
GAAP operating profit, pretax profit and GAAP net income attributable.  Reconcile
reported amount plus normalization to normalized amount and show cash support,
accrual component, investment and cycle adjustments, persistence driver,
competitive response, fade target and horizon, source IDs and graph nodes.

For every forecast period also show signed tax expense and net income
attributable to non-controlling interests in the bridge.  Use explicit zero for
the minority claim when absent.  The reported revenue, GAAP operating profit,
pretax profit, tax, minority claim and GAAP attributable net income must match
the same-period `integrated_model` income statement and canonical
`forecast_snapshot.outputs` point fields; a period missing from any of the
three artifacts blocks publication.

For FY+2 and later, when cycle normalization or competitive persistence is a
material thesis carrier, state the mean-reversion object, preselected reference
class, target distribution, company departure, speed mechanism and falsifier. Trailing
growth, guidance, consensus and reference-class outcomes are symmetric
challengers; neither acceleration nor deceleration may bypass the driver tree.

### Executable monitoring

Each thesis carrier, falsifier and material commercialization gate has a row
containing driver ID, an exact workbook cell, `continuous|milestone` monitor
type, series, source, frequency, ISO last-observation and next-expected dates,
ISO milestone date when event-driven, numeric current/model values, unit,
controlled trigger operator, numeric threshold, owner and prescribed action
if breached. Monitoring only counts when a future observation can be entered
into the named cell and cause a predeclared re-underwrite, downgrade or kill
action.

### Recurring / usage economics

For recurring-contract, platform or AI-usage businesses, show original cohort
or customer-group rows for beginning ARR, churned/retained ARR, price, seat and
usage/cross-sell expansion, new-logo ARR, ending ARR, reported/calculated NRR,
average ARR, recognition factor and subscription revenue. NRR excludes new
logos and is never added to revenue a second time. Choose the case-fitting cost
construction. When multiple constructions are useful, compile each to one
canonical cost node, execute exactly one, and leave the others as non-executing
cross-checks; do not add an all-in hosting cost to a decomposed serve/capacity/
support path. Roll deferred revenue/contract liabilities, receivables,
payables, capitalized development, amortization, SBC, tax and cash through all
three statements, with share denominators kept on their distinct bases. Every active rival scenario
changes the case-selected material retention, price, usage/cost,
acquisition-efficiency or other causal nodes with cohort, unit, effective
period and lag. Do not require an immaterial driver merely because it appears
in a recurring-business template. If disclosure is absent, the affected rows
remain as unknowns and cap readiness.

## Case-routed horizon outputs

### FY+1

Provide quarterly revenue and the requested profit/cash outputs when quarterly
disclosure and the forecast decision require the near-term spine. Add an
interval only when uncertainty output is requested or decision-material. The
annual value is formula-linked to quarters.

### FY+2

Provide the executable reference path. When a joint scenario module is active,
also provide material rival states with named causal-state changes,
probabilities only when supportable, recognition timing, capacity or supply
response, statements and value. Use `role=reference` for the one path that
reconciles to point outputs and `role=alternative` for each named-shock rival;
IDs are freely chosen descriptions and no fixed rival count is imposed.
The canonical point is therefore the executable reference joint path, not an
unlabeled probability-weighted mean, median or mode.  If a distribution
statistic is useful, calculate and label it separately from all applicable
executable states; never combine marginal financial lines into a joint state
that cannot occur.

### FY+3 and beyond

Provide the requested profit horizon. Add distributions, regime scenarios,
commercialization options, reinvestment or competitive fade only when their
named drivers materially affect it. A point estimate may be shown as a summary,
but not as false precision.

### Long term

Provide normalized growth, margin, incremental ROIC, reinvestment, capital
intensity, FCF, competitive response, fade and terminal sensitivities.

## Operating and statement outputs

Show:

- three-year historical segment bridge and forecast continuation;
- causal graph and main-line arithmetic;
- demand, supply, quantity, price, mix and cost schedules;
- integrated P&L, balance sheet and cash flow;
- working-capital, PPE, debt, cash and share-count roll-forwards;
- reported-to-normalized and GAAP/non-GAAP bridges;
- zero-valued mechanical checks.

Reported profit, analytical operating profit and cash remain separate.

## Value-creation outputs

When value creation or persistence is in scope, show NOPAT, average invested
capital, ROIC, incremental ROIC, organic and acquired reinvestment,
reinvestment rate and fundamental growth. Add explicit fade only when it is a
material driver. State definitions and disputed adjustments.

## Valuation outputs

When valuation is in scope, choose the primary method that fits the issuer and
provide its formula-linked result, the enterprise-to-equity bridge and
valuation-date fully diluted per-share denominator. Add residual income, a
cycle-normal/multiple cross-check or another second method only when it supplies
distinct information; reconcile methods whenever more than one is used. Add
reverse-implied market expectations when a dated market price and an investment
decision are in scope.

Terminal output includes growth, incremental return, reinvestment, margin,
discount rate, terminal-value share and economic constraint checks.

`valuation_summary` is only a generated dashboard projection. Its scenario IDs
come from the authored scenario catalog and every published fair value must
equal an executable valuation result. Until a rival scenario has its own
validated valuation identity, list it in `not_valued_scenario_ids`, set the
derived completeness state, keep the recommendation at `watch`/human-required
and leave the recommended buy price empty. Never type a plausible rival fair
value into the summary or silently omit an unvalued state.

## Conditional scenario and interval output

Activate this section only when joint scenarios or an uncertainty interval are
requested, materially alter the requested output, or discriminate a named
rival. Each active scenario names changed graph nodes, probability when used,
and earliest observable trigger. Every shock, not only a recurring-business shock, also records a unit
matching the graph node, an exact workbook cell or executable formula, a
declared forecast `effective_period` and a non-negative integer `lag_periods`.
The model must therefore identify both where and when a shock enters the
statements. Do not widen every row by a common percentage.

For every forecast period, each named scenario recomputes Revenue → operating
profit → pretax profit → tax → consolidated net income → NCI → GAAP
attributable net income from its shocked model cells. The `role=reference` path reconciles to the
integrated statements and point snapshot. The snapshot names
`low_scenario_id` and `high_scenario_id`; revenue, operating-profit, pretax,
tax, NCI and attributable-net-income low/high values must all come from the
same selected joint scenario. Do not assemble a publishable range from
independent marginal intervals.

When an interval is part of the requested output, freeze its nominal
miscoverage probability `interval_alpha` for each horizon before scoring.
Report interval width, empirical coverage where evaluable and a proper interval
score using that same alpha.
Wider is better only when it represents a supported uncertainty state
and improves calibration. Preserve unaffected branches rather than using global
range widening.

For a material discrete accounting event, show eligible amount, state,
probability, recognition timing, reported effect, analytical treatment, cash
effect and falsification. Combine the discrete-state distribution with
recurring operations; do not smooth it into tax or margin.

## Reverse-implied and disagreement map

State what the current price requires for units, share, ASP, unit cost, margin,
incremental ROIC, reinvestment, fade or commercialization timing. Compare each
implied driver with the research case, physical constraints and evidence.

For every material disagreement show:

- market-implied path;
- analyst path and evidence;
- value sensitivity;
- next resolving observation;
- upgrade, downgrade and kill action.

## Red team and monitoring

Red team the thesis carriers first, then evidence lineage, competitor response,
statement mechanics, accounting adjustments, capital allocation, terminal
economics and double counting.

The monitoring table includes source, frequency, current value, threshold,
owner, affected node and prescribed model action. Monitor leading causal nodes
before reported outcomes.

## Required limitations

State source gaps, unresolved conflicts, ratio carries, unverified customers,
missing technology gates, allocation choices, accounting uncertainty and
readiness caps. If a hard gate fails, deliver not-decision-ready with the exact
evidence or model work required to unblock it.
