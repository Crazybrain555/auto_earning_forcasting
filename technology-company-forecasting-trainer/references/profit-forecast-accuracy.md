# Profit-forecast accuracy (the objective function)

The purpose of this method is one thing: **predict a company's future revenue
and net profit accurately**. This file is the accuracy doctrine. It is built
from this method's own measured errors, not from investment philosophy.

## 1. The measured baseline (round-1, four sealed cases, twelve horizons)

Revenue absolute percentage error by horizon:

| Horizon | Mean APE | Every case |
|---|---|---|
| FY+1 | 5.7% | 4.6 / 4.6 / 5.2 / 8.4 |
| FY+2 | 10.3% | 6.9 / 9.1 / 10.6 / 14.7 |
| FY+3 | 18.7% | 13.9 / 19.4 / 20.2 / 21.3 |

Two facts to carry into every forecast:

**(a) Error roughly doubles per year of horizon** (~1.8x per step). An FY+3
number is a different kind of object from an FY+1 number, and the intervals
must say so.

**(b) All twelve horizons under-forecast.** Not eleven - twelve. That is not
noise; it is the method's own directional bias, and it must be actively
counteracted (§4).

Profit error decomposes far worse than revenue error. Using
`ln(P_f/P_a) = ln(R_f/R_a) + ln(m_f/m_a)`, the share of profit error coming
from the **margin** rather than from revenue:

| Case | Horizon | Revenue share | Margin share |
|---|---|---|---|
| CDNS | FY+2 | 6% | **94%** |
| NOW | FY+2 | 9% | **91%** |
| ASML | FY+3 | 47% | 53% |
| TSM | FY+3 | 70% | 30% |

**In the worst cases, over 90% of the profit miss came from the margin and
below-the-line lines - not from revenue.** Revenue modeling is in decent
shape; profit modeling is where this method loses. Effort allocation must
follow the error, not tradition.

## 2. State the error budget before forecasting

Every delivery declares, in the snapshot, an `error_budget`: for each horizon,
the expected revenue error and the expected margin-error contribution, with a
sentence on which is the bigger risk and why. This forces the analyst to say
in advance where the forecast is most likely to be wrong, and it is checkable
after the fact.

The default prior, absent a company-specific argument, is the measured
baseline above: FY+1 ~6%, FY+2 ~10%, FY+3 ~19% on revenue, and margin as the
dominant profit-error source.

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

## 4. Counteracting the under-forecast bias

Twelve of twelve horizons came in low. The dominant sub-causes found in
round-1:

- **Guidance anchoring.** Management guidance is conservative for most
  technology companies; anchoring the Base on guidance imports that
  conservatism and compounds it over the horizon. Compute the company's
  historical guidance-versus-actual bias where the data exists, state it, and
  state whether the Base uses guidance as given, haircut, or raised.
- **Mean-reversion of growth by default.** Forecasting FY+2/FY+3 growth below
  trailing organic growth is a *claim* about deceleration and needs a reason
  (saturation, comp, competitive loss, cycle turn). Absent that reason,
  deceleration is an unargued default and must be corrected.
- **Missing the second-order upside** of an inflection already visible in the
  base (a ramp that has started usually continues faster than a linear
  extrapolation of its first quarters).

Required check before sealing: for each horizon, compare forecast growth
against trailing organic growth, and where forecast < trailing, state the
deceleration reason explicitly. An unexplained deceleration is a defect.

## 5. The below-the-line and tax layer (where CDNS lost 27.6pp)

The single largest margin error in round-1 came from a deferred-tax
valuation-allowance release that the forecast never considered - a balance-
sheet event that moved net profit by more than the entire revenue error.
Mandatory screen, every delivery:

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

Each row is either quantified into the bridge or explicitly recorded as "no
material exposure, because X". Silence on this layer is a delivery defect.

## 6. Predictability regimes set both effort and interval width

Not all revenue is equally forecastable. Classify each driver-tree branch:

| Regime | Examples | FY+1 revenue error to expect | Interval discipline |
|---|---|---|---|
| Contracted / backlog | equipment backlog, RPO, take-or-pay | low (2-5%) | narrow; risk is timing, not level |
| Installed-base recurring | service, subscriptions, consumables | low (3-6%) | narrow; risk is churn/attach |
| Share-of-known-market | components into a forecast end market | medium (6-12%) | driven by the end-market anchor's own error |
| Cycle-priced commodity | memory, panels, freight | high (15-40%) | wide and asymmetric; the price path is the forecast |
| Early ramp / new product | first-generation products, new segments | very high (30%+) | distribution, not a point; timing dominates |

Two consequences:

1. **Effort follows uncertainty.** Spend research on the branches whose regime
   is uncertain and whose size is material - not evenly across the tree.
2. **Interval width follows regime, not habit.** Round-1 interval coverage was
   50% - the intervals were too narrow to be honest. Absent a
   regime-specific argument, revenue intervals should be at least
   ±6% / ±11% / ±19% at FY+1 / FY+2 / FY+3, and wider for cycle-priced or
   early-ramp branches. An interval that never misses is useless; an interval
   that misses half the time is broken.

## 7. Near-term accuracy is a nowcast, not a forecast

FY+1 accuracy comes mostly from arithmetic on things already known: quarters
already reported, the current quarter's elapsed weeks, guidance, channel and
pricing data with a known lag. Build FY+1 as
`reported quarters + nowcast of the current quarter + modeled remainder`, and
state how much of the year is already locked. A method that reasons about
FY+1 annually is throwing away its most reliable information.

## 8. What to check after scoring

Every scored case updates the accuracy record: revenue APE and the
revenue/margin split of profit error per horizon, plus whether the miss was
directional (bias) or dispersive (noise). Rules that reduce measured error
survive; rules that do not are reverted. The baseline table in §1 is
recomputed each round - if it does not improve, the method is not improving,
whatever else changed.
