# Core forecast workflow

## 1. Forecast contract

Define entity, security, perimeter, accounting basis, fiscal periods, `as_of`, horizons, output artifacts, intended decision, and readiness target.

## 2. Historical normalization

Build at least three to ten years of comparable financials and operating KPIs where available. Reconcile segments, share count, net debt, working capital, capex, leases, and non-GAAP adjustments.

## 3. Mechanism map

Map each material segment to one or more mechanism modules. Weights must cover 100% of material economics. Do not select a mechanism only because the company belongs to a familiar sector.

## 4. State and regime

Classify each segment using observable signals: price, units/usage, inventory, capacity, utilization, orders, churn, product stage, customer capex, and competitor response. Use probability mixtures when signals conflict.

## 5. Customer, demand and contract-state tree

Identify payer, user, workload/application, deployment unit, usage or units, content, price, attach rate, share, and renewal/churn as relevant. Record unconfirmed customer relationships explicitly.

When recurring or multi-period contracts are material, build the stock-flow bridge in `module-recurring-contract-revenue.md`: beginning recurring base and unrecognized contract stock, renewal, price/seat/usage expansion, new-logo or expansion contracts, stage probability, cancellations/FX/scope changes and recognition timing. ARR, billings, bookings, deferred revenue, backlog, RPO and recognized revenue are distinct measures and may only cross-check one another.

## 6. Supply, delivery, or content capacity

Model the binding constraint: manufacturing, yield, packaging, components, installation, labor, data-center assets, service capacity, content production, licensing, or distribution.

## 7. Operating model

Use selected mechanism equations. Keep quantity/usage, price, mix, cost, recognition timing, perimeter, and accounting bridges separate. Build quarterly one-year forecasts before annualizing.

For recurring-contract companies, the customer/cohort and contract-state rows must feed formulas. Guidance is a reconciliation constraint, not the primary economic equation. If direct cohort or duration data are unavailable, preserve a residual bucket, cap readiness and expand only the affected state uncertainty.

## 8. Financial statements, accounting states and cash

Translate operating drivers into GAAP P&L, working capital, capex/economic capital, debt, cash, share count, and FCF. State allocation methods for incomplete segment disclosure.

Separate recurring pretax economics, recurring tax, discrete GAAP accounting states and cash taxes. Use `module-discrete-accounting-events.md` for bounded event-family state transitions. Use `submodule-dta-valuation-allowance.md` only for DTA/valuation-allowance realizability; impairments, restructuring, litigation and acquisition accounting require their own triggers. Reverse non-cash benefits in FCF and show reported versus recurring/normalized profit.

## 9. Stage gates, scenarios and uncertainty attribution

Route immature products/programs/business models to options or tails until evidence permits Base inclusion. Build Bear/Base/Bull and discrete regime branches. Decompose operating uncertainty from discrete accounting-event uncertainty. Each interval change must map to a named driver or state, amount cap, period, probability and falsification trigger; global range widening is not a valid calibration method.

## 10. Cross-checks

Compare product/segment economics, customer demand/usage, supply/capacity, normalized long-term value, and market-implied requirements. Explain gaps; do not add cross-check outputs to revenue.

## 11. Monitoring

Every assumption must have a next evidence point, upgrade trigger, downgrade trigger, affected periods, and model action.

## 12. Snapshot

Freeze sources, assumptions, formulas, scenarios, conclusions, and hashes. Never edit a published snapshot.
