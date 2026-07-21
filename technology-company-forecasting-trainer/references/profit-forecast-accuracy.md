# Profit-forecast accuracy (the governing outcome, not a scalar objective)

The purpose of this method is to improve the accuracy and decision usefulness
of forecasts of a company's future revenue, operating profit and GAAP net
income attributable.  There is no single numerical objective function. Point
error, signed bias, direction, interval calibration, width and causal error
attribution are different diagnostic views; optimizing one of them can make the
forecast less honest or less useful.  Financial/industrial logic, point-in-time
integrity and generalization are non-compensating requirements. This file is
the accuracy doctrine and is built from measured forecast errors rather than a
promise that one metric captures investment quality.

## 1. Measured evidence belongs to the run, not the method

Case values, realized Actuals, issuer names and aggregate error tables live in
the sealed run workspace.  They are never copied into this reusable method as
a baseline, forecast floor, universal horizon multiplier or directional
adjustment.  Recompute diagnostics from the currently eligible frozen sample
and always publish its entity clusters, forecast origins, horizons, accounting
targets, lifecycle/cycle states, overlap and revisions beside any aggregate.

Read the diagnostic vector rather than one average: revenue, operating-profit
and attributable-income point error; signed bias and direction; interval
coverage and width; and causal error attribution.  Decompose a profit miss
through the executed profit chain—volume, price, mix, unit cost, utilization,
opex, below-the-line items, tax and NCI—without assuming in advance that
revenue or margin must dominate.  A pattern found in one locked sample is a
hypothesis for an untouched sample, not a parameter in the Skill.

The active run may use its own earlier frozen method, a simple historical or
run-rate model and a minimal causal model as challengers.  Their values remain
run artifacts.  The reusable rule is only to allocate new research and method
work to the diagnosed failure mode, then test that change on untouched cases
for the right reason.

## 1A. State what the point forecast means

The canonical point outputs are the values of the one executable joint path
with `role=reference`.  They are a realizable causal/accounting state selected
before Actuals are known.  They are **not automatically** the probability-
weighted mean, median or mode of the scenario distribution, and the word
`Base` does not create one of those statistical meanings.

If a case publishes a probability-weighted expectation, median or quantile, it
must be calculated separately from all applicable executable joint states,
name the functional and probability vintage, and remain labeled as a
distribution summary that may not itself be a realizable operating path.  It
cannot replace the reference path or be assembled by independently averaging
revenue, margin, tax and NCI rows from incompatible states.

Training therefore interprets point-error diagnostics as performance of the
frozen reference path. Absolute-error and interval diagnostics do not silently
redefine that path as a median or mean forecast.  A method comparison states
which functional is being compared and uses a compatible loss or proper score;
otherwise apparent `bias` or superiority may be an evaluation-definition
error rather than a forecasting improvement.

## 2. State the error budget before forecasting

Every delivery declares, in the snapshot, an `error_budget`: for each horizon,
the expected revenue error and the expected margin-error contribution, with a
sentence on which is the bigger risk and why. This forces the analyst to say
in advance where the forecast is most likely to be wrong, and it is checkable
after the fact.

Use only a frozen, point-in-time baseline from the active run as a challenger,
and only after judging comparability in business model, horizon, lifecycle,
cycle state and accounting perimeter.  The error budget states that judgment;
the baseline values themselves do not enter the reusable method.

## 3. Forecast margin as a bridge, never as a percentage

A margin assumption written as "GM 52% in FY+2" carries no information about
why. Every horizon's margin must be a **bridge from the base period** with
named, quantified deltas:

```
Base-period gross margin
  ± price/cost spread    (ASP path minus unit cost path - the two must be modeled separately)
  ± mix                  (segment/product/customer mix shift, each with its own margin)
  ± utilization / yield   (manufacturing: fixed-cost absorption)
  ± pass-through          (input cost changes and the lag before they reach price)
  ± scale/learning        (unit cost decline with cumulative volume)
= Forecast gross margin
```

then, below gross profit:

```
Gross profit
  − opex by driver        (headcount, R&D programs, % of revenue ONLY with a stated operating-leverage rate)
= Operating profit
  ± below-the-line        (§5)
  × (1 − tax rate)        (§5)
= Net profit
```

Each ± line is a number with a source, not a vibe. If a bridge line cannot be
quantified, it is a stated unknown, and it widens the interval.

