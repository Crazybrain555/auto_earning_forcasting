---
name: technology-company-forecasting-trainer
description: Train, evaluate, audit, and release the multi-skill company-profit forecasting system through sealed point-in-time historical cases, post-seal Actuals, capability-level error attribution, external method reflection, independent review, cross-company/regime validation, and deterministic builds of technology-company-profit-forecasting plus its specialist skills. Use for backtests, method changes, trainer rounds, audits, or releases; not for an ordinary current forecast.
---

# Technology Company Forecasting Trainer

Improve the generalized reasoning about future revenue, operating profit and
GAAP attributable net income.  Metrics, source counts, field counts, equations,
test counts and validator pass rates are diagnostic evidence, not the objective.

This skill is the training and release coordinator for a five-skill system.  It
does not repeat the production analysis:

- `technology-company-profit-forecasting` owns the live decision, orchestration,
  red team, readiness and immutable snapshot.
- `company-evidence-research` owns point-in-time evidence and data quality.
- `company-operating-modeling` owns industry economics, causal structure and
  operating equations.
- `company-financial-forecasting` owns integrated statements, attributable
  profit, earnings power and valuation.

The three specialists serve both live cases and **sealed historical** cases.
They never receive post-cutoff Actuals.  This trainer alone opens Actuals after
the forecast is sealed, attributes the earliest failure to a capability or
shared contract, and decides whether a reusable change merits release.

## Canonical authority

Read, in order:

1. `assets/skill_system/manifest.json` for ownership and handoffs.
2. `references/research-sop.md` and `assets/method_system.json` for the one
   production analysis order and construction philosophy.
3. `assets/training_method_overlay.json` and
   `references/historical-training-loop.md` for historical cutoff, Actuals,
   error attribution, external reflection and promotion.  These controls extend
   the production method; they never flow back into the live package.
4. `references/multi-skill-system-architecture.md` for system boundaries.

Specialist references deepen their owned stage; they never define another SOP.
Industry lenses remain optional calibration examples, not skills or scorecards.

## Training loop

1. Freeze entity/security, perimeter, accounting basis, `as_of`, horizons,
   case groups, initial hypothesis, serious rivals and a simpler challenger.
   Evidence available after `as_of` and answer-bearing searches are inaccessible.
2. Run the same coordinator and three specialist contracts used in production.
   Validate the point-in-time evidence, causal graph, formula-driven
   `model/model.xlsx`, `earnings_power_bridge.csv`, routed
   `internal_intangible_investment.json`, report and snapshot.  Missing remains
   `human-required`, not zero.
3. Freeze all evidence, observation rows, equations, model outputs, ranges and
   the independent review packet.  Seal before any Actuals are exposed.
4. Open the Actuals vault only through the trainer.  Its 3.2 receipt status is
   honestly `locally_consistent_untrusted` while builder-controlled local files
   lack an external append-only trust root; this cannot support an accuracy
   promotion by itself.
5. Attribute revenue, operating-profit and attributable-net-income error to the
   earliest failing handoff: evidence/definition/vintage; industry state or
   causal structure; operating parameter/timing/regime; financial basis,
   ownership or statement integration; orchestration/scenario/readiness; or an
   exogenous event.
6. Pre-register the diagnosis, rival remedies, right-reason test, ablation and
   retirement condition.  Complete an external-method reflection using original
   research, official standards, original-author practice and serious
   practitioner material with proposition-bounded permissions.
7. Revise one primary capability owner first.  Change a shared contract only
   when the failure genuinely crosses capabilities; version the contract and
   retest every consumer.  Never tune a company value to known Actuals.
8. Test on untouched issuer clusters and different lifecycle/cycle regimes.
   Compare direction, magnitude, bias, calibration and interval width against
   the simpler challenger without collapsing them into one score.  A wider
   interval cannot manufacture success.
9. Freeze inputs before independent causal, evidence, accounting and investment
   reviewers respond.  Role names do not create independence; preserve material
   disagreement.  A swap fold is a consistency diagnostic, never a new clean
   holdout.
10. Promote only when the method reflection, orthogonal structural suite,
    specialist evals, blind review and release build all support the change.
    Otherwise retain the rejected hypothesis and revert the candidate.

## Assurance boundary

Deterministic tests own cutoff, type, stable-ID, hash, structured transform,
equation execution and accounting conservation.  Independent agents judge
principal contradiction, source meaning and noise, rival mechanisms,
paper-to-production transfer, cycle, moat, persistence and investment relevance.
Consolidate tests that detect the same defect; validators are a safety net, not
the generative method.

The trusted structural suite is `trainer_structural_contracts`.  Promotion
evidence selects that suite ID, never an evidence-supplied command.  Blind audit
receipts bind `assertion_specs` and candidate/challenger `grading_artifacts`;
non-compensatory failures are recomputed from their rows rather than accepted as
a reported score.

## Release

The promotion-bound source includes the specialist templates and shared
protocol under `assets/skill_system/`.  Never hand-edit the generated live or
specialist directories.  Validate evidence, then build the whole system:

```bash
python scripts/build_skill_system.py \
  --trainer-skill-root . \
  --output-parent .. \
  --self-test --promote --promotion-evidence <promotion_evidence.json>
```

The builder regenerates `technology-company-profit-forecasting`, the three
specialists and `forecasting-system-contracts` from one promotion-bound tree.
Commit and push them atomically only after independent review succeeds.

## Method routes used by specialist owners

- Evidence: `references/core-source-and-evidence.md`,
  `references/data-quality-and-triangulation.md`,
  `references/research-lanes-and-corroboration.md`.
- Operating: `references/driver-tree-modeling.md`,
  `references/equation-primitives.md`, `references/mechanism-router.md`,
  `references/industry-economics-and-cycle.md`,
  `references/technology-commercialization-and-ip.md`.
- Financial: `references/model-mechanical-integrity.md`,
  `references/earnings-power-and-mean-reversion.md`,
  `references/internal-intangible-investment.md`,
  `references/business-quality-and-moat.md`,
  `references/valuation-and-market-expectations.md`,
  `references/core-output-and-valuation.md`.
- Full delivery: `references/full-company-delivery-contract.md` and
  `references/codex-parity-execution.md`.

The **Minimum decision-memo tables** and **Minimum integrated three-statement
schedule** remain defined in the routed financial/output contracts.
`not-decision-ready does not waive` the reported-profit chain,
**Value-creation identity**, **Patent / IP diligence**, **Recurring / usage
economics** or **Executable monitoring** when material.
