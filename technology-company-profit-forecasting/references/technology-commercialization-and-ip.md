# Technology Commercialization and IP

This file is an optional cross-validation input for the `operating_model` and
`causal_graph` stages. A technology, science or IP judgment enters the forecast
only by changing the value or a named scenario of a specific financial driver —
the "From technology to the financial model" gate below — and must rest on
evidence an independent reviewer can re-check; it never independently constitutes
a conclusion, and the value-investing view of normalized earning power owns the
answer. Route this reference only when technology/IP is explicitly requested, a
technology claim is material to the requested revenue or operating-profit
output, or the gates distinguish a named rival. Otherwise omit the gate
register; do not make a non-technology or immaterial branch complete a generic
technology checklist.

Treat science, engineering, manufacturing, qualification, commercial adoption,
accounting revenue and cash as distinct gates. A strong technology claim can
fail economically at any later gate.

## Independent gates

For every conclusion-critical technology, create one record for each applicable
gate:

1. scientific mechanism and measured performance;
2. reproducibility and engineering prototype;
3. patent and freedom-to-operate position;
4. standards or ecosystem compatibility;
5. technology readiness;
6. manufacturing readiness;
7. supplier and customer qualification;
8. binding commercial commitment;
9. delivery, installation and acceptance;
10. revenue recognition, gross profit and cash collection.

Each record states status, dated evidence, owner, next milestone, probability
only if needed, financial permission and falsification condition. Passing one
gate does not imply the next.

## Papers

Use papers to understand mechanism, performance frontier, constraints,
reproducibility and competing approaches. A material paper citation gets one
machine-readable row in `technical_evidence_records.jsonl` under
`technical-evidence-record/v2`. First classify the proposition's design as
`experimental`, `observational`, `theoretical`, `methods`,
`review_or_meta_analysis` or `standard_or_specification`; the label describes
how that exact claim is supported, not the journal or document as a whole.
Record the exact claim rather than the paper's topic; DOI or other stable
identifier and exact version; correction, expression-of-concern, withdrawal or
retraction status and the dated source used to check it; uncertainty; data and
code availability; computational reproduction; independent replication;
orthogonal engineering corroboration; funding and conflicts; competing routes
and negative results; and any difference between the research setting and the
production environment.

Sample and benchmark fields are typed contracts, not mandatory decorations.
Each separately declares `applicable`, `not_applicable` or `unknown`. If an
experimental or observational claim is allowed to affect the model and relies
on a sample, its conditions, sampling frame, positive sample size and unit must
be declared. If a sample or benchmark is not applicable or is unknown, store a
null value and a specific reason; never invent a sample of one, substitute zero,
or fabricate a benchmark to satisfy a form. Theoretical, methods, review,
standard, background and rejected records may therefore preserve their real
design without pretending to be experiments. Unknown is a disclosure state,
not evidence against the claim. Non-empirical material may support a mechanism,
technical boundary, background, monitor or named scenario when the proposition
warrants it, but it cannot itself authorize a Base factory parameter.

Reproducibility and replication are separate. Re-running the same code and data
does not independently replicate the physical claim. Trace every paper,
replication and engineering observation to its **root original** source.
Independent replication requires a different root, originating organization or
experimental team, and measurement method; a mirror, translation or paper from
the same laboratory is common-origin evidence even if its cluster label changes.
Orthogonal engineering corroboration must also be independent and must measure
the claim through a genuinely different production-test, qualification or
engineering method. A
`base_technical_parameter` requires either an accepted independent replication
from another independence cluster or accepted orthogonal engineering evidence,
plus `matched_with_quantified_bridge` from experimental to production
conditions. Otherwise the maximum permission is `technical_bound`,
`scenario_only`, `monitoring`, `background` or `human_required`. Retractions,
withdrawals and expressions of concern cannot drive Base. The validator is
`scripts/validate_technical_evidence.py`.

