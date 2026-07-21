# Data schemas

Bundled JSON Schemas:

- `assets/schemas/source_record.schema.json`
- `assets/schemas/forecast_case.schema.json`
- `assets/schemas/forecast_snapshot.schema.json`
- `assets/schemas/model_graph.schema.json`
- `assets/schemas/technical_evidence_record.schema.json`
- `assets/schemas/backtest_result.schema.json` — retrospective metrics link to
  a separate `legacy-backtest-diagnostics/v1` artifact; old threshold
  comparisons are preserved observations with no promotion authority.

Use stable IDs. Dates must be explicit. Every forecast case must include `as_of`, archetypes, horizons, evidence references, actual values only in the validation section, and separate fact/assumption labels.

`source_record.schema.json` separates free-form retrieval metadata from
permission. `origin_record_kind` is a controlled affirmative record form and
sets the ceiling for the compatible `epistemic_class`; neither `source_type`
nor role can upgrade it. Claim evidence links always carry an
`observation_ids` array. A model-changing independent direct/causal/external
measurement names observation rows in `data_series_register.csv`, and the
independent review binds the exact source origin plus the computed
source-and-observation fingerprint.

The v2 snapshot schema publishes a period-by-period reported-profit chain. The
same period must carry revenue, operating profit, pretax profit, signed tax,
explicit non-controlling-interest net income and GAAP attributable net income
in the integrated statements and canonical output points. The graph schema
uses the corresponding typed `financial_role` vocabulary and rejects generic
`profit` as the main-line destination.

`historical_segment_bridge.csv` uses the bundled CSV header as its executable
row schema. Every input row has an explicit period; blank, `TBD` and `PENDING`
periods are invalid rather than non-substantive. A segment/elimination member's
declared partition dimension resolves to exactly one member-ID column:
`reported_operating_segment → reported_segment`,
`normalized_economic_branch → normalized_segment`, and every other dimension
`→ partition_member_id`. The resolved value must be non-placeholder and is the
only uniqueness key; row type and descriptive aliases never participate. The
scaffolder copies this canonical template rather than maintaining a second CSV
field list.

`technical-evidence-record/v2` is a proposition-level paper/evidence permission
record, not a general bibliography. It binds a version- and status-checked
technical claim to an explicit research design, typed sample and benchmark
applicability, uncertainty, replication/orthogonal evidence,
production-transfer differences, named driver/scenario IDs and one maximum
technical use. Applicable empirical samples require declared conditions and a
positive size. `not_applicable` and `unknown` require a reason and null rather
than a fabricated zero. Non-empirical records may inform theory, boundaries,
background or scenarios only as the proposition warrants. Its commercialization
permission is always `none`.
