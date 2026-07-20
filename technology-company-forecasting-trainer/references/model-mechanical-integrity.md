# Model mechanical integrity (Check rows and diagnostic rails)

A model earns trust two ways: the logic is defensible, and the arithmetic
ties. This file governs the second. Calibrated against a Goldman Sachs
US-equity model (SNDK) and the FAST Standard's consistency principles.

The single test: **a reviewer must be able to find every Check row and see
zero.** If a model has no Check rows, it has not been checked.

## 1. Required Check rows

Every delivered workbook carries these reconciliations as explicit rows whose
value is zero (or within stated rounding tolerance). They are formulas, never
typed zeros.

| Check | Formula | Tolerance |
|---|---|---|
| `chk_balance_sheet` | Total assets − (Total liabilities + Total equity) | 0 |
| `chk_cash_tie` | Ending cash (cash-flow statement) − Cash (balance sheet) | 0 |
| `chk_segment_sum` | Σ segment revenue − Total revenue | ≤1% |
| `chk_crosscut_sum` | Σ second-cut revenue − Total revenue | ≤1% |
| `chk_gaap_bridge` | GAAP NI + Σ named adjustments − Non-GAAP NI | 0 |
| `chk_quarter_roll` | Σ quarters − fiscal year | 0 |

A failed Check row is a hard delivery failure, not a warning. Do not "fix" a
Check by hardcoding the difference into a plug line; if a genuine plug is
needed (e.g. interest income computed from average cash), label the row
`PLUG` and state the driver and rate.

## 2. The quarterly spine

FY+1 is modeled **by quarter** whenever the company reports quarterly; the
annual column is the sum of quarters (`chk_quarter_roll`). Reasons:

- The forecast gets falsified or confirmed every 90 days, not every year.
- Seasonality, ramp timing, and inventory corrections live in quarters; an
  annual-only model hides the timing risk that usually breaks a thesis.
- Breakpoint monitoring needs a quarterly cadence to be actionable.

FY+2 may be annual with a quarterly split only for the ramp segments.
FY+3 is annual/distribution. If quarterly disclosure does not exist, say so
in `human-required` rather than inventing quarters.

## 3. Diagnostic rails on every forecast line

Each forecast line carries, as standing rows: **qoq, yoy, and % of revenue**
(or % of the relevant parent). These are not decoration - they are how an
absurd implication becomes visible before it ships. A line whose implied yoy
is +2,108% must be seen and either defended in the report or corrected.

Related required diagnostics:

- **Incremental margin** = Δ gross profit ÷ Δ revenue, shown for every year
  where revenue moves more than ±20%. A commodity upcycle can legitimately
  show ~90-100% flow-through; a diversified business cannot. State which
  regime is assumed and why.
- **Implied CAGR** for FY+1→FY+3 on revenue and on the main-line driver.
- **Implied market share / TAM share** where a total market is known - a
  forecast implying >100% of a market is the classic silent failure.

## 4. Two independent decompositions

Total revenue must be decomposed at least **two independent ways** that both
reconcile to the same total, for example:

- by product / customer (the driver tree of `driver-tree-modeling.md`), and
- by end market (datacenter / edge / consumer) or geography.

Independent cuts catch errors a single tree cannot: if the product tree says
+150% but the end-market cut cannot say which customer segment absorbs it,
the forecast has an unowned assumption. Record both cuts and their Check rows.

## 5. Working capital by days, not by percentages

Balance-sheet forecasting uses operating ratios with physical meaning:
**DSO** (receivable days), **DIO / inventory days**, **DPO** (payable days),
each shown historically and forecast explicitly. Cash conversion follows from
them. A working-capital line forecast as "% of revenue, flat" is acceptable
only for immaterial items, and must be labeled as such.

## 6. Non-GAAP discipline

The GAAP → Non-GAAP bridge is a table with named adjustment lines
(goodwill impairment, SBC, separation costs, termination benefits, tax
effects), not prose. Every adjustment states whether it recurs. Valuation
must state which basis it uses and apply it consistently; SBC is never
silently excluded from the valuation basis without a stated argument.

## 7. FAST-style layout discipline

- One formula per row, copied consistently across all period columns; if a
  column needs a different formula, it needs its own row.
- Inputs (hardcodes) live in dedicated input rows/cells and are visually
  distinct (blue-text convention); calculation rows never mix hardcodes.
- Every hardcoded input carries a source note: filing / call / dataset, date,
  and location.
- No hidden rows or columns in the delivered workbook.
