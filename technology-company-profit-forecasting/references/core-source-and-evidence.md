# Core source and evidence workflow

## Purpose

Build a reproducible point-in-time Source Pack before forecasting. This workflow is universal across technology companies.

## Evidence hierarchy

| Tier | Meaning | Allowed model use |
|---|---|---|
| E0 | Statutory or audited fact: filings, reported financials, executed disclosed contracts | Historical/base hard anchor |
| E1 | Official operating disclosure: guidance, earnings calls, customer/product announcements | Near-term anchor with execution discount |
| E2 | Peer-reviewed research, standards, official technical documentation | Feasibility and parameter bounds |
| E3 | High-quality industry research, experts, channel work | Scenarios, total market, share and timing assumptions |
| E4 | Anonymous, second-hand or unclear market intelligence | Monitoring and follow-up search only |

Do not upgrade a source because its conclusion is convenient.

## Source Pack steps

1. Declare entity, security, `as_of`, timezone, fiscal calendar, currency, accounting basis, and forecast horizon.
2. Enumerate required sources from E0 to E4 according to selected mechanisms.
3. Save original files or canonical URLs with publication/retrieval time and content hash.
4. Extract subject, period, unit, basis, value, source location, original wording, and confidence.
5. Detect conflicts and preserve all versions. Do not silently overwrite.
6. Assign evidence tier and allowed use.
7. Build comparability bridges for segment recasts, acquisitions, divestitures, carve-outs, discontinued operations, FX, and accounting changes.
8. Freeze the Source Pack. Any later source creates a new version.

## Universal conflict rules

- Filing beats press release, presentation, database, or channel note for statutory financial facts.
- Company and customer statements are authoritative only for their own facts.
- A technical paper proves feasibility, not a company order.
- A contract can prove legal quantity obligations without proving execution, price floors, margin floors, or timing.
- A platform deployment proves demand, not a named supplier's share.
- An E4 claim cannot override E0/E1.

## Minimum SourceRecord

- `source_id`
- `source_type`
- `publisher`
- `published_at`
- `retrieved_at`
- `period_scope`
- `evidence_tier`
- `content_hash`
- `location`
- `claim_or_fact`
- `allowed_use`
- `limitations`


## Forward-evidence extension
Complete the dated SignalCard review in `forward-evidence-and-signal-validation.md`. Required artifacts are `forward_signal_cards.csv`, `historical_query_log.csv`, and `source_independence_map.csv`. Trace sell-side/expert claims to original sources; repeated reports count as one cluster. Validate source dates and forbidden future terms before using an enhanced forecast.


## Source depth metadata

Every accepted source must record `document_depth`, `word_count`, `anchor_count`, `coverage_topics`, `original_source_available` and page/section anchors. `summary_only` records do not satisfy filing, transcript, product or technical minimums. The research-depth validator may measure local source-file words and override an overstated self-report.
