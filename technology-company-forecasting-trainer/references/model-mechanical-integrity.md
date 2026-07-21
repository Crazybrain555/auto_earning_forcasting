# Model Mechanical Integrity

Mechanical integrity proves that the workbook implements its stated equations.
It does not prove that the evidence or assumptions are good. Report process
integrity and research sufficiency separately.

## Workbook architecture

Use a consistent left-to-right flow:

sources and controls → historical normalization → causal drivers → segment
schedules → statements and roll-forwards → value creation → scenarios →
valuation → checks and monitoring.

Separate inputs, formulas and outputs visually and structurally. Avoid hidden
hardcodes inside formulas, repeated magic numbers, merged-cell calculations,
uncontrolled external links and formulas that silently change across a row.
Document units, sign convention, period basis and accounting basis.

## Typed accounting basis and comparability

`GAAP` is not a usable accounting contract. In `run_manifest.json`, declare a
dated basis record with `basis_id`, `framework` (`US_GAAP`, `IFRS`,
`PRC_GAAP`, or a named `OTHER_LOCAL_GAAP`), jurisdiction, version,
`effective_at`, `presentation_currency`, and sourced `major_policy_choices`.
Use the accounting basis effective for the reported facts and forecast when the
bundle is frozen. Every historical fact names one declared historical basis,
and the forecast snapshot names the forecast basis.

When a historical basis differs from the forecast basis, use a sourced,
quantified comparability bridge by period and financial-statement line. A
qualitative note or a normalized-margin plug is not a conversion. Accounting
policy choices describe recognition and measurement; an accounting policy is
not a company driver parameter, assumption weight, growth rate, or causal-node override.

## Quarterly spine

Where the company reports quarterly, build FY+1 by quarter. Annual values equal
the sum or appropriate average of quarterly values. Show qoq, yoy and percent-
of-revenue diagnostic rails beside material forecast lines. These diagnostics
surface implausible flow-through; they do not become forecast inputs.

For longer horizons, use annual columns only after the near-term recognition,
working-capital and seasonality path is resolved.

## Required zero-valued checks

Create visible check rows that evaluate to zero, or to a documented immaterial
rounding tolerance:

- analytical segments + eliminations − consolidated revenue;
- quarters − fiscal year;
- gross profit from revenue and cost − statement gross profit;
- opening + movements − closing for inventory, working capital, PPE, debt,
  retained earnings and cash;
- assets − liabilities − equity;
- cash-flow ending cash − balance-sheet cash;
- reported-to-normalized bridge;
- sell-in − sell-through − change in channel/customer inventory, shipments −
  production − opening company inventory + closing company inventory, and
  recognized revenue − accepted quantity × realized price for every applicable
  operating-cycle branch;
- revenue − operating costs − operating profit, operating profit + signed
  non-operating items − pretax profit, and pretax profit − signed tax expense
  − non-controlling-interest income − GAAP attributable net income for every
  forecast period;
- enterprise value − equity bridge;
- equity value / valuation-date fully diluted shares − value per share, when
  valuation is in scope;
- for an authored probabilistic scenario set, scenario probabilities − 100%;
  every shock enters through its declared node-compatible unit, workbook
  cell/formula, effective period and lag.

Every scenario-period row must recompute the same full reported-profit chain:
revenue − operating costs = operating profit; operating profit + signed
non-operating items = pretax profit; pretax profit − tax expense = consolidated
net income; consolidated net income − NCI income = GAAP attributable net
income. Bind every layer to an exact model cell or executable formula and bind
every named shock to every affected row. Exactly one freely named scenario has
`role=reference` and reconciles to the integrated statements and canonical
point outputs; each `role=alternative` scenario names a causal shock. Each
published low/high tuple must name one **joint scenario** and
reconcile every layer to that same scenario-period row; independent **marginal
intervals** (that is, marginal intervals assembled independently) may not be
spliced across revenue, `operating_profit_low`/high,
pretax profit, tax, NCI and attributable net income.

Checks cannot be disabled merely because a scenario changes. Any non-zero
check blocks publication until explained and repaired.

`model_checks.json` does not pass because an analyst entered zero and selected
`passed`. Each check binds its signed operands to exact workbook cells. The
runtime reads those cached operands, recomputes the residual, compares it with
the declared residual, and then applies the tolerance. This generic signed-sum
contract covers consolidation, statement and roll-forward conservation without
rewarding a check count or prescribing company-specific rows.

Aggregation has an additional scope contract. State the partition ID and
dimension and explicitly declare exhaustiveness and mutual exclusivity. Only
then may customer/product/region/segment members be required to add to the
parent. Partial top-customer disclosures and overlapping analytical cuts are
not failed for summing below or above 100%; they are barred only from claiming
a parent reconciliation.

## Integrated three statements

The income statement drives retained earnings and operating cash. Working
capital, capex, depreciation, financing and capital allocation drive both the
balance sheet and cash-flow statement. Build explicit roll-forwards for:

