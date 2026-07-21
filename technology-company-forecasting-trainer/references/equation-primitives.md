# Equation Primitives

These are composable equations, not sector classifications. Select the smallest
set that represents the economics of each material causal branch. Define every
variable, unit, period and recognition basis before using an equation.

The operating capability uses the revenue, cost/profit, inventory/cycle and
selection sections and stops at operating profit.  The integrated-statement
and value-creation continuations are owned by the financial capability; their
presence here does not expand an operating handoff.

## Dimensional discipline

For every row, state whether it is a stock, flow, rate, price, count, capacity,
currency amount or probability. Stocks roll from opening to closing; flows
belong to a period; rates require a denominator and time basis. Never add
quantities with different units or multiply two nominal currency series without
an economic interpretation.

## Revenue primitives

Segment roll-up:

Revenue(t) = sum of segment revenue(t) + eliminations(t)

Unit, price and mix:

Revenue(t) = sum over products of Units(product,t) × Net ASP(product,t)

Demand, share and content:

Supplier units(t) = End-market units(t) × Addressable share(t) × Supplier share(t)

Revenue(t) = Supplier units(t) × Content per unit(t) × Price per content unit(t)

Capacity, utilization and yield:

Saleable units(t) = Nameplate capacity(t) × Utilization(t) × Yield(t)

Revenue(t) = min(Demand units(t), Saleable units(t)) × Net ASP(t)

Orders, delivery and recognition:

Recognized units(t) = sum over cohorts of Orders(cohort) × Survival(cohort) ×
Delivery fraction(cohort,t) × Acceptance fraction(cohort,t)

Installed-base service:

Ending base(t) = Beginning base(t) + New installs(t) − Retirements(t)

Service revenue(t) = Average active base(t) × Attach(t) × Service ASP(t)

Recurring-contract state and recognition:

Ending contract stock(t) = Beginning stock(t) − Churned stock(t) +
Expansion(t) + New stock(t)

Revenue(t) = sum over contract cohorts of Contract value(cohort) ×
Recognition fraction(cohort,t)

Usage and platform:

Revenue(t) = Workloads(t) × Usage per workload(t) × Effective price(t) ×
Monetized share(t)

Subscriber economics:

Ending subscribers(t) = Beginning subscribers(t) + Gross adds(t) − Churn(t)

Revenue(t) = Average subscribers(t) × ARPU(t)

Program-stage conversion:

Expected recognized units(t) = Addressable deployments(t) × Supplier share(t) ×
Stage survival(t) × Timing fraction(t)

Enterprise perimeter:

Reported revenue(t) = Organic comparable revenue(t) + Acquired revenue(t) −
Disposed revenue(t) + FX effect(t) + Recast bridge(t)

## Cost and profit primitives

Unit cost:

Cost of sales(t) = Saleable units(t) × Unit cost(t) + Period costs(t) +
Inventory and under-utilization adjustments(t)

Unit cost must expose material materials, conversion, yield loss, logistics,
royalty, warranty and fixed-cost absorption drivers. Gross margin is an output,
not an input, unless disclosure is insufficient and the temporary ratio carry
is explicitly flagged.

Alternative constructions of one cost pool do not add together.  Declare the
shared canonical cost node, compile every candidate construction to it, select
exactly one for execution and feed that selected output into operating profit
once.  Unselected constructions remain non-executing cross-checks.

Operating profit:

EBIT(t) = Gross profit(t) − R&D(t) − S&M(t) − G&A(t) − other operating items(t)

## Inventory and cycle primitives

Ending inventory(t) = Beginning inventory(t) + Production cost(t) −
Cost of goods sold(t) − Write-downs(t)

Channel inventory is separate from company inventory:

Channel inventory(t) = Beginning channel inventory(t) + Sell-in(t) −
Sell-through(t)

Orders, sell-in, sell-through, usage, inventory, capacity and price are separate
state variables. A cycle call must identify the lead-lag relation, not merely
label a period recovery or downturn.

## Financial continuation: integrated-statement primitives

Working capital:

Ending operating working capital(t) = Beginning operating working capital(t) +
Revenue and cost timing changes(t)

PPE:

Ending net PPE(t) = Beginning net PPE(t) + Capex(t) − Depreciation(t) −
Disposals and impairments(t)

Debt:

Ending debt(t) = Beginning debt(t) + Borrowing(t) − Repayment(t) +
Non-cash and FX changes(t)

Cash:

Ending cash(t) = Beginning cash(t) + CFO(t) + CFI(t) + CFF(t) +
FX effect on cash(t)

The balance sheet must balance, and cash from the cash-flow statement must equal
balance-sheet cash. Acquisition, lease, SBC, deferred tax and minority-interest
bridges must be explicit where material.

## Financial continuation: value-creation primitives

NOPAT(t) = EBIT(t) × (1 − normalized operating tax rate(t))

Reported, normalized and cash tax views remain distinct.

Invested capital(t) = Operating assets(t) − Operating liabilities(t), with a
documented treatment of goodwill, acquired intangibles, leases and excess cash.

ROIC(t) = NOPAT(t) / Average invested capital(t)

Incremental ROIC(t) = Change in NOPAT(t) / Change in invested capital(t)

Reinvestment(t) = Change in invested capital(t), adjusted for acquisitions and
other non-organic changes.

Reinvestment rate(t) = Reinvestment(t) / NOPAT(t)

Fundamental growth(t) = Reinvestment rate(t) × Incremental ROIC(t)

If the business can grow without proportionate balance-sheet capital, identify
the expensed investment, customer pre-funding or intangible capital that
explains it. Do not claim capital-free growth by ignoring economic investment.

## Selection and fallback

Use causal fit, disclosure and dimensional consistency to select primitives.
Do not average equations or assign mechanism weights. If disclosure does not
support a bottom-up branch, ratio carry is a labeled fallback with a sensitivity
range, evidence gap and monitoring trigger. It is never described as causal
knowledge.
