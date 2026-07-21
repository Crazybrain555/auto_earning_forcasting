# Internal Intangible Investment and Analytical Cohorts

Internally generated R&D, software, content and customer acquisition can make
reported operating profit, reinvestment and ROIC incomparable across firms or
periods. They are not automatically assets. Preserve the issuer accounting
basis first; use `internal_intangible_investment.json` only to test an economic
investment hypothesis and its sensitivity.

## Trigger and honest escape

Assess each potentially material category. A category is one of:

- `accepted`: the spend is material and a sourced analytical cohort is built;
- `not_material_with_reason`: a source-backed amount divided by revenue is
  recomputed below the declared threshold;
- `human_required`: materiality or economic life cannot be supported, which
  caps a research-grade conclusion but does not force a fabricated estimate.

Silence is not an immateriality conclusion. The default template keeps common
technology-company categories unresolved until the analyst performs this test.

## Preserve reported accounting

Every accepted category identifies the reporting-basis ID and issuer policy.
`reported_expense` and `reported_capitalized` reconcile to total internal
investment. The only permitted shadow-schedule uses are
`analytical_sensitivity_only` and `reference_class_comparability`. Shadow
capitalization never changes GAAP/IFRS/ASBE Base revenue, operating profit,
pretax profit, tax or attributable net income.

## Vintage cohort contract

For each investment vintage record product/program, causal driver nodes,
commercialization gates, sources and named scenarios, then recompute:

```text
total internal investment = reported expense + reported capitalized
closing shadow asset = opening shadow asset + new shadow investment
                       - shadow amortization - shadow write-off
adjusted NOPAT = reported NOPAT + after-tax expense addback
                 - after-tax shadow amortization
average adjusted invested capital = average reported invested capital
                                    + average shadow asset
adjusted ROIC = adjusted NOPAT / average adjusted invested capital
```

Economic-life low/base/high, attrition or obsolescence, and maintenance/growth
shares are company parameters supported by evidence and scenarios. A published
population estimate, management label or accounting amortization period is not
automatically the economic life. Maintenance plus growth shares equal one, but
that identity does not make the classification observable.

## Forecast use

Use the schedule to ask whether changing investment under conservative
accounting temporarily depresses or releases earnings, whether a product cohort
has passed commercialization gates, and how adjusted NOPAT/ROIC change across
life and attrition scenarios. Keep reported and analytical returns side by
side. If the analytical result carries the valuation, the red team attacks the
life, attrition, product attribution, maintenance share and commercial outcome
before the reported earnings thesis.

Penman and Zhang and Lev and Sougiannis motivate investigating conservative
accounting and R&D investment. They do not prove that all R&D is valuable or
authorize a universal life, capitalization rate or amortization pattern. The
issuer's applicable accounting standard controls reported results.
