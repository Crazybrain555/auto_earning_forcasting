---
name: company-operating-modeling
description: Turn an accepted public-company evidence bundle into a falsifiable causal operating model: industry boundary and profit pool, demand and supply, volume-price-mix-cost equations, capacity and inventory cycles, technology commercialization, segment drivers, rival hypotheses, and monitored assumptions. Use for operating-driver or industry modeling. Do not ingest raw sources or publish final statements and valuation.
---

# Company Operating Modeling

Explain how observable industry and company states become revenue and operating
profit.  The output is a typed, executable operating model—not a factor score,
an industry label or a narrative growth rate.

## System contract

Read `../forecasting-system-contracts/protocol_manifest.json` and the shared
handoff schema.  Apply the kernel's `alternative_path_closure`,
`conditional_analysis_routing` and `minimum_sufficient_presentation`
invariants before selecting a module.

Accept only a `decision_bundle` and `evidence_bundle` carrying an
`orchestrator_acceptance_ref`. The orchestrator resolves source eligibility
and use permissions before handoff; `snapshot_at` is audit identity, not
permission. Follow only the method, reference and validator routes named in
the accepted bundles. Return one candidate `operating_model_bundle` to the
orchestrator for validation and acceptance. Bind every factual input to
evidence record IDs; do not replace records with a narrative summary or open a
parallel source channel.

## Build the smallest causally sufficient model

1. Define the economic boundary before company equations: end demand, payer and
   user, customer/channel layers, substitutes, complements, suppliers,
   capacity, inventories, regulation, price formation and cash conversion.
   Locate where profit and bargaining power can migrate.
2. State the principal contradiction, the smallest thesis-carrying paths and a
   serious rival.  Common counts are not caps.  Add a path only if it changes a
   material revenue or operating-profit distribution or distinguishes the
   rival.
3. Select equations from economics, not sector identity: volume × price × mix,
   capacity × utilization × yield, installed base × usage × price, backlog ×
   conversion, subscribers × ARPU, cohort retention, milestone conversion or
   another dimensionally explicit mechanism.
4. When two constructions are alternatives—an all-in observed cost versus a
   decomposed cost, for example—declare one alternative-path set and one
   canonical output node.  Compile every candidate path to that same node,
   select exactly one path for execution, and prove that its output reaches
   operating profit once.  Unselected paths are diagnostics and do not execute.
   This prevents both orphan equations and double counting without forcing one
   economic decomposition on every company.
5. Separate demand, supply, price, mix, unit cost and fixed-cost absorption.
   Represent material stocks and lags—inventory, capacity under construction,
   backlog, qualified programs, installed base or deferred revenue—before
   predicting their flows.
6. Reconcile segment/customer/product branches to company totals without
   double counting.  `ratio_carry` is a disclosed limitation, not a default
   forecast method.
7. Only when technology is material to the requested profit output or needed
   to distinguish a named rival, keep feasibility, replication, manufacturing,
   qualification and commercial gates separate.  Do not instantiate a
   technology checklist for an immaterial or non-technology branch.
8. When explicitly requested or material to the requested output, put
   uncertainty on named inputs and propose causal shocks for the main rival.
   The coordinator owns any final joint scenario set, probabilities and
   independent red team; otherwise omit scenario scaffolding.
9. Define monitors as observation, date, threshold and model action.  If the
   accepted evidence cannot identify a parameter or state, return an
   `evidence_request`; do not browse around the evidence boundary or invent it.

## Capability routes

When the accepted bundles route this capability into a compatible coordinator
installation, use only the minimum needed subset of:

- `references/driver-tree-modeling.md`
- `references/equation-primitives.md`
- `references/mechanism-router.md`
- `references/industry-economics-and-cycle.md`
- `references/technology-commercialization-and-ip.md` when material
- the minimum relevant operating `references/module-*.md` named by the router;
  perimeter/accounting and discrete-event modules are downstream financial
  continuations, not operating execution; optional `lens-*.md` only as
  calibration examples
- `scripts/validate_model_graph.py`

## Boundary

Do not mutate source records, normalize accounting facts, choose a balancing
plug, finish the three statements, set a valuation conclusion or publish the
snapshot.  Preserve an unsupported branch as `human-required` and identify the
specific evidence that could resolve it.  Stop the executable graph at the
canonical operating-profit handoff; statement, share, scenario-probability,
fade and valuation execution belong to their owning capabilities.  Keep the
machine bundle complete, but show a human only the requested equations,
material rival and earliest blockers.  Author a blocker once and pass its
reference downstream rather than restating it throughout the answer.
