# Module: recurring-contract revenue state and recognition

Use when a material portion of revenue is created by subscriptions, term licenses, maintenance/support, committed usage, multi-year agreements, deferred revenue, backlog or RPO. This is a stock-flow and state-transition module, not a rule to raise growth for every software company.

## 1. Contract-type decomposition

Classify material revenue into ratable subscription/term license, maintenance/support, usage/consumption, upfront license/IP/hardware/royalty, professional services, and acquired/migrated/accounting-transition cohorts.

Contract value, billings, backlog, deferred revenue, RPO, bookings, ACV, ARR, usage and recognized revenue are different states or flows. Never add them.

## 2. Required stock-flow equations

For each material contract type and, where disclosed, customer cohort:

```text
Retained recurring value_t
= beginning eligible recurring base_t
× renewal probability_t
× price / seat / usage expansion_t

New recognized recurring revenue_t
= new-logo or expansion contract value_t
× stage / close probability_t
× period recognition fraction_t

Recognized recurring revenue_t
= retained recurring value recognized in period
+ new recognized recurring revenue_t
+ permitted catch-up / variable-consideration adjustments_t

Ending unrecognized contract stock_t
= beginning unrecognized contract stock_t
+ signed contract additions_t
- cancellations / FX / scope reductions_t
- recognized contract revenue_t

Reported revenue_t
= recognized recurring revenue_t
+ upfront product / IP / hardware revenue_t
+ usage revenue_t
+ services revenue_t
+ permitted accounting-transition adjustments_t
```

Customer demand, contract stock, billings/deferred and reported revenue are cross-checks, not additive models.

## 3. State transitions

- `C0` prospect/no contract;
- `C1` qualified opportunity;
- `C2` signed but not started;
- `C3` live/partially recognized;
- `C4` renewal, expansion or contraction;
- `C5` churn, cancellation, migration or collection risk.

A new accounting standard, pricing model, contract migration or acquisition integration needs a separate transition ledger. Do not infer organic demand from a recognition shift.

## 4. Evidence permission

- E0/E1 filings, contract notes, official KPI definitions, audited deferred revenue/RPO and official guidance may anchor the bridge.
- Official customer/partner evidence may change stage probability after perimeter and independence checks.
- Measured independent research may change a driver only after corroboration.
- Sales anecdotes, unnamed pipeline claims, search snippets and duplicated commentary are monitoring signals only.
- Missing cohort, duration, cancellation or recognition data require an explicit residual and lower readiness; do not invent customer names or shares.

## 5. Technology-inflection expansion floor

When observable evidence at `as_of` shows a technology inflection driving structural demand acceleration for the recurring product set, the Base expansion rate for FY+2 and FY+3 must not fall below the inflection-driven floor. This rule prevents anchoring on pre-inflection historical averages when the demand driver has demonstrably shifted.

**Applicability.** All three conditions must hold:

1. A named technology transition is in progress (e.g., major semiconductor node shift, new design-methodology requirement, platform migration) with E0/E1 evidence of customer adoption at `as_of`.
2. The transition creates incremental, measurable demand for the recurring product (more seats, higher complexity per design, new tool attach) — not merely a general narrative of "growth."
3. At least two independent forward signals (design starts, customer disclosures, order patterns, official guidance citing the transition) corroborate accelerating adoption as of the cutoff.

**Rule.** When applicable, set the FY+2 and FY+3 Base expansion rate at or above the higher of (a) the trailing four-quarter organic expansion rate and (b) the inflection-driven floor implied by the measured adoption signals. The floor is not a point estimate — it sets the lower bound of the Base case; upside scenarios may exceed it.

**Failure conditions — do not apply when:**

- the transition evidence is analyst commentary or model memory only (no E0/E1 anchor);
- the product's share of the inflection is unquantified or speculative;
- the customer base is concentrated enough that one delayed program would remove the floor;
- the inflection is a one-time migration (e.g., ASC 606 transition) rather than a sustained demand expansion.

## 6. Permission and uncertainty

- Guidance is an output constraint and management belief, not the revenue equation.
- Beginning base, renewal, expansion/new logos, price/usage, stage probability and recognition timing are separate parameters.
- RPO/backlog raises visibility only after survival and timing; it does not establish price, margin or collection.
- Upfront and ratable revenue have distinct margin/cash profiles when material.
- Attribute uncertainty to the relevant state or driver; do not widen all lines/years uniformly.
- FY+1 point precision requires a bridge that explains a substantial, decision-relevant share of revenue and reconciles to official guidance/run rate.
- FY+2 shows renewal/expansion and recognition breakpoints; FY+3 is distribution-first when cohort/duration evidence is weak.

## 7. Workbook and registers

Include product × customer group × contract type × quarter, beginning recurring base, unrecognized contract stock, renewal/expansion/new logos, price/usage, stage conversion, billings/deferred/RPO reconciliation where disclosed, recognition by revenue type, cancellations/FX/scope, margin/cash differences, source permission, materiality, sensitivity and falsification trigger.

## 8. Coverage and residual diagnostics

Calculate:

```text
explained_revenue_share
= revenue generated by explicit driver rows / modeled revenue

sensitivity_weighted_residual
= unexplained revenue share × sensitivity of the conclusion to that residual
```

An 80% explained share and 10% unexplained residual are useful default warning thresholds for a reasonably disclosed business, not universal hard gates. Tighten or relax them only with a documented reason based on disclosure quality, concentration, business mix and decision sensitivity.

Cap readiness or fail the mechanism when:

- customer/product rows do not feed formulas;
- a material residual is unnamed or unsensitized;
- contract value is treated as recognized revenue;
- ARR, billings, RPO and revenue are added;
- one renewal/growth rate is applied to heterogeneous cohorts without evidence;
- an accounting transition is called organic demand.
