# Submodule: deferred-tax asset and valuation-allowance state

Use only for jurisdiction-specific deferred-tax assets, NOLs, credits and valuation allowances.

## Observable states

- `S0`: full/substantial allowance; cumulative losses or insufficient positive evidence.
- `S1`: improving evidence, but realization remains insufficient; tail probability only.
- `S2`: sustained jurisdiction-specific profitability and realizability evidence; release probability may rise.
- `S3`: explicit management/auditor evidence or accounting conclusion that release is probable; a bounded GAAP branch is permitted.
- `S4`: recognized in an official filing and available as a reported fact.

## Eligible amount and scheduling

Cap the benefit by the eligible jurisdiction-specific DTA or valuation
allowance, adjusted for expiration, uncertain tax positions, forecast taxable
income, reversal schedules and legal realization limits. Base permission
requires tax-note facts for the reported balance and proposition-appropriate
evidence for jurisdictional realizability and timing; an evidence label alone
does not establish release.

```text
Recurring tax provision_t
= recurring pretax income_t × jurisdiction-weighted recurring tax rate_t

DTA/valuation-allowance discrete effect_t
= eligible realizable amount_t × state probability_t × recognition fraction_t

Cash taxes_t
= current cash-tax schedule after NOL/credit utilization and payment timing
```

A generic effective tax rate cannot replace this bridge. A non-cash release raises GAAP net income but is reversed in FCF and excluded from normalized recurring earnings.

## Falsification and monitoring

Track jurisdiction profitability, cumulative-loss evidence, expiry schedules, management/auditor language, tax-law changes and uncertain tax positions. Do not assign the same probability to every horizon.
