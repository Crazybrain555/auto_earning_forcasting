# Data Quality, Vintages and Triangulation

Evidence authority and data fitness are different questions.  A regulator can
publish an authoritative series that is too aggregated, stale or defined
differently from the model node. A conclusion-critical number enters Base only
when its lineage, construct, population, period, unit, vintage and causal
permission fit the intended use.

This is a veto contract, not a weighted data-quality score.

## Two levels of lineage

### Document-level SourceRecord

Keep publisher, publication/retrieval times, hash, original location, authority,
independence, directness, role, scope match and limitations.  Never replace the
original document with a summary or database row.

Establish provenance once, at ingestion, and reuse that graph everywhere.  Each
source declares `root_original_source_id`, `derived_from_source_id` (explicitly
null for a root), `common_origin`, publisher/originator, authors or producing
team, `measurement_method_id` and `independence_cluster`.  Resolve derived
chains recursively to the root and reconcile the fields against
`source_independence_map.csv`.  A URL, vendor, broker wrapper or renamed cluster
cannot change the root.  Sources with a shared root, originator/team or
measurement method are not independent even when their cluster strings differ.

### Observation-level DataSeriesRecord

For each material quantitative series record:

- numeric observation value, stock/flow/average type and stable vintage ID;
- exact metric definition and observed construct;
- entity, product, geography and population/sample coverage;
- period start/end, stock/flow/average meaning and frequency;
- unit, currency, nominal/real, price and fiscal/calendar basis;
- publication, actual public-availability, retrieval and vintage times plus a
  recomputable period-end-to-availability lag;
- preliminary/final status, explicit predecessor for a revision, revision
  policy and classification version;
- input observation IDs and transformation, seasonal/quality adjustment,
  imputation and aggregation;
- known bias, missingness, breaks and allowed model use;
- original-source and measurement-method lineage;
- driver node, independent cross-check and reconciliation result.

Derived data preserve every input series id and the formula.  Repackaging one
original series, or multiplying it by another assumption, does not create an
independent source.

