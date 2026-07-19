# Full-company delivery contract

## Trigger

Apply when the request asks for a company forecast, financial model, three- to five-year revenue/profit forecast, valuation, customer/supply analysis, or a durable research package.

## Required artifacts

A complete delivery contains:

```text
<entity>_financial_model.xlsx
<entity>_forecast_report.md
run_manifest.json
source_manifest.json
assumption_register.csv
red_team.md
forecast_snapshot.json
```

A narrative-only answer does not satisfy a full-model request.

## Workbook concept requirements

Sheet names may vary, but the workbook must contain these concepts:

1. Executive summary / current market anchor.
2. Source Pack and evidence tiers.
3. Historical actuals and current-year bridge.
4. One-year quarterly operating model.
5. Driver and assumption schedules.
6. Three- to five-year GAAP operating model.
7. Cash flow, working capital, capital intensity, and share-count bridge.
8. Customer, demand, supply/capacity, contracts, products/programs, and stage gates as relevant.
9. Bear/Base/Bull and regime/perimeter tails.
10. Cycle/growth-path and normalized valuation.
11. Market-implied reverse model.
12. Monitoring triggers and formula/quality checks.
13. Run/delivery manifest or equivalent audit sheet.

The model must use formulas for derived outputs and link assumptions from dedicated schedules. Calculated forecast lines may not be manually retyped across sheets.

## Minimum report structure

1. Information cutoff, current price timestamp, model basis, and readiness.
2. Investment conclusion and what the market price requires.
3. Historical/current-year bridge.
4. Base forecast table.
5. Segment/customer/product drivers.
6. Supply, capacity, delivery, or content constraints.
7. Contracts, product/program stages, and enterprise perimeter.
8. GAAP, cash flow, capital intensity, and share count.
9. Bear/Base/Bull and regime tails.
10. Near-term and normalized valuation.
11. Reverse-implied expectations.
12. Changes from the prior model, when applicable.
13. Key monitoring triggers, kill/upgrade evidence, and human-required items.
14. Source IDs or citations.

## Evidence minimum

For a current public-company model, normally require:

- latest statutory filing;
- latest earnings release/call or shareholder letter;
- at least two historical filings or recast sources for comparability;
- official product/customer/contract/capacity evidence where material;
- current market price with source and timestamp;
- E2/E3 evidence only where it adds technical or industry bounds.

If the minimum is unavailable, publish `not-decision-ready` or `screen-grade` and list the missing items.

## Model quality gates

Before delivery:

- revenue segments sum to total in all forecast periods;
- COGS/gross profit/operating profit/net income bridges tie;
- cash roll-forward ties;
- share count and repurchases tie;
- scenario probabilities equal 100%;
- Bear < Base < Bull for core economic outputs unless a documented non-monotonic mechanism exists;
- normalized-value assumptions do not simply reuse peak-cycle margins;
- cross-check demand is not added to product revenue;
- contracts/RPO do not imply undisclosed price or margin protection;
- samples, design wins, qualifications, and awards obey stage gates;
- no future source is used before a historical `as_of` cutoff;
- formula errors are zero;
- unresolved P0 issues are disclosed and readiness is capped.

## Artifact style

- Facts/links and analyst inputs must be visually distinguishable.
- Tables use explicit units, fiscal periods, and accounting basis.
- Negative values and percentages use consistent formats.
- Long narratives belong in the report, not inside formula schedules.
- The executive summary should show the model's first failure point, not only the upside case.

## Final response contract

The chat response should summarize the conclusion, the five-year table, current valuation, major changes, readiness, and link all artifacts. It should not claim Codex and another model will produce identical numbers; it should state that the deterministic workflow and validators reduce variance while tools, source access, and judgment can still differ.


## Forward evidence synthesis
A full forecast must document investor dialogue, cross-company official read-through, independent measurements/research, named-expert evidence and relevant papers/standards. SignalCards must show accepted, rejected and conflicting signals, independence clusters, permissions and falsification triggers. Papers do not directly create company revenue, share or margin.


## Research-sufficiency gate

Before operating-model construction, complete `research-completeness-and-company-quality.md`. A full forecast must include the research-coverage matrix, company-quality/moat register, technology-commercialization register, product/customer driver schedule and material-assumption support table.

The minimum source count does not authorize tiny summaries. Three historical filings must be full documents or substantial anchored extracts, and the accepted corpus must be deep enough to cover statements, segments, products, customers, technology, management, accounting and cash.

If a critical mechanism variable is Human-required, cap the horizon contract and readiness. For channel hardware with unknown current sell-through/inventory, FY+2 and FY+3 are scenarios/distributions rather than high-confidence points.
