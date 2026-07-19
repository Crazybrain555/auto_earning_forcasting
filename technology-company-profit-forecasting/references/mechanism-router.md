# Mechanism router

Modules are composable references inside this single Skill. They are not separate Skills.

## Selection questions

1. What is the revenue-recognizing economic unit: bit, chip, wafer, system, project, usage, subscriber, content license, or transaction?
2. What constrains revenue: demand, capacity, yield, backlog, acceptance, infrastructure, content, customer budget, or stage conversion?
3. What makes margin nonlinear: price cycle, mix, utilization, pass-through BOM, amortization, content cash, churn, or customer concentration?
4. What changes enterprise perimeter or accounting basis?
5. Which mechanism has historical validation, and which remains provisional?

## Module matrix

| Module | Read when | Do not use when |
|---|---|---|
| `module-unit-volume-price-cost.md` | Revenue is units/bits/content × price and cost | Usage/subscriber economics dominate |
| `module-capacity-utilization-yield.md` | Manufacturing capacity/yield/utilization bind | Pure software or content capacity dominates |
| `module-orders-backlog-recognition.md` | Orders, backlog, delivery, installation or acceptance matter | Instant self-serve usage revenue |
| `module-platform-usage-adoption.md` | Usage, workloads, effective price, product mix, customer state and infrastructure drive revenue | Physical units are the only driver |
| `module-recurring-contract-revenue.md` | Subscriptions, term licenses, maintenance, committed usage, deferred revenue, RPO or mixed recurring/upfront contracts are material | One-time physical-unit revenue dominates and contracts do not affect timing |
| `module-subscriber-content-economics.md` | Subscribers, ARPU, churn and content cash/amortization dominate | Hardware unit economics dominate |
| `module-program-stage-conversion.md` | Design wins, custom silicon, optical or long programs | Mature commodity products without project gates |
| `module-contracts-jv-capital.md` | RPO, long-term agreements, JVs or off-balance capital matter | No material contracts/JVs |
| `module-perimeter-and-accounting.md` | M&A, carve-outs, segment changes or non-GAAP bridges matter | Stable organic perimeter and simple accounting |
| `module-discrete-accounting-events.md` | A bounded discrete GAAP event can materially affect profit, balance sheet or cash | Only recurring operating variance is material |

## Recurring-contract routing checks

For enterprise recurring or hybrid software, read `module-recurring-contract-revenue.md` and `lens-enterprise-recurring-software.md`. Require a beginning-base / renewal / expansion-new-logo / contract-stock / recognition bridge. Route usage, upfront IP/hardware and services through their own mechanisms. Add an accounting-transition ledger when the revenue standard, contract model or acquisition perimeter changes. For material discrete accounting events, route through `module-discrete-accounting-events.md`; use `submodule-dta-valuation-allowance.md` only for DTA/valuation-allowance cases.

## Universal modules

Evidence, historical normalization, customer analysis, financial statements, scenarios, valuation, backtesting, governance, and monitoring always apply.

## Platform-specific routing checks

For cloud or usage platforms, separately route:

- usage/workloads;
- effective price and committed-use discounts;
- customer cost optimization / rightsizing;
- infrastructure capacity and utilization;
- reported versus normalized depreciation and operating margin;
- RPO recognition;
- standalone FCF/ROIC allocation gaps.

Do not claim standalone FCF or ROIC when the segment lacks working-capital, lease, tax, cash, or capital-structure disclosures; use `human-required`.

## Subscription/content routing checks

For subscription/content platforms, separately route paid members, average members, ARPU/FX/plan mix, price-churn response, regional maturity, contribution margin, content amortization, cash content additions, obligations, release timing and debt. Exogenous pull-forward must use distribution-only evaluation.

## Compute-platform routing checks

For compute platforms, separately route sell-in/sell-through/channel inventory, market-platform revenue, chip/system/network/software boundaries, foundry/packaging/HBM supply, purchase obligations, acquisitions, GAAP provisions and regime tails.

## Unknown domains

If no validated module combination captures the economic equation, do not choose the nearest industry. Mark `human-required` and propose the missing module and validation plan.
