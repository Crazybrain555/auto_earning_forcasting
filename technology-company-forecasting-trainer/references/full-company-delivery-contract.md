# Full-company delivery contract

## Trigger

Apply when the request asks for a company forecast, financial model, three- to five-year revenue/profit forecast, valuation, customer/supply analysis, or a durable research package.

## Required artifacts

A complete delivery contains:

```text
<entity>_financial_model.xlsx
<entity>_forecast_report.md
run_manifest.json
source_manifest.json
financial_fact_ledger.csv
data_series_register.csv
assumption_register.csv
earnings_power_bridge.csv
internal_intangible_investment.json
claim_ledger.jsonl
model_graph.json
industry_profit_pool.csv
operating_cycle_register.csv
red_team.md
forecast_snapshot.json
```

A narrative-only answer does not satisfy a full-model request.

Strict validation requires an explicit major-version-2 `contract_version` in
`run_manifest.json`. There is no legacy fallback in strict mode: a missing or
non-v2 declaration fails, v2 artifacts remain mandatory, and manual importance weights remain forbidden. Legacy manifests may be inspected only outside the
strict full-company publication gate.

## Workbook concept requirements

Sheet names may vary, but the workbook must contain these concepts:

1. Executive summary / current market anchor.
2. Source Pack and evidence tiers.
3. Historical actuals and current-year bridge.
4. One-year quarterly operating model.
5. Driver and assumption schedules.
6. Three- to five-year GAAP operating model.
7. Cash flow, working capital, capital intensity, and share-count bridge.
8. Customer, demand, supply/capacity, contracts, products/programs, and stage gates as relevant.
9. Reference path, material rival states and regime/perimeter tails.
10. Cycle/growth-path and normalized valuation.
11. Market-implied reverse model.
12. Monitoring triggers and formula/quality checks.
13. Run/delivery manifest or equivalent audit sheet.

The model must use formulas for derived outputs and link assumptions from dedicated schedules. Calculated forecast lines may not be manually retyped across sheets.

## Minimum report structure

1. Snapshot timestamp, current price timestamp, model basis, and readiness.
2. Investment conclusion and what the market price requires.
3. Historical/current-year bridge.
4. Base forecast table.
5. Segment/customer/product drivers.
6. Supply, capacity, delivery, or content constraints.
7. Contracts, product/program stages, and enterprise perimeter.
8. GAAP, cash flow, capital intensity, and share count.
9. Reference path, material rival states and regime tails.
10. Near-term and normalized valuation.
11. Reverse-implied expectations.
12. Changes from the prior model, when applicable.
13. Key monitoring triggers, kill/upgrade evidence, and human-required items.
14. Source IDs or citations.

## Evidence readiness

For a current public-company model, reproduce the comparable historical profit
chain and latest operating state from dated current primary facts, bind current
market price to a timestamp, and obtain direct or independently measured
evidence for the thesis-carrying product/customer/contract/capacity nodes.
Technical or industry evidence is added only when it bounds a material
parameter or distinguishes a rival hypothesis.

This is a fact-and-driver contract, not a filing/source count. If a material
fact, definition bridge or thesis-carrier measurement is unavailable, publish
`not-decision-ready` or the independent review's lower readiness cap and list
the precise missing observation.

## Model quality gates

Before delivery:

- `historical_segment_bridge.csv` contains three annual consolidated periods,
  the latest interim status and one first-forecast bridge; the five numeric
  profit-chain fields, segment-to-consolidated revenue and forecast deltas
  reconcile; any changed perimeter/basis also reconciles reported values plus
  metric-level comparability deltas to comparable values, while disclosure gaps
  are typed and cap readiness; `not_applicable` is permitted only when no
  segment/elimination partition rows exist, while numeric partial disclosures
  use `disclosure_limited` and remain cross-checks rather than forced 100%
  partitions; `annual`/`interim` rows are actual and `first_forecast` rows are
  forecast, with every other period-state pairing rejected as input error;
  blank, `TBD` and `PENDING` period rows are also errors rather than filtered
  placeholders;
  every segment/elimination row resolves through period, period type,
  actual/forecast state and currency to exactly one consolidated parent, so
  every legal actual or first-forecast partition is inspected; each member
  resolves its `partition_dimension` to one non-placeholder member field:
  `reported_operating_segment` uses `reported_segment`,
  `normalized_economic_branch` uses `normalized_segment`, and every other
  dimension uses `partition_member_id`; that resolved ID alone determines
  uniqueness, so neither `row_type` nor descriptive aliases can manufacture a
  second member; an orphan or unnamed
  segment/elimination never disappears from the mechanical check;
