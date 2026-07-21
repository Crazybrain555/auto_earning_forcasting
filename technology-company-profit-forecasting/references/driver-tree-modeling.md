# Driver-Tree Modeling

This file implements references/analysis-kernel.md in a forecast model. The
driver tree is the arithmetic projection of the causal DAG; it is not a score,
a list of themes or a weighted blend of mechanisms.

## Historical base

Reconstruct at least three comparable fiscal years plus the latest interim
period before forecasting. A period label is not a historical base. For every
annual consolidated period preserve numeric revenue, cost, gross profit,
operating profit and GAAP net income attributable, with the currency, statement
scope and source IDs. Reconcile revenue less cost to gross profit, and reconcile
the signed sum of reported segments and eliminations to consolidated revenue.
Before summing customer, product, geography or segment rows, declare the
partition ID, dimension, whether the members are exhaustive, and whether they
are mutually exclusive. Only a partition declared both exhaustive and mutually
exclusive may reconcile to its parent. Historical-base rows use one explicit
period-state contract: `annual` and `interim` rows are `actual`, while
`first_forecast` rows are `forecast`; another combination is a data-contract
error, not an unvalidated extra row. Every input row is validated: a blank,
`TBD` or `PENDING` period is an input error and cannot disappear before the
partition check. Period, period type, actual/forecast state
and currency form a stable period identity: every segment or elimination row
must resolve to exactly one consolidated parent with that identity. Every
member must resolve its declared `partition_dimension` to exactly one explicit,
non-placeholder member-ID field. The existing reported-segment view maps
`reported_operating_segment` to `reported_segment`; the normalized economics
view maps `normalized_economic_branch` to `normalized_segment`; every other
dimension uses the general `partition_member_id` field. There is no fallback
to whichever alias happens to be populated. Uniqueness and error display use
only that resolved member ID, so changing `row_type`, another alias or another
descriptive field cannot create a second member. A full-partition member also
has a numeric revenue value.
A consolidated-only first forecast remains valid; an orphan
forecast member, unnamed segment or unnamed elimination cannot disappear from
the sum. A
disclosed top-customer table or an overlapping product/geography view is a
cross-check, not a 100% decomposition.
The runtime recomputes the signed member residual; a typed zero or a green
status cannot substitute for the member values.  For a numeric consolidated
actual, `segment_reconciliation_status=not_applicable` is a narrow exception
only when the period has no segment or elimination partition rows.  Once such
numeric rows exist, use `reconciled` or `single_segment` and recompute their
signed sum, or use `disclosure_limited` with a company-specific reason and cap
readiness at `screen-grade`.  A partial Top-N customer disclosure remains a
non-exhaustive cross-check under the limited route; it is not forced to 100%.
Use one marked `latest_actual` row so the forecast bridge has an unambiguous
starting point.

Preserve reported segment totals and build explicit bridges for recasts,
acquisitions, disposals, FX, accounting-policy changes and share-count changes.
Every period states its perimeter and accounting bridge; `none_no_change` is a
valid finding, while `bridged` requires both a substantive explanation and a
metric-level `reported + comparability_delta = comparable` reconciliation for
revenue, cost, gross profit, operating profit and GAAP net income attributable.
If that adjustment cannot be quantified, use the limited route; narrative alone
does not create comparability. Do not manufacture zeroes for an undisclosed line. Use the typed
`disclosure_limited` state, state the company-specific reason and cap readiness
at `screen-grade`. Use `not_applicable` with a reason when no interim period has
yet ended since the annual filing; that calendar fact does not by itself lower
readiness. Keep a latest-interim status row in either case so absence is
auditable rather than silently omitted.

Forecast columns continue to the right of history using the same definitions.
The first forecast period must name the marked latest-actual period and show
numeric deltas for revenue, cost, gross profit, operating profit and GAAP net
income attributable. Those deltas reconcile latest actual plus change to the
first forecast and map to named causal driver nodes; a prose CAGR is not a
bridge. A new business may lack its own history, but its addressable demand,
capacity, qualification, unit economics and capital needs still require a
historical or externally measured base.

## From causal graph to arithmetic tree

For each material branch record:

- stable branch and causal-node IDs;
- reported segment and analytical subsegment;
- customer, product, geography and revenue-recognizing unit where material;
- equation primitive and variable definitions;
- units, price basis, period and accounting-recognition basis;
- dated evidence, analyst assumptions and named uncertainty state;
- upstream demand and supply constraints;
- canonical revenue, cost and operating-profit output nodes plus downstream
  handoff mappings;
- monitor and falsification condition.

The consolidated tree must identify one primary full partition and reconcile:

Total revenue = sum of segment and subsegment revenue + eliminations

