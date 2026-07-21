---
name: company-financial-forecasting
description: Convert accepted evidence and an executable operating model into reconciled public-company historicals, integrated income statement/balance sheet/cash flow forecasts, GAAP attributable net income, earnings power, reinvestment and fade, valuation, and market-implied expectations. Use for financial-model construction or audit. Do not collect raw evidence or redesign operating causality without a returned handoff.
---

# Company Financial Forecasting

Translate the operating model into period-by-period revenue, operating profit,
cash and GAAP net income attributable without losing accounting basis,
ownership or causal meaning.  Valuation is downstream of the operating and
financial forecast, not a substitute for it.

## System contract

Read `../forecasting-system-contracts/protocol_manifest.json` and the shared
handoff schema.  Apply the kernel's `share_basis_separation`,
`conditional_analysis_routing` and `minimum_sufficient_presentation`
invariants before expanding the requested output.

Accept only a `decision_bundle`, `evidence_bundle` and
`operating_model_bundle` carrying an `orchestrator_acceptance_ref`. The
orchestrator resolves source eligibility and use permissions before handoff;
`snapshot_at` is audit identity, not permission. Follow only the method,
reference and validator routes named in the accepted bundles. Return one
candidate `financial_forecast_bundle` to the orchestrator for validation and
acceptance. Use only bound evidence facts and operating equations; do not open
a parallel source or result channel.

## Integrate economics and accounting

1. Reconstruct comparable reported history before forecasting: segments and
   eliminations; revenue; costs; operating profit; pretax; tax; consolidated
   net income; NCI; attributable net income; working capital; PPE; debt; cash;
   ending basic shares and disclosed period EPS denominators.  Restatements and
   perimeter changes remain dated.
2. Continue the accepted operating equations into forecast periods.  The first
   forecast period bridges numerically from the latest comparable actual; do
   not insert unexplained CAGR, margin, tax or cash-flow plugs.
3. Execute one coherent reference path through revenue, operating profit,
   pretax, tax, consolidated net income, NCI and GAAP attributable net income.
   Execute additional named joint paths only when the coordinator supplies
   them because they are requested, material to the profit output or needed to
   distinguish a serious rival.  Do not manufacture a scenario catalog or
   probabilities to fill an otherwise irrelevant template.
4. Roll PPE/depreciation, operating working capital, debt, cash, equity and
   ending basic shares.  Separately calculate period weighted-average basic and
   diluted shares for GAAP EPS, and valuation-date fully diluted shares for
   equity value per share.  These are different time bases and never share a
   closing-stock equation.  Reconcile CFO + CFI + CFF + FX to cash and assets
   to liabilities plus equity.  A generic formula or worksheet name is not a
   completed schedule.
5. Keep reported, normalized and cash earning power distinct.  Explain
   accruals, temporary investment, cost asymmetry, cycle state, internal
   intangibles, reinvestment, incremental ROIC, competition, conditional mean
   reversion and fade only when those modules are material to the requested
   profit horizon or valuation.  Reference classes are priors, not copied
   parameters; do not instantiate them merely because a schema supports them.
6. Close NOPAT to after-tax operating free cash flow and change in net operating
   assets when cash earning power or valuation depends on it.  Activate
   valuation only when requested or decision-material; choose one fit-for-
   purpose primary method and add a second method only when it contributes a
   distinct diagnostic.  When active, reconcile enterprise to equity and the
   valuation-date fully diluted denominator, then reverse the market price into
   named operating requirements.
7. Missing disclosure remains `human-required` and blocks the affected output.
   If the operating mechanism or evidence is inadequate, return the relevant
   bundle for revision rather than silently changing another capability's work.

## Capability routes

When the accepted bundles route this capability into a compatible coordinator
installation, use only the minimum needed subset of:

- `references/model-mechanical-integrity.md`
- `references/earnings-power-and-mean-reversion.md` when earnings persistence,
  cycle normalization or a multi-period valuation is material
- `references/internal-intangible-investment.md` when material
- `references/business-quality-and-moat.md` when persistence or capital
  allocation is material
- `references/valuation-and-market-expectations.md` and
  `references/core-output-and-valuation.md` only for a valuation, investment
  decision or output contract that depends on them
- `scripts/workbook_contract.py`
- `scripts/validate_investment_case.py`
- the accounting and delivery checks routed by the coordinator

## Boundary

Do not ingest unregistered sources, reinterpret an expert quote as a measured
input, rewrite the causal graph to make statements close, or publish the
immutable final snapshot. Surface the earliest failing handoff and its
financial consequence. Persist complete machine schedules and
lineage, but keep the human answer to the smallest set of rows and explanations
needed for the requested revenue, operating-profit, attributable-profit or
valuation conclusion.  Author a blocker once at the earliest failure and use
its reference in dependent schedules instead of repeating the same paragraph or
placeholder table.