- revenue recognition and deferred balances where material;
- receivables, inventory, payables and other operating working capital;
- PPE, depreciation, impairments and disposals;
- debt, interest and financing fees;
- leases, pensions, taxes, minorities and provisions where material;
- ending basic shares, period weighted-average basic/diluted EPS denominators,
  valuation-date fully diluted shares, SBC, issuance and repurchases;
- cash, restricted cash and FX effects.

For a full-company decision memo or a three-year-or-longer forecast or
valuation, the final answer itself must show period rows—not merely workbook
tabs—for the minimum identities below:

```text
closing net PPE = opening net PPE + capex - depreciation - disposals/impairments +/- perimeter/FX
closing operating working capital = opening operating working capital + change
closing debt = opening debt + borrowings - repayments +/- non-cash/perimeter/FX
ending basic shares = opening basic shares + basic issuance - repurchases +/- other basic-share changes
period weighted-average basic/diluted EPS shares = time-weighted in-period basic shares + GAAP incremental dilution for that period
valuation-date fully diluted shares = valuation-date basic shares + economically dilutive options/awards/convertibles on the stated valuation basis
closing cash = opening cash + CFO + CFI + CFF +/- FX = balance-sheet cash
assets = liabilities + equity
```

The first row is a point-in-time capital stock, the second is a period-average
GAAP EPS denominator, and the third is a point-in-time valuation denominator.
Do not roll an "ending diluted share" stock and reuse it for EPS or valuation;
the timing and dilution tests differ.

Each row names its P&L link, CFS link, closing balance-sheet amount and check
residual. Unknown numbers remain `human-required` cells; they do not remove the
row or permit a full-company conclusion.

The reported profit chain is one period-by-period machine contract, not three
similar summaries.  `integrated_model`, `forecast_snapshot.outputs` and
`earnings_power_bridge.csv` must contain every forecast period and agree on
revenue, GAAP operating profit, pretax profit, signed tax expense,
non-controlling-interest net income and GAAP attributable net income.  State
non-controlling-interest net income as explicit zero when absent.  A generic
`financial_role: profit` is not a valid causal-graph destination: the main line
must pass through typed revenue, operating-profit, pretax-profit and tax nodes
and terminate at `gaap_net_income_attributable`.

The GAAP operating-profit row also carries the earnings-quality conservation
bridge: operating profit less operating tax equals NOPAT, and NOPAT equals
after-tax operating free cash flow plus the change in net operating assets.
The residual is recomputed; a qualitative accrual label cannot replace it.

Do not use cash, debt, tax, other income or retained earnings as a balancing
plug. Circular financing must be solved transparently or isolated as an
intentional iterative calculation.

### Narrow-scope materiality exception

A genuinely narrow audit—such as one patent family, one segment, or one
accounting event—that does not forecast or value the whole company may limit
the roll-forwards to economically affected items. It must state the scope, run
a named materiality test with a numeric perturbation and decision threshold,
show the affected statement links, and list blocked full-company conclusions.
Missing disclosure, a read-only request, or a `not-decision-ready` label is not
a scope test. Narrowing the title after beginning a full-company forecast does not waive the full schedule.

## Two independent revenue views

For each thesis carrier, maintain:

1. the primary operating equation used in the statements; and
2. an independently constructed demand, customer, capacity or recognition
   cross-check.

The second view is diagnostic and must not be added to revenue. Investigate
differences through units, scope, timing, price and accounting basis.

## Conditional value-creation identities

When earnings-power, capital-allocation or valuation analysis is in scope, the
workbook must also reconcile:

- ROIC = NOPAT / average invested capital;
- incremental ROIC = change in NOPAT / change in invested capital;
- reinvestment rate = reinvestment / NOPAT;
- fundamental growth = reinvestment rate × incremental ROIC;
- DCF present values and terminal value;
- residual-income book value and abnormal-earnings path.

Acquisitions, divestitures, goodwill, expensed investment and working-capital
funding require explicit bridges before these identities are interpreted.

## Input and formula audit

For every conclusion-critical input verify:

- it is labeled as reported, derived, assumed, scenario or unknown;
- source ID and date are present when evidence-based;
- units and periods match all dependent formulas;
- the formula chain reaches statements and value;
- sensitivity uses a named perturbation;
- no stale hardcode remains in a forecast formula.

Scan for broken references, formula errors, missing sheets, inconsistent signs,
unexplained blank cells and formula-pattern deviations. Recalculate in an
independent engine when practical and inspect cached values before delivery.

## Case-routed stress tests

Select shocks that are material to the requested outputs or discriminate a
named rival.  Common candidates include:

- zero volume or zero new bookings where economically possible;
- capacity or qualification delay;
- adverse price and unit-cost state;
- working-capital and capex shock;
- tax, FX, debt and share-count bridge changes;
- terminal growth and incremental-return limits when valuation is active.

The statements must still close. Impossible outputs such as negative physical
units, utilization above documented capacity, terminal growth at or above the
discount rate, or value generated without required reinvestment must fail a
gate rather than pass silently.

## Review record

Record check ID, formula or invariant, tolerance, observed residual, status,
reviewer and timestamp. A green workbook is reproducible evidence of arithmetic
closure only. Research, causal and valuation gates remain independent.
