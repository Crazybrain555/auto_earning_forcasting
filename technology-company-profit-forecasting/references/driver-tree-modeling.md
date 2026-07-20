# Driver-tree modeling (the modeling constitution)

This file defines HOW a forecast model is built. Mechanism modules are
decomposition templates used inside this structure - they are never scored,
weighted, or blended. A forecast is one arithmetic tree with evidence on its
branches, not a weighted combination of mechanisms.

Calibration references: sell-side analyst models (华泰-style 分部量价拆分
three-statement models) whose structure this file encodes.

## The seven-layer structure

```
L0 历史基座   Historical base: 3 FY + latest interim, segment-level actuals
L1 终端需求锚 Terminal-demand anchors: external, monitorable series
L2 驱动树     Driver tree: revenue = Σ segments; each leaf = volume × price
L3 单位经济   Unit economics: price - unit cost = unit profit, per leaf
L4 三表联动   Three-statement integration: opex, tax, WC, capex, cash
L5 情景分布   Scenarios/distribution on the MAIN LINE variables only
L6 监测因子表 Monitoring table: every anchor mapped to a trackable series
```

## L0 - The historical base comes first

Before forecasting anything, rebuild the company's OWN disclosed history at
segment level: revenue, yoy, % of total, segment cost, segment gross margin
for at least 3 fiscal years plus the latest interim period. The forecast
columns continue this table to the right - history and forecast share rows,
units, and definitions. If the segment table cannot be rebuilt from filings,
say so explicitly and mark the affected branch `ratio_carry` (see L2).

Hard rule: the first forecast year must reconcile against the most recent
actual (base = last reported FY / LTM). No forecast line may exist without
its historical row.

## L1 - Terminal-demand anchors

Each major branch of the tree hangs from an EXTERNAL, monitorable series -
not from the company's own guidance alone. Examples: global iPhone units ×
ASP (IDC), hyperscaler capex, WFE spend, NAND bit demand, EV deliveries.
Record for every anchor: source, frequency (quarterly preferred), latest
value, and the transmission link into the company line (share %, content per
unit, attach rate). These anchors feed the monitoring table (L6) and the
forward-evidence SignalCards.

## L2 - The driver tree

```
Total revenue
├── Segment A (customer × product line)     basis: volume_price
│     volume → ASP → revenue → unit cost → segment GM
├── Segment B                               basis: subscriber_economics
│     subscribers → ARPU → revenue → contribution margin
├── Segment C (disclosure-limited)          basis: ratio_carry
│     % of total + yoy continuation, flagged as weak
└── New business main line (主线)            basis: capacity_ramp
      capacity → shipments → ASP → revenue  (built from ramp, not from history)
```

Rules:

- Leaves must sum: Σ segment revenue = total revenue (tolerance 1%).
- Every leaf declares its `basis` - the decomposition template used:
  `volume_price` | `capacity_ramp` | `subscriber_economics` |
  `usage_economics` | `orders_backlog` | `program_conversion` |
  `ratio_carry` | `other` (explain).
- `ratio_carry` (占比+同比延续) is allowed ONLY when disclosure genuinely
  prevents a volume/price split, and must be labeled as such - it is a
  weakness declaration, not a modeling choice.
- Mechanism modules map to bases: unit-volume-price-cost → volume_price;
  capacity-utilization-yield → capacity_ramp; recurring-contract-revenue /
  subscriber-content-economics → subscriber_economics; platform-usage-adoption
  → usage_economics; orders-backlog-recognition → orders_backlog;
  program-stage-conversion → program_conversion. One company uses several
  bases at once - one per branch, chosen by the router's selection questions.

## L2b - The main line (主线) is explicit

Every model declares 1-2 main-line drivers: the branches that carry the
thesis (e.g. "AI CCL capacity ramp", "HBM bit share gain"). Requirements:

- The main line is modeled bottom-up from capacity/orders/design-wins - not
  extrapolated from its own (often tiny) history.