- revenue segments sum to total in all forecast periods;
- COGS/gross profit/operating profit/net income bridges tie;
- reported, normalized, cash/accrual, investment and cycle profit layers
  reconcile, including the NOPAT = after-tax operating FCF + ΔNOA identity;
- material numeric observations preserve value, stock/flow/average type,
  definition, scope, actual availability time, stable vintage/predecessor,
  revision policy and model permission;
- each claim's `source_ids` exactly matches its proposition-scoped
  `evidence_links`, including support/contradict/context direction, authority
  and construct basis, incentives, reconciliation and permission rationale;
  accepted claims contain no unresolved contradiction; the validator derives
  bounded authority from each actual support SourceRecord's controlled
  `origin_record_kind` and compatible `epistemic_class`; free-form role/source
  type/family labels never grant authority, and `claim_type` cannot override
  the source boundary; management's own plan may be a direct anchor without a
  second-source quota, but Base use preserves it as a management forecast with
  historical bias/range, calibration basis, application boundary and frozen
  review permission, while every management/issuer-supported model-changing
  future-execution or external-state claim names an independent factual
  causal/external test whose link binds a separate observation-level record and
  whose frozen review binds the source origin and observation fingerprint;
  expert/analyst inputs cannot be relabeled reported facts;
- every model-changing SignalCard use binds an accepted claim, its own source's
  support link, the same driver and any matching frozen independent permission;
  monitoring/search/discovery uses may remain unbound but confer no model
  permission;
- every material series records whether a proposition-appropriate independent
  measurement is needed and available; when corroboration is claimed, the
  sources have different roots and methods plus a numeric definition bridge.
  A single direct hard anchor is disclosed to the independent reviewer, who
  decides whether it is sufficient, requires a readiness cap or remains outside
  Base;
- industry profit-pool components reconcile to a declared boundary total, and each applicable operating-cycle branch recomputes the channel-inventory, company-inventory and accepted-quantity × realized-price identities in exact workbook check cells; disclosure-limited equations cap readiness;
- cash roll-forward ties;
- share count and repurchases tie;
- scenario probabilities equal 100%, and every ordinary shock has a node-compatible unit, exact workbook cell/formula, declared forecast effective period and non-negative integer lag;
- scenarios that are explicitly ordered as adverse/base/favorable preserve the
  expected economic ordering unless a documented non-monotonic mechanism
  explains otherwise; no scenario naming taxonomy is mandatory;
- normalized-value assumptions do not simply reuse peak-cycle margins;
- cross-check demand is not added to product revenue;
- contracts/RPO do not imply undisclosed price or margin protection;
- samples, design wins, qualifications, and awards obey stage gates;
- every source used by the forecast is included in the registry-bound evidence
  bundle frozen for publication;
- formula errors are zero;
- unresolved P0 issues are disclosed and readiness is capped.

## Artifact style

- Facts/links and analyst inputs must be visually distinguishable.
- Tables use explicit units and fiscal periods, plus the typed accounting
  basis ID. Bare `GAAP` is invalid: framework, jurisdiction, version,
  effective date, presentation currency and major policy choices must be
  declared; cross-basis history requires a sourced quantitative comparability
  bridge into the forecast basis.
- Negative values and percentages use consistent formats.
- Long narratives belong in the report, not inside formula schedules.
- The executive summary should show the model's first failure point, not only the upside case.

## Final response contract

The chat response should summarize the conclusion, the five-year table, current valuation, major changes, readiness, and link all artifacts. It should not claim Codex and another model will produce identical numbers; it should state that the deterministic workflow and validators reduce variance while tools, source access, and judgment can still differ.


## Forward evidence synthesis
A full forecast must document investor dialogue, cross-company official read-through, independent measurements/research, named-expert evidence and relevant papers/standards. SignalCards must show accepted, rejected and conflicting signals, independence clusters, permissions and falsification triggers. Papers do not directly create company revenue, share or margin.


## Research-sufficiency gate

Before operating-model construction, complete
`research-completeness-and-company-quality.md`. Maintain the open research-question
register, material-assumption links and frozen independent research review.
Company-quality, technology, paper, patent, cycle and other specialist schedules
are routed by materiality rather than populated as universal checklists.

Reconstruct the required comparable financial history from fact-level filing
lineage and statement reconciliation. Do not substitute document counts or
long extracts for the exact statements, segments, definitions and restatement
bridges the model needs.

If a critical mechanism variable is Human-required, cap the horizon contract and readiness. For channel hardware with unknown current sell-through/inventory, FY+2 and FY+3 are scenarios/distributions rather than high-confidence points.