Papers may set technical bounds or motivate a scenario. They do not prove
factory yield, cost, qualification, customer share or timing of material
revenue. Accordingly every record has `commercialization_permission=none`.
Citation count, peer review and a current Crossmark-style status check are
custody signals, not probabilities of truth or commercial success.

The production transfer bridge is a structured numeric bridge from the paper's
measured condition to the claimed production condition. It names source and
target evidence, units and controlled operation; itemizes every scale or
adjustment with evidence; and exposes source, bridged and target values plus a
machine-recomputed residual. Every endpoint and adjustment must cite an accepted
source; a rejected production measurement cannot anchor the transfer. A
narrative production transfer bridge such as
"allowing for factory conditions" is not executable evidence and cannot grant a
Base parameter. This is the same bridge primitive used for data-series basis
reconciliation, so technical work cannot evade arithmetic checks by changing
field names.

## Patents and IP

Analyze patent families, not raw document counts. For a material family record:

- priority date, jurisdictions, assignee history and legal status;
- independent claims and the product or process they cover;
- remaining life and geographic relevance;
- forward citations with examiner/applicant context where available;
- standards-essential declarations, licensing obligations and disputes;
- likely design-around, complementary know-how and manufacturing dependency.

Every material technology row declares `patent_evidence_status` as
`material_family|searched_none|not_material|human_required` and preserves the
search source IDs. A `material_family` separately populates
`patent_claim_scope`, `patent_assignee_and_encumbrances`,
`patent_family_and_citation_context`, `freedom_to_operate_status`,
`patent_design_around_and_knowhow`, and `ip_economic_link`. The economic link
uses the executable form `claim -> existing driver_node_id ->
price|unit_cost|yield|share|capex|qualification_lag|fade`, and the workbook
cell for that node is named in the memo. `not_material` requires a reason and
`searched_none` requires the search sources and conclusion. FTO status is
`cleared|limited_with_terms|blocked|not_performed|unknown`; blocked,
not-performed or unknown FTO cannot support a Base parameter or moat-persistence
claim and is limited to a technical bound, scenario, monitor or background.
If the available packet omits one of these items, report the exact missing
diligence and required source; do not compress the result into “patent evidence
is weak.”

Patent citations can help trace knowledge flows, but they are noisy and shaped
by examination practice, firm strategy and jurisdiction. A patent is evidence
of a claimed invention, not proof that a product works, is defensible, is used,
or earns excess returns.

## TRL and MRL

Technology Readiness Level and Manufacturing Readiness Level answer different
questions. TRL concerns maturity of a technology in a relevant environment.
MRL concerns the ability to manufacture it repeatedly at required quality,
rate and cost. Record the rubric and evidence behind any assigned level; never
infer MRL from TRL.

For commercial forecasting, add qualification readiness and commercial
readiness. These are not official substitutes for TRL or MRL; they are separate
company-model gates with their own evidence.

## Qualification and commercialization

Map the specific path for the product and customer:

research → prototype → sample → engineering validation → design selection →
supplier qualification → production award → ramp → shipment → acceptance →
recognized revenue → cash.

Use contractual and accounting facts to define each transition. A design win,
memorandum, framework agreement, backlog or reserved capacity has no automatic
revenue permission. Route uncertain stages to named scenarios or option value
until the required gate is passed.

## From technology to the financial model

An accepted technology claim must change a named parameter such as:

- addressable units, content per unit or attainable share;
- price premium or useful life;
- yield, throughput, energy, materials, labor or warranty cost;
- qualification time, capex, working capital or cash timing;
- terminal persistence or competitive fade.

Then trace it through the causal graph, statements and valuation. If no
parameter changes, the research is background rather than forecast evidence.

## Commercialization hard gate

FY+2 and later forecasts cannot include material technology-led revenue in Base
unless the case documents the relevant scientific, readiness, qualification
and commercial gates. Missing gates require an explicit scenario, value range,
monitoring event and readiness cap.
