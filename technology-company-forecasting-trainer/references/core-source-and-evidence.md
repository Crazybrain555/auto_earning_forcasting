# Core source and evidence workflow

## Purpose

Build a reproducible, dated and versioned Source Pack before forecasting. This workflow is universal across technology companies.

## Evidence routing labels

These labels help route retrieval; they are not a global hierarchy and never
decide a conflict by themselves.

| Tier | Meaning | Default permission boundary |
|---|---|---|
| E0 | Statutory or audited fact: filings, reported financials, executed disclosed contracts | What was reported or legally specified on that basis; forecast use still needs a causal bridge |
| E1 | Official operating disclosure: guidance, earnings calls, customer/product announcements | The speaker's stated view, intent or observed state within its authority; not proof of execution |
| E2 | Peer-reviewed research, standards, official technical documentation | Feasibility and parameter bounds under the stated test conditions |
| E3 | High-quality industry research, experts, channel work | Hypotheses and measurements only within their construct, population and incentive limits |
| E4 | Anonymous, second-hand or unclear market intelligence | Monitoring and follow-up search only |

Do not upgrade a source because its conclusion is convenient.

## Source Pack steps

1. Declare entity, security, timezone, fiscal calendar, currency, accounting
   basis and forecast horizon. The runtime records a snapshot timestamp
   automatically and keeps current research open through bundle freeze.
2. Enumerate material propositions, rival explanations and the source/measurement
   type with authority to inform each; do not search to fill E0-E4 quotas.
3. Save original files or canonical URLs with publication/retrieval time and content hash.
4. Extract subject, period, unit, basis, value, source location and original wording.  For every material numeric observation also create a dated DataSeriesRecord; document authority alone does not establish construct, population or vintage fit.
5. Detect conflicts and preserve all versions. Do not silently overwrite.
6. Assign evidence tier and allowed use.
7. Build comparability bridges for segment recasts, acquisitions, divestitures, carve-outs, discontinued operations, FX, and accounting changes.
8. Freeze the Source Pack. Any later source creates a new version.

## Proposition-scoped conflict rules

- Filing beats press release, presentation, database, or channel note for what
  was reported as a statutory financial fact on that filing's perimeter and
  accounting basis.  It does not automatically win on economic substance or a
  future external state.
- Company and customer statements are authoritative only for facts, intentions
  or transactions within their own knowledge and authority.  Management
  guidance is a direct management forecast, not realized demand.
- A technical paper proves bounded feasibility under its test conditions, not
  a company order or production economics.
- A contract can prove legal terms without proving execution, recognized
  quantity, realized price, margin or timing beyond those terms.
- A platform deployment proves a deployment, not a named supplier's share.
- E0-E4 are retrieval and default-permission labels.  No tier can override a
  definition, period, perimeter or authority-scope mismatch.

When sources disagree, first normalize the proposition, definition, period,
unit and perimeter; then determine which source has authority for that precise
claim.  Preserve genuine conflict and seek an independently generated
measurement.  Management, expert or sell-side opinion must be decomposed into
testable subclaims before it can support an analyst-authored Base assumption.
Read the full conflict and incentive protocol in
`references/data-quality-and-triangulation.md`.

### Executable claim-permission record

`claim_ledger.jsonl` makes that discipline proposition-specific. Each claim's
`source_ids` must be the exact set of `evidence_links[].source_id`; every link
records `relation` (`support`, `contradict` or `context`), `authority_scope`,
`evidence_function`, `measurement_or_construct_basis`, `incentive_conflict`,
`reconciliation_status` and `permission_rationale`. A source may therefore
support one bounded proposition while providing only context—or direct
counterevidence—for another. An accepted claim cannot contain an unresolved
contradiction.

