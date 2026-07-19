# Mode router and executable time boundary

## Purpose

Use one unified Skill in three modes. Forecasting, evidence, model, red-team and delivery standards remain the same; the information boundary and evaluation lifecycle change.

| Mode | Research boundary | Actuals | Typical use |
|---|---|---|---|
| `historical_train` | every forecast-used source must have original `published_at` or `version_at <= as_of` | prohibited until a valid forecast seal | training and method validation |
| `live_forecast` | latest evidence available at the current `as_of` | future Actuals do not yet exist | current research and valuation |
| `audit_only` | read-only contract | read-only | inspect a model or package |

## Historical-train rules

1. Freeze entity, fiscal calendar, `as_of`, targets, the score contract, the base method commit, and each case's role (training or validation) before research.
2. Web research is expected, but the source boundary applies to original publication/version time, not retrieval time.
3. A later host may carry an old eligible document only when the original version date is proved and retained.
4. Unknown-date, ambiguous-date and post-cutoff material is quarantined with zero forecast permission.
5. Search snippets are discovery aids only and cannot anchor conclusion-critical claims.
6. Model memory is not admissible evidence. The system cannot prove that a pretrained model has no ambient memory; instead every forecast-used factual claim, number, named event, and parameter must map to an eligible Source Pack record.
7. Historical queries must not contain target Actuals, later outcome labels, later product names, later transactions or other answer-bearing terms.
8. Maintain an exposure ledger separate from the Source Pack. Session exposure may change holdout evidence grade even when forecast permission remains zero.
9. `actuals_retrieval_allowed=false` throughout forecast, revision, calibration and unsealed holdout phases.
10. FY+1 is point-and-interval; FY+2 is scenario-weighted; FY+3 is distribution/regime-tail unless direct evidence supports more precision.
11. Run time-boundary, research-completeness, delivery and experiment-integrity validators before sealing.

## Contamination response

Follow `contamination-and-holdout-sop.md`.

- Incidental non-answer-bearing material may be quarantined and disclosed.
- Exact answer-bearing exposure before seal makes that holdout diagnostic-only; preserve a candidate already frozen before exposure and replace the holdout from the pre-registered reserve pool.
- Direct use, early Actual retrieval or hardcoding is an experiment breach.
- Exposure after a valid seal does not alter the sealed forecast.

## Source statuses

- `eligible_pre_cutoff`
- `quarantined_post_cutoff`
- `quarantined_unknown_date`
- `actual_only_after_seal`

## Release

Training governance is retained in trainer packages. A live-only artifact excludes trainer-only evaluation, Actuals and promotion files while keeping evidence, mechanisms, GAAP/cash, uncertainty, red-team and delivery disciplines. See `live-mode-release.md`.
