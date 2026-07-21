# Industry Economics and Cycle

This file is an optional cross-validation input for the `operating_model` and
`causal_graph` stages. Its industry-structure, cycle and profit-pool judgments
enter the forecast only by changing the value or a named scenario of a specific
financial driver; they never independently constitute a conclusion. The
value-investing view of normalized earning power owns the answer, and every
claim admitted from this file must name the financial line and driver it moves
and rest on evidence an independent reviewer can re-check. It is not a sector
scorecard and it does not substitute an industry growth rate for a company
model.

Industry work explains who captures the profit pool, why returns persist or
fade, and which state variables lead the financial statements.

## Map the economic system

Draw the value chain from scarce input through production, distribution,
customer deployment and end-user consumption. For each layer record:

- basis of competition and purchase decision;
- capacity unit, expansion lead time and bottleneck;
- fixed versus variable cost structure;
- price-setting mechanism and contract duration;
- switching, qualification and redesign cost;
- supplier and customer concentration;
- inventory ownership and cancellation rights;
- regulation, standards, complements and substitutes;
- share of industry revenue, gross profit, EBIT and invested capital.

Profit-pool share matters more than revenue-chain position. Reconcile the
company's reported segment economics to the industry map, and state where
unallocated corporate cost, transfer pricing or joint ventures obscure the
comparison.

Declare one boundary ID for product, geography, period, currency and profit
measure.  Within that boundary require one total plus component and explicit
residual rows:

```text
total revenue pool = sum(component revenue pools) + residual
total profit pool = sum(component profit pools) + residual
total invested capital = sum(component invested capital) + residual, when observable
```

Do not mix revenue from one perimeter with profit or capital from another.  A
company's revenue share and profit share are separately calculated; neither is
a moat score.

## Competitive response is an explicit edge

A forecast of high growth or excess returns must model the response it invites:
entry, capacity additions, price cuts, customer dual-sourcing, vertical
integration, product substitution or regulatory action. Specify:

- which rival can respond;
- the economic trigger;
- response cost and lead time;
- the company's barrier;
- the observable sign that the barrier is weakening.

The absence of a response in one historical window is not proof of a moat.

## Select the cycle states that carry the economics

Do not collapse the cycle into one label, and do not replace research with a
universal checklist. Start from the company's profit-pool boundary, main-line
causal paths and serious rival. Ask which stocks, flows, prices, capacity
constraints, recognition events and cash lags can materially change revenue,
operating profit or cash conversion. End demand, usage, sell-through, orders,
inventory, backlog, utilization, yield, capacity, realized price, unit cost and
cash conversion are candidates, not required state families.

A software subscription may need cohorts, usage, contracted backlog,
receivables and service cost but no physical channel inventory. A foundry may
need most of the manufacturing chain. A marketplace may need transactions,
take rate, incentives and settlement balances. Their lags can change across
regimes. The independent research reviewer receives the frozen economic
boundary and judges whether the selected states cover the principal cycle risk
and whether an omitted state could reverse the thesis.

`operating_cycle_register.csv` therefore ships as a header-only register.
Author only selected states and equations; do not pre-populate ten candidate
states, three reusable equations, or `not_material` rows merely to satisfy a
template. An explicit exclusion claim may be recorded when it resolves a real
boundary dispute, but irrelevant states are simply omitted. Absence of a row is
not evidence that the omitted state was researched; that adequacy question
belongs in the independent review.

Every selected material state records its period, frequency, unit,
ownership/location, observation vintage, source ID, DataSeriesRecord ID and
graph node. Every source, series and node must resolve. The state must touch a
main-line carrier, a causal upstream node or a material node in the reconciled
profit-pool boundary. A revised industry series must not overwrite the vintage
used when the evidence bundle was frozen.

Where definitions permit, reconcile the selected stock-flow chain rather than
reading each series alone. Examples include:

```text
sell-in = sell-through + change in channel/customer inventory
shipments = production + opening company inventory - closing company inventory
recognized revenue = accepted quantity * realized price, adjusted for the contract basis
```

Add an `equation_check` row only when that identity carries the selected branch.
The currently machine-recomputable reusable types are
`channel_inventory_roll`, `company_inventory_roll` and
`revenue_recognition`; selecting one never requires the other two. A different
business model should use the relevant general equation primitive rather than
manufacture inventory rows.

Each selected equation records its ID/type, period, operand values and units,
conversion factor, tolerance, residual, workbook check cell or executable
formula, sources, registered data series and graph nodes. The validator
recomputes the residual; a typed zero in `check_residual` cannot hide an
equation that does not close. Additive units must match, and quantity multiplied
by realized price must yield the recognized-revenue unit after the explicit
conversion factor.

If a selected, economically applicable equation cannot be observed, retain
that equation as `disclosure_limited`, explain the missing stock, flow or
acceptance field, and cap the affected conclusion at `screen-grade`. Missing
disclosure is not `not_applicable`, and unrelated observed values cannot stand
in for a material stock-flow identity.

## Capacity and investment clock

Model expansion as a dated chain:

investment approval → equipment or construction order → installation →
engineering qualification → customer qualification → yield ramp → saleable
capacity → shipment → acceptance → revenue → cash.

Every step has a duration, attrition risk and evidence status. Announced capex
is not qualified capacity. Nameplate capacity is not saleable output. Saleable
output is not demand. The same discipline applies to software infrastructure,
content libraries, sales capacity and regulated approvals.

## Cycle-normal earnings

Separate structural growth from inventory and pricing cycles. Estimate:

- mid-cycle volume, price, utilization and unit cost;
- replacement versus growth demand;
- maintenance versus growth capex;
- normalized working capital;
- incremental economics through a full cycle;
- balance-sheet endurance at the adverse state.

Use cycle-normal earnings as a valuation cross-check, not an instruction to
erase a genuine structural transition.

## Industry calibration workflow

Treat these steps as optional calibration, not a required pass. Run them only
when a specific `causal_graph` or `operating_model` driver has a value or cycle
state that industry evidence can discipline, and route each result into that
named driver rather than a standalone industry verdict.

1. Reconstruct historical industry demand, supply, price and inventory.
2. Reconcile company share and mix to those totals.
3. Identify the thesis carrier and the industry's response function.
4. Define cycle states by observable variables rather than narrative labels.
5. Propagate each state through price, utilization, cost, capital and cash.
6. Set monitoring triggers at the earliest observable node.

Files matching references/lens-*.md are optional calibration cases. They may
suggest useful variables and source types, but the general causal and accounting
kernel must work when every lens file is absent.