Company KPIs are versioned observations, not timeless labels. Preserve the
calculation, management use, scope and effective dates of each definition and
open an explicit bridge when presentation changes, consistent with the
[SEC's KPI/MD&A guidance](https://www.sec.gov/rules/interp/2020/33-10751.pdf).
Stopping disclosure makes the later value unknown and triggers research; it
does not create a zero, a deterioration signal or permission to splice a
different vendor's similarly named metric without a construct bridge.

## Financial-fact ledger

For financial statements preserve fact-level lineage separately from documents:
filing/accession, filed date, form, fiscal period, exact period, taxonomy/tag,
dimensions, unit, decimals, scale, sign, reported value, statement/note anchor,
extraction method, amendment/restatement predecessor and comparability bridge.

Maintain the first-reported fact and every later amendment or restatement as
separate, linked versions. Bind each forecast bundle to the version it actually
uses; never silently overwrite the first report with the latest restatement.
XBRL Company Facts/frames are extraction aids; verify material facts against the
rendered filing or note, fiscal calendar, dimensions and statement identities.

## Reconciliation and external validity are orthogonal

First prove that the numbers describe one internally consistent scope.  For
every exhaustive, mutually exclusive partition, the parts plus eliminations
must equal the whole: segment revenue, product/customer/geography mix,
scenario probabilities and ownership attribution.  A disclosed list of only
the largest customers is **not** an exhaustive partition and must not be forced
to 100%.  Also recompute the income chain, balance-sheet equation, cash, debt,
PPE, working-capital and inventory rolls, share-count/EPS bridge, GAAP to
non-GAAP bridge and period/quarter aggregation wherever those relationships are
present.

That internal closure is necessary but not sufficient.  A perfectly balanced
model can still use the wrong perimeter, omit a transaction, misread economic
substance or forecast the wrong mechanism.  For each material fact separately
ask whether it exists/occurred, is complete, belongs to the entity, is measured
and valued on the stated basis, and is presented in the right period and scope.
The main-line calculation is independently re-performed from its inputs; a
check value typed as zero is not a re-performance.

The [IFRS Conceptual Framework](https://www.ifrs.org/content/dam/ifrs/publications/pdf-standards/english/2022/issued/part-a/conceptual-framework-for-financial-reporting.pdf?bypass=on)
distinguishes direct verification from checking inputs and recalculating model
outputs. [PCAOB AS 1105](https://pcaobus.org/oversight/standards/auditing-standards/details/AS1105)
likewise makes relevance and reliability specific to the assertion being
tested and requires contradictory evidence to be investigated.  These support
two separate assurance questions; they do not turn an investment forecast into
an audit.

Segment reconciliation has no fixed percentage-of-revenue allowance.  The
runtime uses the shared equation numeric tolerance for calculation noise; any
larger rounding allowance must be derived from fact-level declared precision
and scale and represented as an explicit signed reconciliation row.  It is
never an analyst-selected materiality threshold.  Economic materiality remains
case-specific and includes qualitative effects on the thesis and decision,
consistent with the warning in
[SEC Staff Accounting Bulletin 99](https://www.sec.gov/interps/account/sab99.htm)
against using a numerical threshold as a substitute for full analysis.

## Claim authority is proposition-specific

### Proposition fidelity before authority

Before judging authority, freeze what the source actually asserted.  Model a
claim as the anchored proposition plus its direction, magnitude, comparison
basis, period, scope and causal relation.  Normalization may standardize units,
calendar labels or registry names, but it may not fill an absent member of that
tuple.  A source that says only "the experts disagree" does not reveal either
expert's sign; a source that says "demand is strong" does not supply a growth
rate, forecast period, company share or causal effect on profit.  Preserve
those dimensions as unknown and request the original material.

This is stricter than avoiding fabricated numbers: a plausible direction,
timeframe, scope or causal verb is also invented evidence when it is not
entailed by the anchor.  Conflict status is metadata about the evidence set,
not permission for the evidence capability to author two scenario states.

Do not use one global rule such as “official always wins” or “independent always
wins.”  Split a conflict into the proposition being asserted and the source's
authority over that proposition:

- an audited filing or regulatory submission is the primary anchor for what
  the entity reported for a stated period and accounting perimeter; it does
  not prove future demand, execution quality or economic durability;
- management and investor relations are direct sources for management's own
  view, intent, internal target and claimed current state; guidance is still a
  forecast with incentives and must be compared with the bottom-up model;
- a customer, supplier or regulator is direct for its own purchase, inventory,
  qualification, licence or policy, but mapping that fact to the target
  company's share, revenue recognition and margin requires a causal bridge;
- an industry dataset is authoritative only for its declared construct,
  sample and coverage; a paper or patent can bound feasibility or ownership,
  not commercial timing, yield, cost or captured profit;
- an expert or sell-side report is initially an interpretation and hypothesis
  source.  Its checkable underlying facts may receive permission after their
  original provenance is recovered.

For every material conflict record `claim_type`, `authority_scope`, root
origin, measurement method, incentive conflict, support/contradict direction,
definition/perimeter reconciliation and final permission.  First remove false
conflicts caused by period, unit, product, gross/net, accounting or perimeter
differences.  If comparable evidence still conflicts, seek a genuinely
independent measurement.  Until resolved, preserve `contested` state, the rival
explanation actually supported by each anchor and the allowed downstream use;
do not vote, average, silently choose the convenient source or author a
scenario in the evidence layer.

The machine-readable form is one `evidence_links` row per source-to-claim
relationship. `source_ids` is only the exact denormalized index of those link
IDs; it cannot contain a source with no proposition-level explanation. A
`contradict` link is either `reconciled` with its basis difference explained or
`unresolved`; an accepted claim cannot hide the latter. This preserves a real
conflict instead of turning it into a synthetic confidence average.

Authority and subjectivity are derived from the declared claim together with
the SourceRecords reached by its actual `support` links. Controlled source
`origin_record_kind` sets the affirmative permission ceiling, while authority,
independence and directness can narrow it further. `role`, `source_type` and
free-form family labels route retrieval but cannot broaden permission. A management or
first-party issuer source remains inside its own authority boundary even if the
claim is labeled `reported_fact`. Expert/analyst support remains subjective
even if the requested use is renamed `historical_anchor`, `technical_bound` or
`scenario_only`. The validator rejects incompatible claim/source types before
consulting the frozen qualitative judgment.

Authority sufficiency is authored in `research_quality_review.json`, whose
frozen inputs include `claim_ledger.jsonl`. For management claims and analyst
assumptions proposed as Base parameters, the reviewer names the claim, the
exact source set reviewed, the permitted use, an `adequate`/`limited`/
`inadequate` judgment and reasoning. Deterministic validation verifies those
fields and the frozen hash. It deliberately has no source-count, tier-point or
authority-score gate; a qualitative permission cannot be manufactured by
adding documents.

For management guidance, distinguish the proposition “management currently
plans/forecasts X” from “X will be executed” or “the external market will be
X.” The first can be directly anchored by the issuer; Base use preserves it as
a management forecast and records historical forecast bias/range, calibration
basis and application boundary. The latter propositions need a named
`causal_test` or `external_test`. That requirement is about crossing an
authority boundary, not collecting a second document.

That execution/external-state test follows the proposition first, not a source
name or `claim_type`. Every model-changing `future_execution` or
`external_state` proposition needs a named `causal_test` or `external_test`
backed by an independent external factual observation. Calling it
`reported_fact` is invalid even when the supporting document is an audited
filing: the filing may prove what was reported, not a future outcome. This
universal boundary also prevents a novel issuer, expert or analyst source label
from becoming predictive authority merely because it is not in a vocabulary.
A frozen qualitative review cannot turn the opinion that states the prediction
into its test, and an analyst-authored
extrapolation remains subjective even when its starting observation is factual.
The independent observation is not merely a SourceRecord label. The causal or
external evidence link names `observation_ids` in `data_series_register.csv`;
each bound record must be an accepted, finite, definition- and period-specific
original measurement whose source root, method, durable locator and SHA-256
content identity reconcile. The frozen reviewer binds both the source origin
kind and a computed observation fingerprint, then explains why the inspected
content is measurement rather than commentary. This is a qualitative
classification decision with an immutable audit trail, not a keyword test.
This is not a blanket ban on
expert evidence: a reviewed expert opinion may inform a scenario or technical
boundary without an execution test when the bounded proposition does not claim
future execution or an external state. A technical paper or discovery-only
item is not silently treated as an external factual observation either.

Management disclosure is explicitly a view through management's eyes in
[SEC MD&A guidance](https://www.sec.gov/rules-regulations/2003/12/commission-guidance-regarding-managements-discussion-analysis-financial-condition-results-operations).
That makes it valuable and direct for management's perspective, not an
automatic external-state truth.

## Opinion-to-evidence transformation

Recommendations, expert conviction, management tone and consensus never enter
Base as numerical evidence.  Process them as:

```text
opinion -> hypothesis queue -> checkable subclaims and causal bridge
        -> recover original measurements -> test incentives/common origin
        -> compare counterevidence and historical base rate
        -> independent review -> bounded analyst assumption or scenario
```

Record compensation/underwriting/issuer-payment exposure, management-access
dependence, stated position, sample selection, recency, extremeness, method and
forecast track record when available.  These are not mechanical optimism
haircuts.  They determine what the source is allowed to establish and what
independent evidence is needed.  Ten reports repeating one earnings call or
one market dataset remain one information root.

[CFA Standard V(A)](https://www.cfainstitute.org/standards/professionals/code-ethics-standards/standards-of-practice-v-a)
requires third-party research to be assessed for assumptions, rigor,
timeliness, objectivity and independence; [CFA Standard I(B)](https://www.cfainstitute.org/standards/professionals/code-ethics-standards/standards-of-practice-i-b)
requires fact and opinion to be distinguished and conflicts disclosed.  The
[SEC's analyst guidance](https://www.sec.gov/about/reports-publications/investorpubsanalystshtm)
explains why a recommendation should not be used alone.  Empirically,
[Jegadeesh and Kim](https://www.nber.org/papers/w12866) find recommendation
herding and [Ma et al.](https://www.nber.org/papers/w26830) document persistent
managerial forecast errors.  These findings justify provenance and
counter-hypothesis work, not a rule that every analyst or manager is biased in
the same direction.

## Availability, revision and versioning

Always preserve actual publication/availability time, the first release used in
the forecast, the first-reported company actual, the latest revised actual and
any segment/accounting recast. Accept all current evidence obtained through
evidence/model freeze. The scaffolding timestamp is lineage metadata, not a
source-eligibility boundary; later evidence creates a newer bundle or, after
publication, a new immutable forecast version.

For every observation preserve `published_at`, `available_at`, `vintage_at` and
`revision_at`; `available_at` is distinct from the economic period end and
retrieval time. `lag_days` recomputes from period end. An explicit revision
resolves to a prior observation of the same construct, period and scope rather
than overwriting it. The bundle records which version entered each model node,
so a later revision can trigger a new forecast version and its effect can be
reconciled separately from a model change.

## Independent triangulation

Select causal paths that can independently discriminate the material claim.
For a physical supply chain, common paths are:

```text
terminal: end demand * addressable content * supplier share -> company units
channel:  sell-through + change in customer/channel inventory -> sell-in
company:  production + change in company inventory -> shipments * realized price
```

Independence requires a different resolved root original, originating
organization/team and measurement method. Two brokers quoting the same
consultant, two publishers using the same panel, and market size derived from
the same shipment series are one measurement cluster.

Operationally, every cross-check names a `source_id`, `original_source_id`,
`independence_cluster` and `measurement_method_id`. The shared provenance graph
resolves the source to its root, publisher and authors/producing team, and a
purported independent check must differ on every substantive dimension. This
deliberately blocks circular corroboration: changing the URL, wrapper publisher,
unit conversion, cluster name or chart title does not create a second
measurement.

Independence is not comparability.  A conclusion-critical check must measure the
same metric construct (`metric_construct_id`) on a compatible unit/currency,
entity/product/geography scope, period and frequency.  An independently
measured Mars employee count therefore cannot corroborate Earth product demand.
When any of those fields differs, `cross_check_bridge_json` must provide a
quantified basis bridge for that series pair.  It must be a **structured numeric bridge**,
not a narrative formula: identify source and target observations and
units, select a controlled operation, list each signed adjustment with its own
source IDs, and provide finite source, bridged and target values plus an absolute
or percentage residual. Endpoint units must match the registered observations,
and endpoint and adjustment sources must remain accepted. The validator
recomputes both bridged value and residual; prose cannot manufacture
comparability.  The bridge also declares the
exact `mismatch_fields` and a `target_basis` matching every comparability field
of the target series.  Narrative such as "directionally consistent" is not a
bridge.
If the economic construct cannot be converted, remove it as corroboration and
limit it to monitoring or discovery.

Do not average paths to hide disagreement.  Reconcile product specification,
geography, ownership, frequency, fiscal/calendar time, unit, currency, gross/net
revenue and revisions.  Preserve the residual and a rival hypothesis.

## Data permission

```text
DataPermission = authority
              AND construct fit
              AND population fit
              AND time/vintage fit
              AND definition/unit fit
              AND causal proximity
```

If a condition fails, set the allowed use to `scenario_only`, `monitoring`,
`discovery_only` or `human_required`.  Source tier, lane count and article count
cannot override a failed condition.

`conclusion_critical` does not create a universal second-source quota. A single
direct hard anchor may remain accepted as a single anchor. Its failure risk,
the availability of another measurement and any resulting readiness cap are
decided in the frozen independent review. If a row claims `cross-checked` or
`corroborated` by populating cross-check fields, deterministic validation then
requires a bound accepted measurement with a genuinely independent root and
method, compatible definitions, or an executable quantified basis bridge. A
label or result narrative without that structure is not corroboration.

Examples of limited permission:

- non-probability or opaque panels: state/monitor unless independently checked;
- spot price with mismatched grade or low volume: scenario/monitor, not ASP;
- orders without cancellation rights or inventory visibility: order state only;
- papers without comparable conditions or replication: technical bound only;
- automatic captions: mechanism discovery; corroborate names, numbers and claims;
- patent counts/citations: search context, not product, FTO, share or moat proof.

## Frequency and transformation rules

- flows aggregate over time; period-end stocks do not sum;
- stock, average and flow denominators are explicit;
- fiscal and calendar quarters use an overlap bridge;
- reported, constant-currency and organic growth remain separate;
- price index, unit price and nominal revenue need compatible quality/mix bases;
- changes in classification, product specification or segment perimeter create a
  definition bridge, not a seamless time series;
- outliers are investigated for late reports, revisions, seasonality, product
  transitions, acquisitions, inventory valuation and one-time contracts before a
  cycle narrative is written.

## Research stopping rule

For each material node state the unresolved uncertainty, what the next source
could change and whether that change can alter scenario, profit or posture.  Stop
collecting low-impact sources when they cannot change the decision; continue when
the most sensitive node remains single-source, method-opaque or human-required.

## Required artifacts

- `source_manifest.json` — document lineage;
- `financial_fact_ledger.csv` — filing facts and restatement chain;
- `data_series_register.csv` — operating/industry observations and vintages;
- `source_independence_map.csv` — origin, method and transformation lineage;
- `claim_ledger.jsonl` — bounded claims and permissions;
- `model_graph.json` — the nodes those observations are allowed to drive.

The strict validator rejects missing vintages, definitions, scope, model links,
unknown or rejected sources/nodes and, whenever corroboration is claimed,
same-origin or method-incompatible cross-checks.
It also requires every declared main-line carrier to be supported by at least
one accepted, conclusion-critical measurement on that carrier or on a node that
the causal graph explicitly places upstream. A perfectly documented but
economically unrelated series cannot make a research-grade package complete.

## Method basis and misuse boundary

The IFRS Conceptual Framework supports relevance, faithful representation,
comparability, verifiability and timeliness.  IMF DQAF supports methodological
soundness, accuracy/reliability and serviceability.  SEC EDGAR documentation
defines the scope and limitations of structured filing data.  Official revision
policies and real-time datasets motivate vintage preservation.  These are method
permissions; they do not prove a particular series is accurate for a company.
