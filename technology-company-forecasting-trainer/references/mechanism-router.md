# Equation-Primitive Router

Read references/analysis-kernel.md and references/equation-primitives.md first.
This router selects implementation modules for individual causal branches. It
does not classify the whole company, score mechanisms or require an industry
lens.

The operating capability routes unit/price/cost, capacity, orders, usage,
recurring, subscriber and program/contract modules and stops at operating
profit. `module-perimeter-and-accounting.md` and
`module-discrete-accounting-events.md` are financial-continuation modules; the
operating capability may name a downstream mapping or evidence gap but does not
execute those modules.

## Selection questions

For each material branch ask:

1. What physical, contractual, installed-base, subscriber or usage unit causes
   revenue?
2. What limits that unit: end demand, share, capacity, yield, qualification,
   orders, delivery, acceptance, churn, infrastructure or contract rights?
3. What determines realized price and mix?
4. What determines unit, cohort or service cost?
5. What lag separates demand, production, recognition and cash?
6. What changes enterprise perimeter or accounting basis?
7. Which disclosures support the equation, and which inputs remain assumptions?

Choose the smallest set of modules that answers those questions.

## Module matrix

| Module | Economic equation or state | Required distinction |
|---|---|---|
| module-unit-volume-price-cost.md | units or content × net price; unit-cost bridge | volume, price, mix and cost |
| module-capacity-utilization-yield.md | capacity × utilization × yield, capped by demand | nameplate, qualified and saleable capacity |
| module-orders-backlog-recognition.md | order cohorts → delivery → installation or acceptance → revenue | orders, backlog, shipment and recognition |
| module-platform-usage-adoption.md | workloads × usage × effective price × monetized share | demand, optimization, price and infrastructure |
| module-recurring-contract-revenue.md | recurring-contract state and recognition | beginning base, renewal, expansion, new stock and recognition |
| module-subscriber-content-economics.md | average subscribers × ARPU with churn and content economics | subscriber state, revenue and content cash |
| module-program-stage-conversion.md | addressable deployments × share × stage survival × timing | design, qualification, award, ramp and recognition |
| module-contracts-jv-capital.md | contract quantity/price/rights plus execution and capital obligations | commercial protection, recognition and funding |
| module-perimeter-and-accounting.md | organic + acquired − disposed + FX/recast and GAAP bridges | economics, perimeter and accounting |
| module-discrete-accounting-events.md | eligible amount × bounded event state × recognition fraction | recurring operations, reported effect, normalized effect and cash |

Installed-base service and inventory/cycle equations are defined in
references/equation-primitives.md and may combine with several modules.

## Routing rules

- Route per branch, never by sector label.
- Use several modules only when they represent different linked states; never
  blend their outputs with analyst-assigned weights.
- Preserve one accounting-recognition path for each revenue line.
- Map every module input to a causal node, source or explicit assumption.
- Export canonical revenue, cost and operating-profit nodes once after branch
  roll-up; the financial capability calculates consolidated statements.
- If disclosure prevents a causal equation, use labeled ratio_carry with a
  sensitivity range and readiness cap.
- If no module captures a material equation, mark human-required and specify
  the missing variable, evidence and validation plan.

## Recurring contracts

When subscriptions, term licenses, maintenance, committed usage, deferred
revenue or RPO are material, read module-recurring-contract-revenue.md. Build a
beginning-base, renewal, expansion/new-logo, contract-stock and cohort
recognition bridge. Usage, upfront hardware or IP, services and discrete
accounting transitions retain their own equations. Never add ARR, billings,
backlog, deferred revenue, RPO and recognized revenue as though they were
independent revenue streams.

## Optional industry calibration

Files matching references/lens-*.md may suggest variables, lags and sources.
They are optional calibration examples. The module choice must be justified by
the active branch's economics and evidence, and the Live method must remain
complete without any lens.
