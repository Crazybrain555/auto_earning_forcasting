# Historical training loop — git flow

## Objective

Improve the forecasting method through historical cases. Git is the only version and release mechanism: a validated improvement is a commit that gets pushed; a failed one is reverted. The time sandbox is the one non-negotiable part of this loop — everything else stays light.

This overlay exclusively owns the historical cutoff, source eligibility,
answer isolation, forecast seal, post-seal Actuals access, realized-outcome
evaluation, error attribution and release decision. Production references
describe only the current-evidence method.

Specialists receive a **projection view**, not the training workspace.  That
view contains the decision contract, eligible source/evidence IDs and content,
accounting basis, forecast horizons and the normal handoff metadata needed to
produce an evidence, operating-model or financial bundle.  It excludes the
cutoff controller, seal receipts, post-seal Actuals, outcome evaluations, error
attribution and candidate/challenger judgments.  Specialists therefore execute
their ordinary professional contracts and never implement a second cutoff,
seal or outcome-evaluation workflow.  The Trainer constructs and audits every
projection view and remains the sole owner of those controls.

The objective is better generalized reasoning about future revenue, operating
profit and GAAP net income, not maximization or minimization of one metric.
Errors, interval scores, pass rates and test counts are diagnostic views.  A
change is promoted only when an independent reviewer finds that the combined
financial/industry logic, causal explanation, untouched-case evidence,
uncertainty honesty and parsimony support it.  No weighted aggregate can allow
a good number to compensate for broken accounting, leakage, overfit logic or a
failure on a distinct economic regime.

Assurance spans the model lifecycle rather than appearing as a final test
wall. Review conceptual soundness and developmental evidence before use;
verify implementation, shared-data dependencies and continued fit while it is
used; and compare forecasts with realized outcomes after the seal.  Apply the
depth of review according to the model's decision exposure and materiality,
not a universal field, source or test quota.  This risk-based separation of
development, monitoring, outcomes analysis and independent effective challenge
is adapted from the 2026 interagency model-risk guidance listed in
`methodological-foundations.md`; it is governance guidance, not a claim that
this skill is a regulated bank model.

## Setup

