# Earnings Power, Persistence and Conditional Mean Reversion

The forecast target is future revenue, operating profit and GAAP net income.
Reported earnings are an accounting total; earnings power is a forecast of
which parts persist, reverse, require reinvestment or invite competition.  This
is a bridge and a set of equations, not an earnings-quality score.

## Build the profit layers separately

For each historical and forecast period, model and then sum:

```text
Revenue
- cash-like recurring operating cost
- working-capital accrual recognized in the period
- non-current operating accruals (depreciation, amortization, provisions)
= core operating profit
+/- unusual but operating items
= GAAP operating profit
+/- financing, equity-method, investment, FX and other non-operating items
= pretax profit
- recurring tax - discrete tax - non-controlling interests
= GAAP net income attributable to common shareholders
```

Do not forecast a consolidated margin first and decorate it afterward.  Each
material layer needs its own driver, period, source, scenario and reversal or
renewal clock.  Gross profit, operating profit, pretax profit and net income
must reconcile through the integrated statements.

For every forecast period, the same reported amounts must reconcile across
`integrated_model`, the canonical point fields in `forecast_snapshot`, and
`earnings_power_bridge.csv`.  The machine chain is revenue less operating
costs to GAAP operating profit, plus signed non-operating items to pretax
profit, less signed tax expense to consolidated net income, and less net
income attributable to non-controlling interests to GAAP net income
attributable.  Record an explicit zero for the non-controlling-interest claim
when none exists; blank never means zero.  Period labels, entity perimeter,
currency, scale, accounting basis and sign convention inherit the frozen run
contract and may change only through an explicit comparability bridge.

## Trace cash and accrual support

Use the accounting identity as a diagnostic:

```text
NOPAT = after-tax operating free cash flow + change in net operating assets
```

Here `after-tax operating free cash flow` excludes financing flows, interest,
security investments and distributions, and `net operating assets` uses the
same operating perimeter.  Do not combine pre-tax operating income with
levered or after-tax free cash flow; that mixed-basis expression is not an
accounting identity.

Then decompose the change in net operating assets into receivables and contract
assets, inventory and reserves, payables and supplier finance, PPE, leases,
capitalized development or commissions, acquired intangibles, provisions and
other operating balances.  Record:

- whether the amount is a stock, flow, estimate or allocation;
- its cash timing and expected reversal or realization event;
- the operating driver it finances;
- the reliability of the estimate and the reporting-policy dependency;
- the allowed forecast use and the observation that would invalidate it.

Use the existing `gaap_operating_profit` row in
`earnings_power_bridge.csv`; do not create a parallel quality score or a second
earnings table. On that row, record operating tax and `nopat`, use
`cash_support` for after-tax operating free cash flow and
`accrual_component` for the change in net operating assets, and recompute:

```text
GAAP operating profit - operating tax expense = NOPAT
NOPAT - cash support - change in net operating assets = NOA bridge residual = 0
```

The linked driver nodes carry the material NOA components and their reversal or
realization clocks. Deterministic validation owns the two identities, source
and node references. The independent reviewer decides whether the operating
perimeter, tax basis, component decomposition and forecast interpretation are
economically complete.

High accruals are not automatically low-quality earnings.  Normal growth can
consume working capital; conservative accounting can expense real investment;
and current cash flow can be lifted by cutting investment.  The question is
whether the balance represents supported growth, timing, a low-reliability
estimate, a reserve release, a perimeter change or deterioration.

<!-- canonical: normalized_earnings_views -->
## Separate reported, normalized and owner cash views

Keep three views and reconcile them; never overwrite GAAP:

1. **Reported earnings** follow the applicable accounting standards.
2. **Normalized earnings** remove or spread only items whose recurrence and
   economic cause have been investigated.
3. **Owner cash view** bridges CFO through maintenance investment, working
   capital, leases, supplier finance, dilution and other claims on cash.

For R&D, customer acquisition and internally generated intangibles, show GAAP
and an optional shadow capitalization schedule.  The economic life, attrition
and amortization must be company-specific and sensitivity-tested.  Neither
capitalization nor expensing proves commercial value.

When expensed internal investment could materially change normalized earning
power or cross-company comparability, read
`references/internal-intangible-investment.md` and complete the routed
`internal_intangible_investment.json` schedule.  Build sourced vintage cohorts,
show a decision-relevant numeric immateriality test, or retain
`human_required` and cap the affected conclusion.  Do not force an empty cohort
schedule on a company where this is not a material uncertainty.  The shadow
view is analytical only and never overwrites the reported profit chain.

## Cost behavior is state dependent

Revenue growth and contraction do not use the same cost elasticity:

```text
change in cost = elasticity_up * change in activity              if activity rises
change in cost = elasticity_down * change in activity
                 + exit or adjustment cost                       if activity falls
```

Add the adjustment lag and committed-resource floor.  Select the activity unit
that creates the cost: units, customers, usage, headcount, installed capacity,
projects, sites or service events.  Percent of revenue is allowed only when its
elasticity, range and lag are stated.  Academic population coefficients are not
company parameters.

This schedule is executable, not narrative.  For each cost line selected as a
material thesis or downside carrier,
`forecast_snapshot.persistence_analysis.cost_behavior` records the causal
activity-driver node and unit, separate non-negative
`elasticity_up` and `elasticity_down`, a non-negative integer adjustment lag,
the committed-resource floor and its unit, exit or adjustment cost, estimation
method, source IDs and named scenario paths.  The activity driver must sit on
the thesis line.  The validator checks supplied equations and references; the
independent reviewer decides whether a material cost carrier was omitted and
whether the estimation method transfers to the company.  An unsupported
industry-average coefficient or a prose claim that costs are "sticky" cannot
set a parameter.
If disclosure cannot support an elasticity, lag or committed-resource floor,
preserve `provisional`, `human_required` or `not_available_with_reason` plus
the limitation. Do not manufacture coefficients to obtain `accepted` status;
the frozen reviewer owns the readiness consequence.