Segment revenue sum must equal total revenue under the shared equation numeric
tolerance contract, and the model should normally tie exactly.  There is no
fixed percentage-of-revenue allowance.  A larger allowance for reported
rounding must come from the financial facts' declared precision/scale and be
represented in an explicit signed reconciliation row; it cannot be chosen by
the analyst. Historical comparability, revenue-cost-gross-profit and
latest-actual-to-forecast identities use the same contract. Other useful views
may be partial or overlapping, but they remain
labeled cross-checks and are never added to the primary tree.
Make this routing decision in `product_customer_driver_schedule.csv` before
model execution: primary rows carry the full-partition declaration, while a
non-exhaustive or overlapping row is labeled `cross_check`.

## General leaf equations

Choose equations by economic unit and constraint, not company label. Common
leaves include:

- units × net ASP;
- end-market units × supplier share × content × price;
- capacity × utilization × yield × price, capped by demand;
- order cohorts × survival × delivery × acceptance × price;
- average installed base × attach × service price;
- beginning contract stock − churn + expansion + new stock, followed by
  contract-cohort recognition;
- workloads × usage × effective price;
- average subscribers × ARPU;
- organic + acquired − disposed + FX and recast bridges.

Full definitions are in references/equation-primitives.md. Modules provide
specialized implementation detail for these equations. They do not vote on the
answer.

## Main line and thesis compression

Declare the smallest causally sufficient set of thesis carriers: causal paths
whose perturbation explains most of the change in revenue and operating profit.
One or
two is common, but no numeric cap may hide a genuinely material path. Each
carrier must:

1. begin with observable evidence or an explicit analyst assumption;
2. terminate in a physical, contractual or usage unit;
3. pass through price and cost into a canonical operating-profit output;
4. state sign, lag, rival explanation and falsification condition;
5. show reference-path and material rival-state values for the named variables;
6. report sensitivity of revenue and operating profit, then expose the named
   output nodes so the financial capability can extend the chain.

The red team attacks the main line first. Uniform percentage haircuts to the
whole model are not scenarios.

## Demand, supply, price and cost stay separate

For each branch build, where material:

- external end demand or usage;
- sell-through, sell-in and channel inventory;
- addressable scope, customer share and supplier share;
- nameplate capacity, qualified capacity, utilization and yield;
- orders, cancellations, delivery and acceptance;
- gross and net price, mix, rebates and contract protection;
- materials, conversion, fixed-cost absorption, warranty and logistics;
- recognized revenue and the timing facts or state changes that downstream
  accounting may need.

A platform deployment is not a supplier order. A design selection is not
qualified production. Backlog is not recognized revenue. Shipment is not
acceptance. Revenue is not cash.

## Unit economics

Manufacturing branches ordinarily show:

capacity → saleable volume → net price → unit cost → unit gross profit.

Recurring or usage branches use an economically equivalent state bridge. Price
and unit cost move only through named drivers. Gross margin is calculated from
the branch schedules; it is not independently forecast and then forced to agree.

When alternative constructions estimate the same economic output, group them
before execution.  Every path compiles to one declared canonical output node;
one and only one is selected for the run, its output reaches operating profit
exactly once, and all unselected paths remain non-executing cross-checks.  For
example, an all-in observed hosting-cost path and a decomposed serve/capacity/
support path must both output the same hosting-cost node rather than leaving one
path outside the operating-profit equation.

## Ratio-carry fallback

ratio_carry is permitted only when disclosure genuinely prevents a causal
decomposition. It must record:

- the missing variable and attempted sources;
- the ratio carried and historical stability;
- sensitivity range and revenue/operating-profit impact;
- why the branch is not a thesis carrier;
- monitoring trigger and readiness limitation.

Ratio carry is an explicit uncertainty state, not a professional preference.

## Downstream handoff, not downstream execution

The operating model ends after revenue, branch cost and operating profit close.
It exports the canonical nodes, their evidence bindings, the relevant timing or
stock-state mappings, and any material named rival to the financial capability
and coordinator.  It does not roll tax, cash, debt, shares or the three
statements; assign scenario probabilities; model competitive fade; or value the
equity.  Those are distinct capability contracts and should not be copied into
an operating answer merely because their inputs begin here.

Map each material carrier to its earliest observable monitor.  A causal shock
proposal is conditional: include it only when requested, when it changes the
requested profit distribution materially, or when it distinguishes the named
rival.  Otherwise the compact executable operating path is the complete output.

## No assigned weights

mechanism_weights and manual materiality weights are retired. Importance is
measured first by perturbing an input and tracing the effect on revenue and
operating profit; downstream capabilities may extend that same path to NOPAT,
FCF and value. Evidence properties help review a claim but are not added into
a truth score. The answer to where a number came from must be a reversible
evidence-and-equation path.