- The main line carries the strongest evidence in the pack: capacity numbers,
  signed orders, customer qualification status - E0/E1 where possible.
- The red team MUST attack the main line first; an unchallenged main line is
  an automatic P1.
- Scenario spread (L5) is driven primarily by main-line outcomes, not by
  uniform haircuts on everything.

## L2c - The forecast must bottom out in a physical unit

Every main-line branch terminates in a **physical or contractual unit** that
exists outside the model: bits shipped, wafers, tools, units, subscribers,
workloads, tonnes, licensed seats. Revenue = unit × price. A branch whose
deepest level is a growth rate is not modeled - it is asserted.

Calibration example (Goldman, SNDK): the entire revenue build is two rows -
`NAND GB shipped` and `ASP per 1GB-equivalent` - and the forecast's whole
claim is that ASP moves ~5x while bits grow modestly. Two numbers carry the
report. That is the standard of compression to aim for.

## L2d - Thesis compression: name the numbers that carry the call

The model must identify the **1-3 quantities whose variation dominates the
outcome**, state them in the report's opening, and show a sensitivity around
each (typically ±1 standard case step). Requirements:

- Each carrier is a driver, never an output: "FY+2 NAND ASP $/GB", not
  "FY+2 EPS".
- Show what the carrier must do for the Bear / Base / Bull cases to hold.
- If no small set of carriers dominates, the thesis is diffuse - say so
  explicitly; a diffuse thesis is a legitimate finding, a hidden one is not.

This is the operational meaning of "logic, not scoring": a reader should be
able to disagree with the forecast by disagreeing with a specific number.

## L3 - Unit economics (量价成本五件套)

For every manufacturing leaf, model the five-line unit table:
capacity → volume → price → unit cost → unit profit (and its margin).
Price and unit cost move for stated reasons (mix, pass-through BOM, yield,
utilization) - never as unexplained percentages. Subscription leaves use the
equivalent: subscribers → ARPU → gross adds/churn → contribution.

## L4 - Three-statement integration

Segment gross profits roll up; opex lines are forecast by driver (headcount,
% of revenue with stated operating leverage), then tax, minority interest,
working capital (by DSO/DIO/DPO days), capex/depreciation, and cash.

FY+1 is modeled **quarterly** where the company reports quarterly; the annual
column is the sum of quarters. Every forecast line carries qoq / yoy / % of
revenue diagnostic rows, and the statements must tie through explicit Check
rows (balance sheet balances, cash-flow ending cash equals balance-sheet
cash, quarters sum to the year, GAAP↔Non-GAAP bridge sums).

Full requirements: `references/model-mechanical-integrity.md`. That file is
not optional - a model that does not tie is not a model.

## L5 - Scenarios and distribution

Bear/Base/Bull differ by NAMED main-line assumptions (e.g. Bull: AI CCL
ships 5,000t at 48万/t; Bear: qualification slips two quarters) - not by
±X% on the total. FY+3 is expressed as a distribution (p10/p50/p90) whose
width comes from main-line dispersion plus cycle state.

## L6 - The monitoring table (核心驱动表)

The deliverable includes a monitoring table: every L1 anchor and main-line
assumption mapped to {series, source, frequency, current value, trigger
level, action if breached}. This is the operational form of breakpoints -
a forecast whose drivers cannot be monitored cannot be maintained.

## What replaced mechanism weights

`mechanism_weights` (sum-to-1) is retired as a modeling concept. It made the
method look like factor scoring. The snapshot now carries:

```json
"driver_tree": {
  "main_line": "AI CCL capacity ramp",
  "segments": [
    {"name": "覆铜板-传统", "basis": "volume_price",  "revenue_point": 23100, "main_line": false},
    {"name": "覆铜板-AI",   "basis": "capacity_ramp", "revenue_point": 2500,  "main_line": true}
  ]
}
```

Σ segments.revenue_point must equal outputs.year_1.revenue_point within 1%.
`mechanism_weights` may still appear as optional legacy metadata; it is no
longer validated or interpreted.
