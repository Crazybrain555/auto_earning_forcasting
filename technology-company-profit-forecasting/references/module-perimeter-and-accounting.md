# Module: enterprise perimeter and accounting bridge

Use whenever acquisitions, divestitures, carve-outs, segment recasts, discontinued operations or material non-GAAP/discrete accounting items affect comparability.

## Perimeter bridge

```text
Reported revenue
= organic legacy revenue
+ acquired revenue × consolidated fraction
- disposed/discontinued revenue
+ FX and recast effects
```

Use transactions evidenced by the current bundle in the reference path and
preserve their announcement, closing and consolidation dates. New evidence may
enter until bundle freeze; after publication it creates a new forecast version.
Unannounced possible transactions remain anonymous tail states and may require
`human-required`.

## GAAP operating bridge

```text
GAAP operating profit
= adjusted segment/program economics
- acquired-intangible amortization
- inventory fair-value step-up
- acquisition/integration
- restructuring
- SBC
- litigation/product claims
- corporate allocations
```

Also model financing, tax, dilution, working capital and cash integration costs.
For every material non-GAAP measure preserve the closest GAAP measure,
definition version, individual adjustment, tax effect, cash/non-cash character
and recurrence evidence.  A changed definition opens a comparability bridge;
it is not spliced into the old series.  The [SEC non-GAAP
interpretations](https://www.sec.gov/rules-regulations/staff-guidance/corporation-finance-interpretations/non-gaap-financial-measures)
are a disclosure-quality anchor, not a mechanical rule that every exclusion is
wrong.  If forward GAAP reconciliation is unavailable, cap the GAAP conclusion
instead of inventing the missing adjustments.

## Discrete accounting events

Read `module-discrete-accounting-events.md` whenever a bounded event can materially change reported profit, balance sheet or cash. Use an event-family-specific state machine; do not apply deferred-tax states to impairments, restructuring, litigation or acquisition accounting.

For DTA/valuation allowances, additionally read `submodule-dta-valuation-allowance.md`. Separate recurring tax, discrete GAAP effects and cash taxes. Reverse non-cash benefits in FCF and exclude them from normalized recurring valuation.

## Failure modes

- reported growth called organic;
- future acquisitions backfilled;
- adjusted margin used as GAAP margin;
- acquisition amortization ignored in long-term EPS;
- divestiture/recast not bridged;
- a generic effective tax rate replacing jurisdiction-specific tax states;
- the same discrete event counted in several statements or valuation lines;
- global interval widening instead of event-local uncertainty.
