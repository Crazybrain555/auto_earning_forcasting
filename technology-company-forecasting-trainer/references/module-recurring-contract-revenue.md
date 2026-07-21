# Module: recurring-contract revenue state and recognition

Use when a material portion of revenue is created by subscriptions, term licenses, maintenance/support, committed usage, multi-year agreements, deferred revenue, backlog or RPO. This is a stock-flow and state-transition module, not a rule to raise growth for every software company.

This operating module closes recurring revenue, service cost and operating
profit. It exports recognition and timing states to the financial capability;
it does not roll shares, cash, tax or the three statements, assign scenario
probabilities, model fade or value the company.

## 1. Contract-type decomposition

Classify material revenue into ratable subscription/term license, maintenance/support, usage/consumption, upfront license/IP/hardware/royalty, professional services, and acquired/migrated/accounting-transition cohorts.

Contract value, billings, backlog, deferred revenue, RPO, bookings, ACV, ARR, usage and recognized revenue are different states or flows. Never add them.

## 2. Cohort ARR/NRR identity and stock-flow equations

Build product × customer group × contract type × original-start cohort ×
quarter rows. An existing-customer expansion remains in its original cohort;
`new_logo_ARR` contains only customers absent from the eligible opening base.
This boundary is mandatory even when management reports only aggregate ARR.

For every opening cohort `c`:

```text
Ending existing-cohort ARR_c,t
= beginning eligible ARR_c,t
- churn ARR_c,t
- contraction ARR_c,t
+ price ARR_c,t
+ seat / volume / usage expansion ARR_c,t
+ explicit price×volume cross-effect_c,t

GRR_t
= sum(beginning eligible ARR - churn ARR - contraction ARR)
÷ sum(beginning eligible ARR)

NRR_t
= sum(ending existing-cohort ARR at constant FX and perimeter)
÷ sum(beginning eligible ARR at constant FX and perimeter)

Ending ARR_t
= sum(ending existing-cohort ARR_c,t)
+ sum(new-logo ARR_c,t)
± separately disclosed FX / acquisition / disposal / migration effects_t
```

NRR excludes new-logo ARR. Price effect is calculated holding retained
quantity/usage constant; seat/usage expansion is calculated at the base price;
the price×volume cross-effect is shown once. Alternatively, calculate ending
ARR directly from ending units × ending price and use the bridge only as an
exact reconciliation. Never put the same existing-customer expansion in both
the retained cohort and an expansion/new-logo row. Require zero checks for the
cohort sum, NRR numerator and reported-ARR reconciliation.

### Recognition and contract-stock equations

For each material contract type and, where disclosed, customer cohort:

```text
Recognized ratable revenue_c,t
= average in-force annualized recurring value_c,t
× period fraction_t
× recognition factor_c,t

New-logo ARR_c,t
= qualified new-logo contract value_c,t
× stage / close probability_c,t
× activation probability_c,t

Recognized recurring revenue_t
= sum(recognized ratable revenue_c,t)
+ permitted catch-up / variable-consideration adjustments_t

Ending unrecognized contract stock_t
= beginning unrecognized contract stock_t
+ signed contract additions_t
- cancellations / FX / scope reductions_t
- recognized contract revenue_t

Reported revenue_t
= recognized recurring revenue_t
+ upfront product / IP / hardware revenue_t
+ billable usage units_t × effective price per usage unit_t
+ services revenue_t
+ permitted accounting-transition adjustments_t
```

Customer demand, contract stock, billings/deferred and reported revenue are cross-checks, not additive models.

### Usage, hosting and support unit economics

For consumption or AI service, the cost schedule is mandatory:

```text
Serve / inference cost_t
= usage units_t × unit serve / inference cost_t

Required hosting capacity_t
= usage units_t × resource intensity per usage unit_t
÷ utilization_t

Hosting capacity cost_t
= average deployed hosting capacity_t × unit hosting cost_t

Support load_t
= active customers, tickets, hours or cases_t
× support intensity per active unit_t

Support cost_t
= support load_t × unit support cost_t
```

Define the cost pools inside each unit rate. If serve cost includes hosting,
set the separate hosting row to zero and label the rate `all-in`; otherwise
exclude depreciation/leases, fixed energy/network, facilities and idle
capacity from serve cost. Reconcile the cost pools so no hosting or support
dollar appears twice. A carried gross-margin ratio or unexplained
`support/other` percentage is non-compliant.

## 3. State transitions

- `C0` prospect/no contract;
- `C1` qualified opportunity;
- `C2` signed but not started;
- `C3` live/partially recognized;
- `C4` renewal, expansion or contraction;
- `C5` churn, cancellation, migration or collection risk.

A new accounting standard, pricing model, contract migration or acquisition integration needs a separate transition ledger. Do not infer organic demand from a recognition shift.