## 4. Diagnose directional bias without creating an optimism rule

Any directional pattern observed in a finite training run is sample-limited.
Treat it as a hypothesis to explain and retest on an untouched sample, never as
permission for a universal optimism or pessimism adjustment.  Relevant rival
explanations include:

- **Guidance anchoring.** Estimate company-specific guidance bias only from the
  same management team, definition, horizon and business regime.  Preserve the
  full beat/miss distribution; management guidance can be conservative or
  optimistic.  State whether Base adopts, rejects or transforms it and why.
- **Growth-transition error.** Trailing organic growth, run rate, consensus and
  a conditionally matched reference class are symmetric challenger baselines.
  Both acceleration and deceleration need a bridge through demand, share,
  price, mix, inventory, capacity, recognition, currency and perimeter.
- **Inflection extrapolation.** A visible ramp can accelerate, stall or invite a
  competitive response.  Continue it only through dated capacity, qualification,
  order, demand and cost evidence; otherwise keep the path in named scenarios.

Required check before sealing: compare driver-tree growth with trailing organic
growth, run rate, company-specific guidance, consensus and a disclosed reference
class.  Explain every material difference in either direction.  The baselines
never override the causal equations.  Apply the conditional mean reversion
contract in `references/earnings-power-and-mean-reversion.md`.

Record the audit in `forecast_snapshot.json.growth_challenger_review`.  Each
challenger has a named status (`accepted`, `not_available_with_reason`, or
`human_required`) rather than a fabricated number.  For an accepted material
difference, state the case-specific materiality basis and reconcile the growth
gap through quantified bridge rows, named driver-node IDs and named operating-
state IDs.  The same contract applies to acceleration and deceleration; there
is no universal growth hurdle or interval-width floor.

## 5. The below-the-line and tax layer

A revenue and operating-profit model can still miss attributable net income
when financing, tax, NCI, perimeter or discrete accounting states change.  The
complete pretax-to-attributable-income bridge is mandatory by construction;
the routes below are conditional investigations selected from the company's
balance sheet, tax notes, ownership structure, transactions and stated risks,
not a checklist that must manufacture eight immaterial assumptions:

| Item | Trigger to check |
|---|---|
| DTA / valuation allowance | company approaching cumulative profitability, or a large existing allowance |
| NOL utilization | history of losses now turning profitable |
| Tax-rate normalization | current rate far from statutory, expiring incentives, tax-holiday roll-off, jurisdiction mix |
| Minority interest / JV equity income | consolidated subsidiaries not wholly owned |
| Interest income/expense | large net cash or new debt; model from balance × rate |
| FX translation | material non-functional-currency revenue |
| One-offs | impairment risk, restructuring programs, legal accruals, gain/loss on divestment |
| Share count | buyback authorization, convertible dilution, SBC issuance |

Quantify an applicable material route in the bridge or preserve it as a typed
unknown with its affected periods and conclusions.  Omit an inapplicable route;
the independent accounting review asks whether an omitted state could change
pretax profit, tax, NCI, attributable income or cash rather than counting rows.

## 6. Predictability regimes set both effort and interval width

Not all revenue is equally forecastable. Classify each driver-tree branch:

| Regime | Examples | Dominant uncertainty | Interval discipline |
|---|---|---|---|
| Contracted / backlog | equipment backlog, RPO, take-or-pay | timing, cancellation and recognition | calibrate on comparable backlog survival and timing errors |
| Installed-base recurring | service, subscriptions, consumables | churn, attach, usage and price | calibrate on matched cohorts and contract mechanics |
| Share-of-known-market | components into a forecast end market | end-market error, content and share | propagate the external anchor and company bridge jointly |
| Cycle-priced commodity | memory, panels, freight | price, utilization and inventory state | use named asymmetric cycle states |
| Early ramp / new product | first-generation products, new segments | qualification, yield and timing | use a distribution across gated commercialization states |

Two consequences:

1. **Effort follows uncertainty.** Spend research on the branches whose regime
   is uncertain and whose size is material - not evenly across the tree.
2. **Interval width follows regime, not habit.** A sample's realized coverage
   is a calibration diagnostic, not a universal width floor.  Start from a
   matched historical error distribution, propagate named driver states and
   score coverage plus interval width with a proper interval score.
   Cycle-priced and early-ramp branches usually need wider or asymmetric
   states, but direction and width come from the active mechanism.

