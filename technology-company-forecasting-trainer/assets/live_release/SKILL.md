---
name: technology-company-profit-forecasting
description: Coordinate current-evidence-backed public-company operating, revenue, GAAP-profit, cash-flow, earnings-power, valuation and monitoring work across the company-evidence-research, company-operating-modeling and company-financial-forecasting specialist skills. Use for current-company forecasts, model builds or updates, investment memos and audits.
---

# Technology Company Profit Forecasting

Coordinate one causal, value-investing model of future revenue, operating profit
and GAAP attributable net income.  The specialist skills do the professional
work; this skill owns model identity, handoffs, joint scenarios,
independent challenge, readiness and immutable publication.

This production coordinator supports `live_forecast` and `audit_only`.  It uses
all relevant current evidence obtainable through the evidence/model bundle
freeze and publishes a new version whenever material evidence changes.

## Canonical authority

Read `references/research-sop.md`, `references/analysis-kernel.md` and
`assets/method_system.json`.  The SOP is the only stage order.  Read the sibling
`forecasting-system-contracts` handoff schema, then route each owned stage to:

- `company-evidence-research` for dated sources, observations, financial facts,
  bounded claims, conflicts and evidence permissions;
- `company-operating-modeling` for industry boundary, profit pool, cycle,
  causal graph, volume/price/mix/cost equations and commercialization;
- `company-financial-forecasting` for comparable history, integrated statements,
  attributable profit, cash/capital/share rolls, earnings power and valuation.

The evidence specialist applies `references/data-quality-and-triangulation.md`;
the coordinator does not recreate that contract.

Do not repeat a specialist's reasoning in the coordinator.  If a downstream
capability finds an upstream gap, return a typed evidence request or rejected
handoff and version the affected bundle.

## Execution

1. Record the user decision, entity/security, consolidation perimeter,
   accounting basis, fiscal calendar, currency, forecast horizons, initial main
   view, serious rivals and largest unknowns. The runtime records a snapshot
   timestamp automatically. Keep accepting current evidence until the
   evidence/model bundle is frozen.
2. Initialize with `scripts/scaffold_delivery.py`.  Follow
   `references/full-company-delivery-contract.md` and
   `references/codex-parity-execution.md`.
3. Ask `company-evidence-research` for an `evidence_bundle`.  It must preserve
   raw and normalized values, actual availability and vintage, original source
   roots, proposition-specific permissions, conflicts and missing evidence.
4. Give accepted evidence IDs—not a narrative rewrite—to
   `company-operating-modeling`.  Receive an executable causal/operating model
   with the smallest causally sufficient thesis paths, a serious rival, named
   input uncertainty and monitors.
5. Give both accepted bundles to `company-financial-forecasting`.  Receive a
   formula-driven `model/model.xlsx`, the full revenue → operating profit →
   pretax → tax → consolidated net income → NCI → attributable-net-income
   chain, statement rolls, `earnings_power_bridge.csv`, routed
   `internal_intangible_investment.json`, and valuation views.
6. Author one freely named `role=reference` scenario and the material
   `role=alternative` shocks.  Re-execute every joint path through the same
   operating and financial model; never splice marginal output ranges.
7. Freeze evidence and model before an isolated red team attacks the main line
   and creates its own rival.  Preserve disagreement before the builder replies.
8. Run `scripts/validate_research_completeness.py`,
   `scripts/validate_model_graph.py`,
   `scripts/validate_investment_case.py` and
   `scripts/validate_delivery.py --strict`.
9. Publish with `scripts/publish_live_forecast.py --workspace <workspace>`.
   It accepts a new immutable snapshot only when its evidence, operating and
   financial bundle hashes match the strictly validated input pack. A material failure yields
   `not-decision-ready` with the exact blocker and next evidence, never a prose
   workaround or a silently lowered standard.

## Minimum integrated three-statement schedule

For every full-company decision and every three-year-or-longer forecast or
valuation, use `references/model-mechanical-integrity.md` and
`references/core-output-and-valuation.md`.  They require period-by-period PPE,
working-capital, debt, cash, equity and diluted-share rolls; CFO + CFI + CFF +
FX to cash; assets = liabilities + equity; and the complete reported-profit
chain.  Missing disclosure is `human-required`, never zero or a balancing plug.

The **Minimum decision-memo tables** also route to Patent / IP diligence,
Recurring / usage economics, the Value-creation identity and Executable
monitoring when material.  `not-decision-ready does not waive` those schedules.

## Earnings power, value and output

Use `references/earnings-power-and-mean-reversion.md`,
`references/internal-intangible-investment.md`,
`references/business-quality-and-moat.md`,
`references/valuation-and-market-expectations.md` and
`references/core-output-and-valuation.md` through the financial specialist.
Reported, normalized and cash earning power remain distinct.  Mean reversion is
conditional on cycle, competition, reinvestment and fade; reference classes are
priors, not copied parameters.

Each period reconciles `revenue_point`, `operating_profit_point`,
`pretax_profit_point`, `tax_expense_point`,
`noncontrolling_interest_net_income_point`, `net_income_point` and
`profit_point`.  The last two are GAAP net income attributable.  Value executed
outcomes, reconcile enterprise to equity and diluted shares, and reverse the
market price into named operating requirements.

## Assurance and judgment

Deterministic checks own types, hashes, mode/snapshot consistency, dated
availability and vintage lineage, stable IDs, structured bridges,
equation execution and accounting identities.  Independent agents judge causal
adequacy, source meaning/noise, rival mechanisms, paper-to-production transfer,
cycle, moat, persistence and investment relevance.  Tests are orthogonal views,
not weights or a completeness score; validators are a safety net, not the SOP.

Treat the method package as a versioned production release.  Case work may
produce evidence, models, snapshots and evidence requests, but it never edits
the released method in place.
