# Module: platform usage, adoption, pricing, infrastructure, and accounting

**Validation scope:** calibrated for platform segment revenue and operating
income. This operating module stops at a canonical operating-profit output and
exports accounting/timing mappings. The financial capability owns cash, tax,
shares, FCF, ROIC and valuation.

## Core revenue equation

```text
Billable usage units_t
= average active workloads or customers_t
× usage units per active workload or customer_t
× billable / monetized share_t

Usage revenue_t
= billable usage units_t
× effective price per usage unit_t
× recognition factor_t

New activated workloads_t
= eligible acquisition / partner spend_t
× sales-efficiency_t
÷ initial annualized usage value per activation_t
```

Do not let usage growth equal revenue growth. Effective price includes list-price reductions, committed-use discounts, migrations to cheaper architectures, customer rightsizing, and higher-layer service mix.

The last equation is a named acquisition/activation branch, not permission to
plug growth from sales expense. Replace it with a directly observed pipeline,
deployment or product-led acquisition equation when that is better measured;
keep `sales-efficiency` as a cross-check and scenario node either way. Existing
customer retention/rightsizing, price, usage intensity and new activation are
separate nodes. Do not count a workload expansion in both retained usage and
new workloads.

## Mandatory platform schedule

Build product/service × customer/cohort × region × quarter rows. Every
material row carries `node_id`, `model_cell_or_formula`, unit, period,
beginning active workloads/customers, new activations, retained/churned or
rightsized workloads, usage per active workload, billable share, effective
price, recognition factor, source/assumption status, and downstream financial
statement cells. The schedule must reconcile:

```text
Ending active base_t
= beginning active base_t
+ activated cohorts_t
- churned / migrated-out cohorts_t

Existing-base usage_t
= retained existing active base_t × usage per retained active unit_t

New-cohort usage_t
= sum(new activated cohort_c × ramp profile_c,t)

Total billable usage_t
= existing-base usage_t + new-cohort usage_t
```

If ARR/NRR is disclosed, use the cohort definitions and anti-double-counting
rules in `module-recurring-contract-revenue.md`. ARR, RPO, bookings, billings,
usage and recognized revenue remain separate stock/flow states and are never
added together.

## Required state variables

- migration / expansion;
- customer cost optimization and rightsizing;
- supply or infrastructure constraint;
- AI or other platform regime break;
- mature-scale normalization.

Preserve materially different states as named rival inputs. The coordinator
decides whether they warrant a joint scenario or probabilities.

## Infrastructure and operating-profit bridge

```text
Required hosting capacity_t
= billable and non-billable usage units_t
× resource intensity per usage unit_t
÷ utilization efficiency_t

Ending deployed hosting capacity_t
= beginning deployed hosting capacity_t
+ capacity activated after construction / delivery lag_t
- retired capacity_t

Serve / inference cost_t
= usage units_t × unit serve / inference cost_t

Hosting capacity cost_t
= average deployed hosting capacity_t × unit hosting cost_t

Support load_t
= active customers or workloads_t × tickets / hours per active unit_t

Support cost_t
= support load_t × unit support cost_t

Reported operating profit
= Revenue
- serve / inference cost
- hosting capacity cost
- support cost
- product development and sales
- shared-cost allocation
```

`unit serve / inference cost` must show its included cost pools. When hosting
capacity cost is modeled separately, exclude depreciation/leases, idle
capacity, fixed energy/network and other hosting costs from the serve-cost
rate; otherwise label the all-in rate and set the separate hosting row to zero.
The cost-pool reconciliation must prove each dollar appears once. Split hosting
capacity cost into depreciation/leases, energy/network, facilities and idle
capacity when material. A residual `support/other` percentage is not an
acceptable substitute for the support-load equation.

For asset-heavy platforms, show both:

1. reported operating margin; and
2. normalized operating margin after removing disclosed useful-life accounting benefits or charges and applying an explicit economic depreciation range.

Use segment assets, property/equipment, net additions, leases, and depreciation as a **reinvestment proxy**. Do not call a proxy standalone segment capex or FCF.

When all-in observed hosting cost and the decomposed serve/capacity/support
construction are both available, compile both to one canonical hosting-cost
node, execute exactly one, and let it reach operating profit once. Preserve the
other as a non-executing reconciliation check.

Export observed deferred revenue, receivables, payables,
capitalized-development, billings, collections, leases and depreciation as
named downstream mappings. Do not execute their statement rolls, cash effects,
share denominators, tax, FCF, ROIC or valuation inside this module.

## Conditional rival-input handoff

When requested, material to operating profit or needed to distinguish a named
rival, return changed causal inputs rather than a top-line growth or margin
overlay. Each proposed change carries:

```text
driver_name | cohort_or_service | node_id |
model_cell_or_formula | reference_value | rival_value | unit |
effective_period | lag_periods | affected_output_cells |
evidence_or_rationale | falsification_trigger
```

Retention, effective price, usage unit cost, hosting/support capacity and sales
efficiency are common candidates, not a mandatory taxonomy. Include a dimension
only when it is material to the requested output or named rival, and preserve its economic
meaning: for example retention changes the existing base rather than new logos,
and usage cost cannot silently absorb hosting or support. A missing value for a
material selected input is `human-required`, not zero or a carried ratio. The
coordinator owns any scenario catalog, probability and downstream re-execution.

## RPO and committed contracts

RPO is a visibility schedule, not annual revenue, fixed effective price, or margin protection. Model:

```text
Recognized contract revenue
= committed amount
× actual consumed usage
× recognition timing
× execution / cancellation factor
```

Keep committed-use discounts in the effective-price bridge.

## Regime-tail rule

Upgrade AI or another platform regime tail only when proposition-appropriate
evidence from genuinely independent measurement roots resolves the material
rival explanations. Relevant observations can include material workload
revenue, customer deployment/capex acceleration, constrained infrastructure
commitments or management disclosure of multi-product demand. A thematic TAM
alone cannot establish adoption, economics or Base probability; neither a
fixed signal count nor an E-label grants forecast permission.

## Human-required inputs

Author one blocker for each distinct missing operating construct that changes
the requested result: usage/price scope, hosting/support cost pools, capacity,
customer/cohort state, recognition factor or shared operating-cost allocation.
The blocker names the node, affected output and next evidence. Reference it
from dependent formulas rather than repeating period tables. Missing
balance-sheet, cash, tax, share or valuation inputs are downstream financial
blockers, not operating-module work.

## Failure modes

- usage growth directly equals revenue growth;
- RPO directly equals next-year revenue;
- group capex mechanically assigned to the segment;
- reported margin extrapolated without useful-life normalization;
- serve, hosting-capacity and support costs blended into one unexplained margin ratio;
- a material rival changes only a top-line output rather than its causal node;
- a missing schedule deleted instead of retained as `human-required`;
- cost optimization interpreted as workload destruction;
- a later observed AI regime break backfilled into an earlier published Base;
- FCF, ROIC or valuation claimed inside the operating bundle.
