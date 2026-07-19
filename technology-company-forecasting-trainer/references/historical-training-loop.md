# Historical training loop — git flow

## Objective

Improve the forecasting method through historical cases. Git is the only version and release mechanism: a validated improvement is a commit that gets pushed; a failed one is reverted. The time sandbox is the one non-negotiable part of this loop — everything else stays light.

## Setup

- The two skills live in one git repository (the installed `.claude/skills/` directory, or wherever the user keeps them). The method version of any run is `git rev-parse HEAD` of that repository; record it as `method_commit` in the run manifest and snapshot.
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

1. Every forecast-use source's original publication/version time is at or before the frozen `as_of`. Model memory is not evidence; undated or post-cutoff material is quarantined.
2. No answer-bearing queries before the seal. Keep `historical_query_log.csv` honest and complete.
3. Seal with `scripts/freeze_training_forecast.py` (which runs the time-boundary, research-completeness, and delivery validators) **before** retrieving any target Actual. Only after the seal, fetch actuals and score with `scripts/score_training_forecast.py`.
4. Actuals and evaluation outputs stay in the case workspace. Never write an actual, or a rule derived from one specific known actual, into the skill files.
5. A case whose seal was broken or whose actuals were seen early can still be used for training and diagnosis — it can never again be counted as validation.

## The round

### 1. Pick the groups

A round is four companies by default: Group A = 2 training (development) companies with frozen cutoffs, Group B = 2 validation companies untouched until step 4. Adjust only with reason (e.g. one very large development case); the validation side stays at 2. Draw candidates from `references/training-curriculum.md` / the user. Prefer B companies that share the mechanism under test but are not the same story as A. Record `round.json` and the base method commit.

### 2. Run Group A in the sandbox

For each case: `scripts/scaffold_training_run.py --case-role development`, research within `as_of`, build the full delivery, seal, then score against actuals.

### 3. Improve the method on Group A

- Attribute each material error with the taxonomy (DATA, PERIMETER, STATE, PARAM, STRUCTURE, TIMING, REGIME, ACCOUNTING, EXOGENOUS; template `assets/templates/forecast_error_taxonomy_template.csv`).
- Fix the reusable mechanism, not the number: a change must be a rule with a stated scope and failure condition (the "when X evidence is missing, cap FY+2 confidence" kind), never a growth/margin/tax value tuned to a known actual.
- Right-reason check: the revised forecast should move for the reason claimed. When useful, score intermediate mechanism outcomes with `scripts/score_mechanism_outcomes.py`.
- Re-run the affected A cases to confirm the diagnosed error is actually addressed.
- Commit locally (message = the rule and its rationale, not the case answer). Do not push yet.

### 4. Validate on Group B

Run both B cases fresh: scaffold as `--case-role validation`, research, seal, then score. "No big problem" means, qualitatively:

- the error type the rule targets does not recur systematically on B;
- B cases that were fine before are not made worse (no new systematic bias);
- intervals were not silently widened to pass — width must still be attributed to named states;
- spot-check one previously trained company (`--case-role regression`, or the bundled backtest scripts) when the rule touches its mechanism.

**Pass → release:** rebuild the production skill (`scripts/build_live_release.py --trainer-skill-root <trainer> --output-root <live> --self-test`), run `scripts/package_self_test.py` and the test suite, commit, push. Round done; record `status: pushed`.

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