## 7. Near-term accuracy is a nowcast, not a forecast

FY+1 accuracy comes mostly from arithmetic on things already known: quarters
already reported, the current quarter's elapsed weeks, guidance, channel and
pricing data with a known lag. Build FY+1 as
`reported quarters + nowcast of the current quarter + modeled remainder`, and
state how much of the year is already locked. A method that reasons about
FY+1 annually is throwing away its most reliable information.

## 8. What to check after scoring

Every scored case updates the accuracy record: revenue APE; revenue, gross and
operating-profit bridges; operating-profit and GAAP-net-income scaled absolute
errors; interval score and coverage; and whether the miss was directional,
dispersive, a data revision or an accounting/segment recast.  Profit MAPE is not
used when the denominator can approach or cross zero.  Use the observation-level
vintage contract in `references/data-quality-and-triangulation.md` so hindsight
revisions are not misclassified as forecasting error.

### Formal score contract

Point errors and calibration have different evaluation populations. Revenue
APE, margin error, scaled absolute error and signed bias use only horizons
explicitly marked `point_evaluable`. Coverage and proper interval score use
all scored horizons, including an FY+3 distribution whose point estimate is
deliberately not evaluable. The scorer records the observation count for every
aggregate so a missing horizon cannot disappear from a mean.

Each horizon freezes `interval_alpha`, the nominal miscoverage probability,
before Actuals are retrieved. The scorer verifies `0 < alpha < 1`, ordered
low/high bounds and uses that declared alpha in the normalized interval score.
It never assigns a different confidence level merely because a horizon is
FY+1 or FY+3. Coverage and width remain diagnostics interpreted together, not
a scalar promotion target.

Direction is always forecast minus actual. The scorer reports
`revenue_signed_bias = mean((forecast revenue - actual revenue) /
abs(actual revenue))`. Because operating profit and GAAP net income can cross
zero, `operating_profit_signed_bias` and `net_income_signed_bias` use the signed
forecast error scaled by actual revenue. Their absolute-error counterparts use
the same scale. Profit MAPE remains prohibited.

Every scored horizon requires actual revenue, operating profit and GAAP net
income **attributable to parent shareholders** plus forecast intervals for all three. The
actual is not a bare number: its unique entity–fiscal-start–fiscal-end–metric observation binds
an issuer/regulator official fact published after the period, a content hash and durable fact anchor, the direct numeric token copied from that fact, the information cutoff and retrieval time,
currency, reported unit, consolidation perimeter and a controlled statutory accounting-basis ID whose label is canonical. Rounded precision is mechanically derived from the numeric token; neither the label nor the reconciliation tolerance is analyst-selectable. A free horizon label cannot make one fiscal period appear twice. Generic
`profit` and consolidated `net_income` aliases are prohibited. Attributable
income must be either a directly reported official fact with explicit parent-
shareholder scope or reconcile through reported pretax income, tax expense,
consolidated net income and NCI. An absent NCI or tax disclosure is not zero;
a numeric zero requires the cited official numeric token itself to parse to zero plus explicit zero provenance; narrative or non-disclosure is unknown.
Identity tolerance is derived from the facts' source-bound precision and is never
an analyst-selected escape hatch.
The scorer emits a content-derived `actuals_validation_receipt` whose only
valid 3.2 status is `locally_consistent_untrusted`. It proves local lineage,
definition, type, source-binding, numeric-literal, arithmetic, hash and timeline
consistency—not external truth against a builder who can rewrite every local
artifact. Candidate and challenger must use identical receipts, but holdout
accuracy promotion remains fail-closed until a host-provided append-only/signed
Actuals registry outside builder control also binds the raw Actuals,
official-source bytes, extraction tuples and scored evaluations. Aggregate
observation counts never substitute for either boundary. A point-evaluable horizon also
requires all three forecast points. A distribution-only horizon may omit the
operating-profit and net-income point values, but not their intervals. Missing required operating-profit or GAAP-net-income data is a hard score-contract
failure; an explicitly distribution-only point is recorded as not evaluable,
never silently omitted from interval calibration.

A method change survives only if its predeclared RuleCard passes ablation and
held-out cases without material regression.  Recompute the baseline each round;
do not optimize a rule to the same cases that inspired it.
