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

Only transactions public by `as_of` may enter historical Base. Unannounced future events belong in anonymous tails and may require `human-required`.

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