## Conditional mean reversion

Mean reversion is an outside-view base rate, not a fixed fade rate and not a
command to be pessimistic.  For every FY+2 or later forecast identify:

1. **object** — revenue growth, price, margin, turnover, RNOA or ROIC;
2. **reference class** — same lifecycle, economic mechanism and cycle state;
3. **target distribution** — median, dispersion and sample-selection limits;
4. **departure** — why the company differs from that class;
5. **speed** — contract duration, switching/qualification, capital response,
   regulation, obsolescence, network or capacity lead time;
6. **falsifier** — the dated observation that changes target, direction or speed.

The reference class is selected before looking for a preferred answer and is
constructed from membership and attributes observable when the evidence bundle
is frozen.
Avoid survivor-only groups, hindsight removal of firms later acquired, failed
or delisted, and a generic sector average.  A structural transition may
justify moving away from a historical mean; a shortage, reserve release or
investment pause may require faster normalization.

The machine contract is
`forecast_snapshot.persistence_analysis.mean_reversion`. An `accepted`
outside-view prior binds the object and unit to known root-source lineage,
states numeric low, median and high targets, discloses sample-selection limits
and the company-specific departure, and links speed, falsification and scenario
nodes. A numeric fade horizon is optional because the executed fade schedule,
not a universal number of years, is the model object. If no defensible class is
observable, preserve `provisional`, `human_required` or
`not_available_with_reason` plus the limitation instead of inventing peers or
targets. The validator recomputes supplied ranges and resolves IDs. It does not
require an independent-source count or declare a class adequate; the isolated
reviewer judges authority for the proposition, selection bias, economic
comparability, departure and readiness consequence.

## Growth transition is a symmetric audit

Trailing organic growth, current run-rate, management guidance, consensus and
reference-class growth are challenger baselines, not truth and not floors.
Explain both material acceleration and material deceleration with a quantified
bridge:

```text
baseline growth
+/- terminal demand
+/- share, content and mix
+/- price
+/- capacity, qualification and recognition timing
+/- inventory stocking or destocking
+/- perimeter and currency
= driver-tree implied growth
```

Forecasting below trailing growth is not a defect.  Forecasting either above or
below a relevant baseline without a measurable transition is a research defect.
Management guidance may be conservative or optimistic; estimate bias only for
the same management, definition, horizon and business regime, preserving the
full historical distribution.

## Margin, turnover and investment

Reconcile operating returns as:

```text
RNOA = operating margin * net operating asset turnover
change in RNOA = margin contribution + turnover contribution + interaction
```

The fundamental-growth identity (reinvestment rate × incremental ROIC) is
defined in `core-output-and-valuation.md`.

Ask separately whether price/mix/unit cost changed margin, whether working
capital or utilization changed turnover, and whether new investment has matured.
A temporary denominator increase is not automatically moat erosion; a margin
peak caused by underinvestment is not automatically durable earnings power.

## Required schedule and validation

Complete `earnings_power_bridge.csv`.  Every material line records the reported
amount, `bridge_from_prior_layer`, normalization, cash and accrual support,
investment and cycle effects, persistence mechanism, competitive response,
fade target and source/model links.  Within each period, the revenue bridge is
zero and every subsequent reported layer equals the preceding reported layer
plus its bridge.  Accepted forecast layers also reconcile to the matching
period in `forecast_snapshot.json`.  Unobservable conclusion-critical items are
`human_required`, appear in the snapshot disclosure and cap readiness; if all
profit layers are unresolved the delivery is `not-decision-ready`.

`not_material_with_reason` is a narrow, measured exception, not an empty-row
status. Each measured immaterial non-revenue layer may use it. Every such row still needs
all numeric bridge, normalization, cash/accrual, investment, cycle and fade
fields; known source IDs; known graph nodes; the reported-to-normalized identity;
the prior-layer reconciliation; and snapshot reconciliation where applicable.
Its absolute bridge divided by the period's revenue must not exceed the run's
case-specific `material_profit_impact_pct`, and notes state the economic reason.
A revenue anchor cannot be exempt. An unmeasured bridge or all layers marked not
material fails; research-grade always requires a measured bridge across the
complete profit chain. There is no arbitrary count cap: arithmetic materiality
and qualitative significance are evaluated line by line, with the independent
reviewer retaining authority over economic significance.

The red team attacks, in order: revenue transition, cash/accrual support, cost
asymmetry, special-item classification, financing/tax, reference-class choice,
competitive response and terminal fade.

## Method basis and misuse boundary

- Fama and French document nonlinear profitability mean reversion in a broad
  population; their population rate is not a company fade parameter.
- Sloan and Richardson et al. support separating cash and accrual components and
  reliability; they do not authorize a universal accrual haircut.
- Nissim and Penman support operating/financing reformulation and profitability
  decomposition; historical ratios remain diagnostics, not constants.
- Penman and Zhang show that conservative accounting and changing investment can
  make current earnings temporarily misleading; not all R&D or SG&A is an asset.
- Fairfield and Yohn support examining changes in margin and turnover; a DuPont
  level alone does not forecast the future.
- Cost-stickiness research supports asymmetric resource adjustment; published
  average elasticities must never be copied into a company model.

See `references/methodological-foundations.md` for the exact sources and narrow
permissions.  No item in this reference is a buy/sell score.