## 4. Evidence permission

- Filings and audited facts anchor what was reported on their stated accounting
  basis; contract notes anchor disclosed terms; official KPI definitions anchor
  the issuer's own construct. None of them independently proves future demand,
  retention, realized price or margin.
- Official customer/partner evidence may change stage probability after perimeter and independence checks.
- Independently generated measurements may change a driver when their construct,
  population, period and causal link fit that proposition; corroboration means
  independent roots, not report count.
- Sales anecdotes, unnamed pipeline claims, search snippets and duplicated commentary are monitoring signals only.
- Missing cohort, duration, cancellation or recognition data require an explicit residual and lower readiness; do not invent customer names or shares.

## 5. Technology-inflection challenger and causal bridge

A technology transition is a rival hypothesis to historical persistence, not a
mechanical growth floor. When material, decompose it into observable adoption
states and the recurring economics it could change:

```text
eligible customers or workloads
× qualification / migration rate
× incremental seats, usage or attach per adoption
× effective price
× recognition timing
= transition-linked recurring revenue
```

Model the opposing mechanisms in the same graph: saturation, delayed programs,
customer concentration, churn or cannibalization, capacity/support constraints,
discounting and competitive response. Historical organic expansion, management
guidance and an adoption build are separate challengers. A gap between them is
a research question; it is not proof that guidance is conservative or that the
historical rate is a lower bound.

Move the transition into the reference operating path only when
proposition-appropriate observations
support the named adoption states and economics and the serious rivals have
been investigated. Technical feasibility, TAM, commentary or a fixed count of
signals cannot grant that permission. If company attribution, timing or
economics remain unresolved, keep the transition as a bounded rival input and
monitor the discriminating observations. The coordinator decides whether that
input warrants an authored joint scenario.

## 6. Permission and uncertainty

- Guidance is an output constraint and management belief, not the revenue equation.
- Beginning base, renewal, expansion/new logos, price/usage, stage probability and recognition timing are separate parameters.
- RPO/backlog raises visibility only after survival and timing; it does not establish price, margin or collection.
- Upfront and ratable revenue have distinct margin/cash profiles when material.
- Attribute uncertainty to the relevant state or driver; do not widen all lines/years uniformly.
- FY+1 point precision requires a bridge that explains a substantial, decision-relevant share of revenue and reconciles to official guidance/run rate.
- FY+2 shows renewal/expansion and recognition breakpoints; FY+3 is distribution-first when cohort/duration evidence is weak.

## 7. Operating bundle and downstream mappings

Include only the schedules needed to close the operating path: product ×
customer group × contract type × quarter; beginning recurring base;
renewal/expansion/new logos; price/usage; stage conversion; unrecognized
contract stock and recognition by revenue type; cancellations/FX/scope; the
selected service-cost construction; operating profit; evidence permission;
material sensitivity and falsification.

When an all-in observed service/hosting cost and a decomposed serve/capacity/
support build are both available, compile both to one canonical service-cost
node, select exactly one for execution and let that node enter operating profit
once. The unselected path remains a reconciliation check.

Export deferred-revenue, receivable, contract-asset, payable,
capitalized-development, billing and collection timing as named downstream
mappings when observed; the financial capability owns their accounting rolls,
cash-flow links, share denominators, tax, FCF and valuation. If a material rival
changes retention, price, usage, cost or recognition timing, return the changed
node, unit, effective period, lag, evidence and falsifier. The coordinator, not
this module, decides whether to create a joint scenario and probability.

If a required cohort, price, usage, cost or recognition input is missing,
author one `human-required` blocker with the affected operating output and next
evidence. Keep the machine formula symbolic and reference that blocker; do not
repeat a placeholder table for every period or pull in downstream schedules to
make the operating bundle look complete.

## 8. Coverage and residual diagnostics

Calculate:

```text
explained_revenue_share
= revenue generated by explicit driver rows / modeled revenue

sensitivity_weighted_residual
= unexplained revenue share × sensitivity of the conclusion to that residual
```

These are diagnostics, not target ratios. The independent reviewer decides
whether the residual can change the revenue, profit or investment conclusion,
using disclosure quality, concentration, business mix and sensitivity. Do not
manufacture rows to improve an explained-share percentage.

Cap readiness or fail the mechanism when:

- customer/product rows do not feed formulas;
- a material residual is unnamed or unsensitized;
- contract value is treated as recognized revenue;
- ARR, billings, RPO and revenue are added;
- new-logo ARR is included in NRR or expansion is counted in two cohorts;
- serve, hosting-capacity and support costs are blended into one margin plug;
- a proposed rival input omits its model node, unit, effective period or lag;
- a missing schedule is deleted instead of retained as `human-required`;
- one renewal/growth rate is applied to heterogeneous cohorts without evidence;
- an accounting transition is called organic demand.
