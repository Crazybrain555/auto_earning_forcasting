# Accounting Credibility Diagnosis

Reported statements are testimony, not ground truth. This stage decides how
much each reported line can be trusted before the skeleton is rebuilt from it,
and records the normalization agenda that later stages must execute. It runs
after source custody and before statement reconstruction; a red flag that is
not cleared or explicitly carried as a limitation blocks the affected line
from Base use downstream.

## Policy and flexibility review

For each material line, identify the accounting policy that produces it, how
much discretion the policy allows (revenue recognition timing, capitalization
versus expense, useful lives, reserve setting, segment allocation), and
whether the company changed a policy or estimate in the reconstruction
window. A policy change inside the window is a construct break: the affected
series needs a bridge or a shortened comparable window, never silent mixing.

## Red-flag screen

Screen the statements against the standing list; every hit either gets a
normalization entry or a typed limitation:

- recurring "one-time" restructuring or impairment charges;
- pension/return assumptions out of line with market conditions;
- stock-based compensation framed as a non-expense;
- pro-forma emphasis that diverges persistently from GAAP;
- reserve releases or valuation-allowance changes flowing through profit;
- receivables, inventory or deferred revenue growing far ahead of revenue;
- capitalized costs whose amortization lags economic consumption;
- channel or bill-and-hold patterns that pull recognition forward.

The screen exists to produce adjustments, not a score. Findings feed the
`historical_statements` normalization work and the claim ledger.

## Incentive map

List the compensation metrics and guidance commitments of the executives who
control reporting judgment, and bind each to the statement lines it touches.
A line that management is paid on carries a discount on management-sourced
claims about it: guidance for that line is a management forecast requiring
the standard claim permission, and its historical bias (below) sets the
default haircut.

## Guidance bias track record

Quantify guidance versus actual for revenue and profit over the available
history: direction, average miss and dispersion. The result is a numeric
prior applied wherever guidance enters a scenario or anchors a range. When
history is too short to quantify, record `typed_unavailable` rather than
assuming neutrality.

## Outputs

- normalization agenda: line, issue, adjustment rule, evidence;
- incentive map: metric, owner, bound statement lines;
- guidance bias record: horizon, direction, magnitude, sample;
- unresolved red flags carried as typed limitations with scenario consequence.