Management is a direct anchor for its own stated view or plan; do not invent a
second-source quota for that proposition. If that management forecast enters
Base, preserve its type, state the historically observed bias or range,
calibration basis and application boundary, and require claim-specific
permission in the independent review. If the claim crosses from “our plan” to
future execution or an external state, a named causal or external test must
carry that bridge. The same proposition boundary applies when the initial
support is an issuer, expert or analyst opinion: none can directly prove the
future execution or external state it predicts. Proposition type comes first:
**every** model-changing `future_execution` or `external_state` claim needs a
`causal_test` or `external_test` support link to a separately recorded original
source whose controlled `epistemic_class` is
`independent_external_observation`, whatever its `claim_type` or source label.
That class is capped by `origin_record_kind=original_measurement_observation`
and requires an independent direct measurement with its own root source and
measurement method. The link also names the underlying observation IDs in
`data_series_register.csv`; source metadata alone never grants execution-test
permission. An expert or analyst summary must instead link the underlying
observation's separate SourceRecord and observation record. `reported_fact` is
incompatible with those proposition scopes because an outcome that has not
occurred is an estimate or inference, not reported history. The same test is
required when an
analyst-authored inference extrapolates a current factual observation into
future execution; factual provenance does not make the extrapolation an
observation. An analyst assumption likewise enters Base
only when the review frozen to that exact claim ledger records `adequate`
authority, the same reviewed source IDs and their exact
`reviewed_source_epistemic_classes` and
`reviewed_source_origin_record_kinds`, the exact observation fingerprints,
`base_parameter` permission and a substantive rationale. A reviewed expert opinion confined to a scenario or
technical boundary does not need that execution test unless it also asserts
`future_execution` or `external_state`.
The validator checks completeness, identity, hashes, links and faithful
enforcement. It does not infer authority from a publisher logo, tier,
confidence score or number of sources.

`claim_type` is also not an authority switch. For each `support` link the
validator resolves the actual SourceRecord and reads one controlled
`epistemic_class`: `official_reported_fact`,
`independent_external_observation`, `management_statement_or_plan`,
`expert_or_analyst_opinion`, `technical_evidence` or `discovery_only`.
`source_type`, `role`, `source_family` and publisher names are retrieval or
routing metadata only and never broaden authority. The controlled
`origin_record_kind` is the affirmative permission ceiling; objective authority,
independence, directness and root-lineage checks may reject an incompatible
class declaration. A management statement cannot be relabeled
`reported_fact`; an expert or analyst interpretation cannot become an external
observation by inventing a new `source_type` or role. Official reported facts
remain historical anchors, technical evidence remains bounded to technical
claims, management plans remain plans, and reviewed opinions may remain
scenario-only.

Every SignalCard use that changes an authored or executed model state—including
Base drivers/parameters, historical anchors, technical bounds and authored
scenario states or probabilities—names an accepted claim. The card's own
`source_id` must be a `support` link on that claim, the claim must name the same
driver, and any source- or claim-derived subjective permission must match the
current frozen authority judgment. Monitoring, search and discovery cards do
not change model state and may remain unbound; they cannot later be promoted by
renaming `allowed_use` without satisfying the full binding.

## Document and observation lineage

Read `references/data-quality-and-triangulation.md`.  A SourceRecord describes
the document; `data_series_register.csv` describes the quantitative observation
and its definition, scope, transformation, lag, vintage, revision policy and
independent cross-check; `financial_fact_ledger.csv` preserves filing/accession,
fact dimensions and restatement lineage.  Do not put all three levels into one
confidence score.

<!-- canonical: independence_and_corroboration -->
## Minimum SourceRecord

- `source_id`
- `source_type`
- `origin_record_kind`
- `epistemic_class`
- `publisher`
- `authors`
- `root_original_source_id`
- `derived_from_source_id` (explicit null for an original)
- `common_origin`
- `independence_cluster`
- `measurement_method_id`
- `published_at`
- `retrieved_at`
- `period_scope`
- `evidence_tier`
- `content_hash`
- `location`
- `claim_or_fact`
- `allowed_use`
- `limitations`

The v3 source schema additionally requires the controlled `origin_record_kind`
and compatible `epistemic_class`,
authority, independence, directness, role, dated availability/vintage and
explicit entity/product/geography/period/unit scope
matches. Resolve the parent chain to one root and reconcile it with
`source_independence_map.csv`; publisher wrappers and renamed clusters do not
create independence. Keep first-reported and latest-restated observations as
separate versions and bind the forecast to the version it actually uses.


## Forward-evidence extension
Complete the dated SignalCard review in
`forward-evidence-and-signal-validation.md`. Required artifacts are
`forward_signal_cards.csv` and `source_independence_map.csv`. Trace sell-side
and expert claims to original sources; repeated reports count as one cluster.
Validate source availability, version and provenance before use.


## Source depth metadata

Record `document_depth`, `word_count`, `anchor_count`, `coverage_topics`,
`original_source_available` and page/section anchors when they help the evidence
reviewer understand custody and limitations. These are diagnostics, not
readiness quotas. A summary cannot establish a claim it does not contain, while
a short primary table can still be the best direct measurement. Permission is
decided from the actual claim, provenance, construct, period, definition and
model link, then challenged in the frozen independent research review.