- The five invokable skills and non-skill contract kernel live in one git repository. The method version of any run is `git rev-parse HEAD`; record it as `method_commit` in the run manifest and snapshot. Specialist and protocol sources are promotion-bound under `assets/skill_system/` and their top-level packages are generated outputs.
- Case workspaces live outside the skill directories, in the runs root configured by the hosting project (see that project's CLAUDE.md / AGENTS.md for the concrete path and any operator controls). Keep the runs root gitignored: actuals and evaluation files must never enter the method tree, and committing them would leak answers into future method context.
- Round bookkeeping is one small file, `training-runs/<round-id>/round.json`:

```json
{
  "round_id": "round-3",
  "base_method_commit": "<git sha when the round started>",
  "group_a": [{"case_id": "MU@2020-01-31", "role": "development"},
               {"case_id": "AMD@2020-02-04", "role": "development"}],
  "group_b": [{"case_id": "VRT@2021-06-30", "role": "validation"},
               {"case_id": "NTAP@2019-11-30", "role": "validation"}],
  "status": "training_a | validating_b | swap_training_b | swap_validating_a | pushed | abandoned",
  "notes": "what was changed and why; where it failed if abandoned"
}
```

## Sandbox invariants (apply to every case, every phase)

1. Every forecast-use source's original publication/version time is at or before
   the frozen `as_of`. The same rule applies to observation availability and
   vintage, filing date, accounting-basis effective date and technical/versioned
   evidence. Preserve first-reported and latest-restated records separately and
   bind the case only to the version then available. Model memory is not evidence;
   undated or post-cutoff material is quarantined.
2. No answer-bearing queries before the seal. Keep `historical_query_log.csv` honest and complete.
3. Seal with `scripts/freeze_training_forecast.py` (which runs the time-boundary,
   research-completeness and delivery validators) **before** retrieving any
   target Actual. Freezing records an **external forecast-seal receipt** at
   `<round>/seal_receipts/<case>.json`; the freeze rolls back if the receipt
   cannot be written and refuses to reseal a case whose receipt already exists.
   Only after the seal, fetch Actuals and score. The scorer records
   `forecast_seal_receipt_status=verified` only when that receipt matches the
   in-workspace seal. This status proves freeze integrity, not external truth of
   the later Actuals. A legacy run explicitly allowed without this receipt is
   `legacy_missing_unverified` and cannot support promotion. Actuals use the 3.2
   observation contract in `assets/templates/training_actuals_template.json`:
   every entity–true-fiscal-period–metric fact binds an issuer/regulator official
   source published no earlier than that period end, content-addresses the
   retrieved source, identifies the fact by a durable page/table/note/XBRL
   anchor, stores the direct numeric token copied from it, and declares currency,
   unit, consolidation perimeter and a controlled statutory GAAP/IFRS basis.
   Narrative, an undisclosed dash or an analyst assumption is unknown, not a
   numeric fact. Rounded precision is recomputed from the numeric token. Period
   dates, rather than a free `FY+N` label, form the observation identity.
   Revenue, operating profit and `gaap_net_income_attributable` are canonical
   identities, not aliases. A generic profit or consolidated net-income number
   is never treated as attributable income; use either a directly reported
   official attributable fact or the complete reported pretax-tax-consolidated-
   NI-NCI bridge. A zero requires the official token itself to parse to zero plus
   explicit zero provenance. Bridge tolerance is mechanically derived from the
   source-bound precision of its facts and cannot be enlarged by the analyst.
4. Actuals and evaluation outputs live only in the seal-exempt subdirectories
   `actuals_vault/` and `evaluation/` (or outside the workspace). Everything else
   in a sealed workspace is hash-locked. A successful score emits one
   `actuals_validation_receipt` bound to the source-file hash and every locally
   checked observation. Its only valid status is
   `locally_consistent_untrusted`; candidate and challenger must use identical
   receipts. The receipt proves local definition, source-binding, numeric,
   reconciliation, hash and timeline consistency—not external truth if one
   builder can rewrite local artifacts and recompute their hashes. This release
   therefore blocks `historical_training`/`validated_on_holdout` promotion until
   the host supplies a trusted append-only or signed Actuals registry outside
   builder control that binds raw Actuals, official-source bytes, extraction
   tuples and scored evaluation identity. Historical cases can still diagnose
   and improve the method, but the release remains `method_research` with
   `profit_accuracy_claim: not_established`. Aggregate metric observation counts
   do not substitute for either auditable facts or that trust boundary. Never
   write an actual, or a rule derived from one specific known actual, into the
   skill files.
5. A case whose seal was broken or whose actuals were seen early can still be used for training and diagnosis — it can never again be counted as validation.

Realized point error, signed bias, direction, interval calibration and coverage
are computed only here, after the forecast seal and Actuals validation.  They
may compare a forward-evidence model with an official-evidence-only challenger,
but remain a diagnostic vector for error attribution; the live forward-evidence
ablation itself tests causal sensitivity and decision relevance.

## The round

### 1. Pick the groups

Pre-register a development group and a genuinely untouched validation group.
Choose cases for economic independence and coverage of the mechanism's material
lifecycle, industry and cycle states, not to fill a 2+2 quota. One issuer cannot
establish cross-company generalization; even two distinct issuers are only a
lower bound for an accuracy claim, never proof that the sample is sufficient.
The independent reviewer decides whether the reference class and regime
coverage support the claimed scope. A smaller exploratory round may still
support a bounded `method_research` integrity change, with
`profit_accuracy_claim: not_established`. Draw candidates from
`references/training-curriculum.md` / the user, and prefer untouched cases that
share the mechanism but are not the same story. Record `round.json` and the
base method commit.

### 2. Run Group A in the sandbox

For each case: `scripts/scaffold_training_run.py --case-role development`, research within `as_of`, build the full delivery, seal, then score against actuals.

### 3. Improve the method on Group A

- Attribute each material error with the taxonomy (DATA, PERIMETER, STATE, PARAM, STRUCTURE, TIMING, REGIME, ACCOUNTING, EXOGENOUS; template `assets/templates/forecast_error_taxonomy_template.csv`).
- Locate the earliest failed handoff and assign one primary capability owner:
  evidence, operating model, financial forecast, or coordinator.  Revise that
  owner first.  Change the shared protocol only when the failure cannot be
  localized without breaking more than one consumer; version it and retest all
  consumers.  The three specialists never see post-cutoff Actuals or evaluation
  artifacts—the Trainer passes only a diagnosed, pre-registered change problem
  and a fresh projection view back to the affected capability.
- Fix the reusable mechanism, not the number: a change must be a rule with a stated scope and failure condition (the "when X evidence is missing, cap FY+2 confidence" kind), never a growth/margin/tax value tuned to a known actual.
- Right-reason check: the revised forecast should move for the reason claimed.
  When useful, use `scripts/score_mechanism_outcomes.py` to preserve the
  activation, direction, state, timing, magnitude, financial-line and cash
  diagnostics separately. It emits no passing score; an independent reviewer
  attributes the row-level pattern and decides whether the mechanism moved for
  the right reason.
- **External-method reflection (required, not optional).** Internal error
  attribution only tells you *that* the method missed; it cannot tell you what
  practitioners already know about that failure mode. Before writing the rule,
  consult outside method sources on the specific error and record what you
  found in `method_reflection.md` (see below). Select evidence for relevance
  and proposition-specific method authority, not a citation quota or category
  keyword. One direct method source may be sufficient for a bounded proposition;
  whenever corroboration is
  claimed, the additional source must have a genuinely independent
  origin/method rather than repeat the same author, dataset, expert or model
  family. Original academic work, official standards and guidance, original-author
  practitioner work, books, published models,
  analyst/podcast company deep dive, or timestamped YouTube transcript can add
  a practice lane. Their format or category label never grants authority
  automatically; the frozen independent reviewer judges originality, relevance,
  authority and transfer for the bounded proposition.
  Ask of every diagnosed error: *is this a known failure mode with a known
  remedy?* Adopting a remedy that outside practice already validated beats
  inventing one from a two-case sample - and where outside practice
  disagrees with what the errors suggest, record the disagreement rather than
  resolving it silently. For every source, record its originality and
  independence cluster, the bounded method claim it supports, and the boundary
  beyond which transferring that claim would be misuse. A source grants
  permission to test a hypothesis; reputation never substitutes for validation.
- Re-run the affected A cases to confirm the diagnosed error is actually addressed.
- **Prefer process correction over another gate.**  First ask whether the
  failure arose because the SOP chose the wrong stage order, duplicated a
  number across artifacts, failed to execute a shared equation, or allowed a
  downstream conclusion to become an input.  Correct that generative path
  before proposing a validator.  A new deterministic test is justified only
  for an objective invariant and must identify the existing test it replaces
  or the genuinely orthogonal assurance angle it adds.
- **Use a complexity budget.**  Record artifacts, authored fields, equation
  primitives, validator branches and tests added/removed.  An increase is not
  a benefit.  If the proposed method needs more machinery, its validation plan
  must show the distinct forecast, integrity or decision error that machinery
  addresses and include a retirement/ablation rule.  Prefer deletion and
  consolidation when two checks respond to the same underlying defect.
- **Keep judgment independent.**  Deterministic scripts test time, types,
  provenance links, arithmetic and accounting conservation.  Separate blind
  agents assess causal adequacy, source interpretation, principal
  contradiction, rival hypotheses, transfer from papers to production, moat
  persistence and investment relevance.  A role name is not independence: the
  reviewer receives the frozen evidence/model before the builder's rebuttal and
  records material disagreements rather than being prompted into consensus.
- Run `python scripts/validate_method_reflection.py --reflection <round>/method_reflection.md --strict`
  before the local commit. This checks structured traceability, source links,
  misuse boundaries, honest support state and process-first change fields. It
  does not decide source authority, conflict resolution, validation-plan
  sufficiency or whether the proposed rule must be adopted.
- Commit locally (message = the rule and its rationale, not the case answer). Do not push yet.

### 3b. The reflection record

Each round writes `training-runs/<round>/method_reflection.md` with, per
proposed rule:

| Field | Content |
|---|---|
| `error_observed` | the measured miss (case, horizon, direction, magnitude) |
| `internal_attribution` | taxonomy code + mechanism reasoning from the cases |
| `external_sources` | one or more relevance-selected structured entries with `source_id`, descriptive `category`, `independence_cluster`, `originality`, `location`, bounded `method_claim`, and `misuse_boundary`; category strings do not grant authority, and corroboration requires genuinely independent roots |
| `outside_view` | what practitioners do about this failure mode |
| `agreement` | does outside practice confirm, refine, or contradict the internal reading |
| `rule_adopted` | the rule as written, with scope and failure condition |
| `support_status` | whether the rule is still provisional, externally supported, or validated; do not overstate what outside sources prove |
| `validation_plan` | untouched companies/mechanisms and lifecycle or cycle states, with named pass/fail evidence for revenue, operating profit and GAAP net income separately; the independent reviewer judges whether this plan is sufficient |
| `why_not_alternatives` | remedies considered and rejected, with reasons |
| `generative_change` | which SOP stage, shared primitive or authored-to-generated boundary is corrected before any safety-net check |
| `assurance_angle` | the one primary orthogonal angle tested; overlapping tests to retire or consolidate |
| `complexity_delta` | artifacts, authored fields, equations, validator branches and tests added/removed, with ablation or retirement condition |
| `independent_review_plan` | reviewer separation, frozen inputs, decision rubric and how disagreement affects readiness |

Every proposed rule names `challenger_baselines` — the simpler rule or model it
must beat. When they materially improve falsifiability, also add
`ablation_plan` (which component to remove when a proposal has several moving
parts) and `rollback_condition` (an explicit reversal trigger not already
captured by the rule's failure condition). Ablation and rollback are
conditional tools, not ceremonial mandatory fields.

Four guards this record exposes for independent judgment:

1. **Sample-size honesty.** A rule inferred from two cases is a hypothesis.
   If outside practice already validates it, say so - the rule inherits that
   support. If not, mark it `provisional` and give it a wider validation plan.
2. **No silent overfitting.** A rule that outside practice contradicts must
   argue explicitly why this method's context differs, or be dropped.
3. **No source laundering.** Corroboration requires independent origin/method
   clusters. A transcript, article, and podcast that all repeat one expert or
   dataset are one cluster, not three.
4. **No authority shortcut.** Every source supplies a bounded method claim and
   misuse boundary. An external rule remains provisional until its validation
   plan survives untouched companies/mechanisms and relevant lifecycle or
   cycle states.

### 4. Validate on Group B

Run both B cases fresh: scaffold as `--case-role validation`, research, seal, then score. "No big problem" means, qualitatively:

- the error type the rule targets does not recur systematically on B;
- B cases that were fine before are not made worse (no new systematic bias);
- intervals were not silently widened to pass — width must still be attributed to named states;
- spot-check one previously trained company (`--case-role regression`, or the bundled backtest scripts) when the rule touches its mechanism.

Answer these **as a structured `fold_review` block in `round.json`** — one line of evidence per field, never a bare "pass":

```json
"fold_review": {
  "target_error_recurred": false,
  "new_systematic_bias": false,
  "intervals_silently_widened": false,
  "right_reason_ok": true,
  "regression_ok": true,
  "evidence": "one line per field: which case/metric shows it"
}
```

**Pass → release:** write `promotion_evidence.json` with the validated reflection, test-suite request, blind audit and direct revenue/operating-profit/GAAP-net-income holdout comparison against the challenger. `test_suite.suite_id` must be `trainer_structural_contracts`; any command/result fields are audit records only. The builder resolves that ID to its internal fixed argv, never executes an evidence-supplied command, runs it without a shell, uses the real return code, and verifies that the trainer tree did not mutate. This suite covers time integrity, schemas, provenance, equations, accounting conservation, runtime profiles and package behavior. Static issuer benchmark modules declare the source-local `diagnostic_benchmark` marker and are deselected by semantic role, rather than being hidden in a growing filename-ignore list. They remain a separate diagnostic panel and do not require a general method to reproduce an old forecast value.

Blind evidence binds the original case inputs, fixed `assertion_specs`, and candidate/challenger `grading_artifacts`. Every assertion admitted to the release audit is non-compensating: a builder cannot turn a failed accounting or evidence assertion into a soft item by changing a `critical` flag. Exploratory observations belong in the independent judgment, not the fixed release assertion set. Leakage, broken accounting, unsupported conclusion permission and outcome-fitted logic are likewise recomputed rather than trusted from a summary. Causal adequacy, right reason, parsimony and generalization remain an isolated reviewer's judgment and are not reduced to assertion pass rate. Holdout error, signed bias, direction, calibration and interval score are a diagnostic vector, never an all-metrics-must-win formula.

An accuracy claim additionally binds every case to an `evaluation_unit`: entity cluster, cutoff, target-period start/end, exact receipt period IDs, horizon, mechanism and cycle/lifecycle regime. The entity and fiscal dates must match the scored Actuals receipt; labels in a summary cannot manufacture a second issuer or a later target. Two labels or two overlapping cutoffs for one issuer are one economic cluster, not two independent holdouts. Use multiple genuinely distinct entities and report leave-one-entity-out influence for revenue, operating profit and GAAP net income, but let the independent reviewer distinguish sampling noise from a systematic failure. A smaller or single-company experiment can still promote an integrity improvement as `method_research`, but its `profit_accuracy_claim` remains `not_established`. Validate the structure with `scripts/validate_promotion_evidence.py`, then rebuild the whole system (`scripts/build_skill_system.py --trainer-skill-root <trainer> --output-parent <repo> --self-test --promote --promotion-evidence <file>`). That build runs the trusted structural suite, live package self-test and cross-skill ownership/handoff checks. Run the diagnostic benchmark panel separately and preserve its mixed results. Commit and push only after the whole body of evidence supports the change. Round done; record `status: pushed`.

### Research-led structural method changes

Accounting, data-lineage, validator-bypass and source-method research can reveal
a structural defect before a clean historical sample exists. Such a change may
be promoted as `change_type: method_research` only when it passes external-method
reflection, the full regression suite and a blind contract audit with zero
critical failures. Its promotion evidence must state
`profit_accuracy_claim: not_established`; it may claim stronger integrity, not
better revenue or profit accuracy. Put the new rule into the next relevant
historical curriculum and upgrade the accuracy claim only after untouched
holdouts beat or match the named challenger for revenue, operating profit and
GAAP net income without new signed bias. This route prevents both paralysis and
unearned accuracy claims.

### 5. Fail → swap fold (左脚踩右脚)

If B performs poorly, reflect and adjust:

- Diagnose B's errors the same way and revise the rule, now using B as the training material.
- Then re-run Group A as the validation side under the adjusted rule (fresh workspaces, sealed before re-reading actuals). Be honest in `round.json`: A's actuals were already exposed this round, so this pass checks **consistency**, not clean generalization.
- Compare two things:
  1. does the adjusted rule keep roughly the step-3 quality on A (not far off — "差得远不远"), and
  2. do the A-trained and B-trained versions of the rule agree in direction and scope?

**Consistent and acceptable on both groups →** merge into one rule, then release as in step 4.

### 6. Still failing → abandon and reshuffle

- `git checkout` / `git reset` back to `base_method_commit`; record `status: abandoned` with the diagnosis in `round.json`.
- Start the next round with a **new** group of training companies. Do not promote this round's Group B to be the next round's validation set — both groups are now exposed; they join the regression pool instead.

## Regression pool

Every company used in a finished round joins the regression pool. When a later rule touches a pooled company's mechanism, re-run at least one pooled case (or the bundled per-company backtest scripts under `scripts/run_*_backtest.py`) before pushing. This is the "fix storage, don't break NVIDIA" check kept at its useful core.
