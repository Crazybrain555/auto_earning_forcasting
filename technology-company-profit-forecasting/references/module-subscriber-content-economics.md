# Module: subscriber, pricing, churn, acquisition, and content economics

**Validation scope:** calibrated for subscriber revenue and operating income.
This operating module stops at operating profit. It exports content-asset,
liability and cash-timing mappings; the financial capability owns cash flow,
debt, shares, FCF, ROIC and valuation.

## Applies to

Subscription and content platforms where paid users, plan price, churn, regional maturity, content release capacity, and capitalized content economics drive revenue and profit.

## Core revenue equations

```text
PaidSubscribers_end[r,p]
= PaidSubscribers_begin[r,p]
+ GrossAdds[r,p]
- VoluntaryChurn[r,p]
- InvoluntaryChurn[r,p]
± PlanMigration[r,p]

Revenue[r,p]
= AveragePaidSubscribers[r,p]
× EffectiveMonthlyARPU[r,p]
× 12
+ Advertising / licensing / other revenue[r,p]
```

Where precise gross adds and churn are not disclosed, do not reverse-engineer exact retention from net additions. Use cohort ranges and mark `human-required`.

## Required separations

1. Region and maturity: mature, scaling, newly launched, or exogenous-pull-forward.
2. Plan and price: list price, plan mix, partner bundles, FX, taxes, advertising, paid sharing, and discounting.
3. Acquisition and churn: gross adds, voluntary churn, failed-payment churn, reactivations, and release-seasonality.
4. Contribution economics: delivery, payment processing, support, partner payments, marketing/customer acquisition, and regional contribution margin.
5. Content economics: licensed versus produced content, release slate, cash additions, amortization, liabilities, off-balance obligations, residuals, and write-offs.
6. Downstream timing mappings: content assets/liabilities, cash payment timing
   and working-capital effects, without executing financing or cash flow here.

## Content expense and downstream cash mapping

```text
Reported content expense
= Licensed-content amortization
+ Produced-content amortization
+ Residuals / participations
+ Other delivery costs

Cash content investment
= Cash additions to content assets
+ Change in content liabilities
+ Cash production / licensing payments

Cash-content gap
= Cash content investment - Content amortization
```

Never treat content amortization as cash content spending. Preserve reported
operating expense and the cash-content timing mapping side by side, then hand
the mapping to the financial capability rather than calculating FCF here.

## Content cohort logic

For material slates or regions, track:

- content available date and release cadence;
- licensed versus produced;
- expected viewing decay and amortization window;
- regional/global rights;
- marketing support;
- renewal, sequel, or franchise option;
- cash payment schedule;
- contribution to acquisition, retention, ARPU, or advertising.

If title-level economics are unavailable, use portfolio-level content-spend, amortization, obligations, and regional maturity ranges. Do not invent title ROI.

## Price and churn response

A price increase must include:

```text
Net revenue effect
= Price uplift
× Retained subscribers
± Plan migration
± FX / bundle changes
- Incremental churn and acquisition replacement cost
```

Do not apply price increases without a churn or plan-mix response.

## State machine

- Expansion: high gross adds, stable churn, new regions/plans.
- Maturity: slower net adds, ARPU and engagement become more important.
- Content-slate disruption: release timing or production interruption changes acquisition, churn, amortization, and cash payments.
- Price reset: ARPU rises but churn/plan migration must be tested.
- Exogenous pull-forward: demand shock moves future adoption into the current
  period; return it as a named rival input when it remains unobserved at bundle
  freeze. The coordinator decides whether to author a distribution.
- Model transition: advertising, paid sharing, games, live events, or bundles require separate stage gates.

## Forecast permissions

- Net additions alone may anchor only near-term paid-membership movement, not exact churn.
- Deferred monthly membership fees are near-term timing items, not multi-year backlog.
- Content obligations are commitments, not future revenue.
- A new plan or monetization model enters Base only after launch plus observable adoption or revenue.
- Exogenous shocks unobserved at bundle freeze remain rival or tail inputs, not
  point facts. Current observations continue to enter until that freeze.

## Required outputs

- paid membership and ARPU bridge by region/plan where disclosed;
- reported operating profit and regional contribution economics;
- content amortization, cash content additions and obligations as downstream
  timing mappings;
- price/churn sensitivity;
- mature versus scaling-region mix;
- a material exogenous-shock or model-transition rival input when applicable;
- human-required TODOs for undisclosed churn, title economics, and content allocation.

## Failure modes

- permanent exponential subscriber growth;
- inferring churn exactly from net additions;
- blending mature and new regions;
- price increases without churn response;
- treating amortization as cash spending;
- ignoring content obligations or claiming downstream FCF/valuation inside the
  operating module;
- treating pandemic or other exogenous pull-forward as a normal Base forecast;
- using later advertising or paid-sharing success to rewrite an earlier
  published forecast.
