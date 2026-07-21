# Research Lanes and Corroboration

Research breadth is a defense against shared blind spots. Lane count is a
coverage diagnostic, not a truth score. Claims enter the model only through
source lineage, causal permission and sensitivity.

## Eight search lanes

| ID | Lane | Typical evidence | Principal strength | Principal risk |
|---|---|---|---|---|
| L1 | Official filings | annual/interim reports, regulatory filings, prospectus | reported history and accounting | backward-looking, aggregated |
| L2 | Management voice | calls, Q&A, investor days, letters, formal interviews | intent, guide and operating context | incentives, selective disclosure |
| L3 | Cross-company official | customer, supplier and competitor filings or calls | orthogonal value-chain read-through | scope and timing mismatch |
| L4 | Measured industry data | shipments, utilization, price, inventory, capex | external state variables | opaque samples and revisions |
| L5 | Sell-side research | models, primers and field work | synthesis and estimate structure | access, banking and consensus incentives |
| L6 | Expert and channel | named experts, distributors, customer or supply-chain checks | close causal proximity | stale, partial or unverifiable samples |
| L7 | Technical and IP | papers, standards, patent families, readiness evidence | mechanism and technical bounds | weak commercialization permission |
| L8 | Trade and event research | specialist press and rigorous long-form work | discovery and chronology | repetition and source laundering |

The evidence tier remains attached to the individual source, not automatically
to the lane. A measured industry series with disclosed method may be more useful
than a vague filing sentence; its permission is still bounded to what it
measures.

## Search routing

Do not optimize lane count. Route searches from the uncertain node and rival
hypothesis. A customer-share thesis usually calls for customer or cross-company
evidence; a cycle thesis calls for measured demand, inventory, supply and price;
a technology-commercialization thesis calls for technical conditions,
replication, manufacturing readiness, qualification and commercial evidence.
Those are causal needs, not a universal requirement that every company touch a
fixed number of lanes.

Log successful and unsuccessful searches. An unsuccessful well-specified query
is a documented evidence gap. No query is an unexamined gap.

A filings-only package should normally trigger an independent-review challenge,
but it fails deterministically only when a material main-line measurement lacks
the required lineage, construct fit, causal permission or a truthfully declared
cross-check. Several lanes repeating one root observation remain one origin.

## Independence is about origin and method

Full independence and corroboration rules live in
`core-source-and-evidence.md`; this document only applies them across the eight
lanes. Sources that share an originating dataset, interview, press release,
analyst note, expert or measurement method are one cluster, and syndication or
citation chains do not create corroboration. Two sources corroborate only when
their failure modes genuinely differ across producer, method, sample, unit,
definition, transformation and dependence on other accepted sources.

## Claim-level corroboration

Each conclusion-critical claim requires:

1. a bounded sentence;
2. causal edge or parameter it may change;
3. at least one source close enough to measure that claim;
4. a genuinely independent cross-check where available;
5. conflicting evidence and rival explanation;
6. falsification condition and monitor.

A reference-path thesis carrier needs evidence appropriate to its failure risk.
A `corroborated` label requires a genuinely independent root, originating team
and measurement method (defined in `core-source-and-evidence.md`); a single
direct hard anchor may stay labeled as such, and the independent reviewer
decides whether its failure risk requires another method or a readiness cap.
Empty cross-check fields preserve the single-anchor state for review; populating
a cross-check series, result or basis bridge is an explicit corroboration claim
that the validator then checks for completeness, independence and definition
compatibility.

Technical feasibility, manufacturing readiness, qualification, commercial
commitment and revenue recognition require different evidence. Sources that
support one gate do not corroborate another.

## Sensitivity determines importance

Materiality is computed from the model. For each assumption record a named
`test_delta` and its effect on revenue, operating profit or NOPAT, attributable
net income, FCF, value per share and the investment posture. Prioritize the
assumptions that explain most of the model's change, can flip the decision, or
interact with leverage, solvency, covenants, dilution or a binary qualification
gate. Do not encode one universal percentage cutoff: the economically relevant
scale depends on the company, horizon and decision.

Allowed support states include hard_anchor, corroborated, single_lane,
contested, analyst_only, scenario_only and human_required. The state describes
evidence; it is not a numerical weight.

## Handling conflict

Do not average conflicting claims. Reconcile scope, period, units, recognition,
incentives and data lineage. If the conflict survives, preserve only the rival
propositions actually anchored by their sources and return their permitted uses
to the coordinator. The coordinator decides whether they are material causal
hypotheses and authors any named scenarios; an evidence researcher does not
complete missing sides of a conflict or assign probabilities. The disagreement
itself may become a monitor.

Management guidance requires a historical bias check where possible. Sell-side,
expert and trade sources must name incentives and trace back to origin.
Technical sources follow references/technology-commercialization-and-ip.md.
