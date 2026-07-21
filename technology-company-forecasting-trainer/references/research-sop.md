# Earnings-Power Research SOP

This is the operating procedure for the forecasting system.  The objective is
not to complete a checklist.  It is to produce a dated, falsifiable estimate of
future revenue, operating profit and GAAP net income attributable, and to know
which observations would change that estimate.

Forecasting quality is the governing objective.  It means economically and
financially coherent reasoning that continues to work on unfamiliar companies,
industries, lifecycle states and cycles.  No scalar score, error metric,
coverage ratio, test count or validator pass rate is a proxy for that objective.
Quantitative measures diagnose particular failure modes; they never become the
thing the method optimizes at the expense of logic or generalization.

The procedure is deliberately smaller than the set of available references.
Specialist modules are tools used inside a stage; they are not extra stages and
they do not create a second constitution.

## First principles

1. **The company is an economic system before it is a spreadsheet.**  Identify
   who pays, what is delivered, the scarce resource, the unit of demand, the
   unit of capacity, the price-setting mechanism, the cost-bearing resources,
   the accounting recognition event and the cash-conversion path.
2. **A forecast is an executable causal argument.**  Every material forecast
   number is either a dated observation, a declared scenario assumption or the
   result of a typed equation.  Narrative cannot be used as a hidden numeric
   input.
3. **Accounting is conservation, not decoration.**  Revenue, operating profit,
   pretax profit, tax, NCI and attributable net income must be produced by the
   same model path. Stocks roll and statements reconcile by construction; the
   earnings-power view also closes NOPAT to after-tax operating cash flow plus
   the change in net operating assets rather than adding an accrual score.
4. **Uncertainty belongs at the uncertain cause.**  The reference path and
   case-selected material rival states change named demand, price, mix, cost,
   timing, capacity, cycle or accounting-state inputs and then re-execute the
   model. Encode exactly one path as `role=reference` and each authored rival
   as `role=alternative`; scenario IDs remain free descriptive names. The
   reference may have no shock, while every alternative names the causal shock
   that distinguishes it. No fixed number of alternatives or naming taxonomy
   is required. Scenarios are not independent edits to output rows.
5. **Value investing asks about normalized earning power and its duration.**
   Current earnings are decomposed into cash/accrual, cycle, temporary
   investment, accounting and structural components.  Mean reversion is a
   reference-class prior; company evidence determines the departure and fade.
6. **Complexity has to earn its place.**  Add a source, branch, schedule or
   parameter only if it can materially change the distribution of revenue,
   operating profit or attributable net income, distinguish a rival
   hypothesis, or prevent a known accounting/data error.  Otherwise keep it as
   optional research context.
7. **Unknown is a valid state; zero is a number.**  Missing disclosure never
   becomes zero, a carried ratio or a precise useful life without an explicit
   limitation and scenario consequence.
8. **Authority attaches to a proposition, not a logo.**  Audited filings anchor
   reported financial facts; management directly establishes its own view and
   intent; customers and regulators establish facts within their boundary.
   None may silently prove a different external state or future outcome.
   Expert, broker and management opinions are decomposed into testable claims,
   provenance and incentives before an analyst independently authors Base.

## Canonical stage loop

Do not author all delivery artifacts in parallel.  Complete one stage, review
its economic exit question, and move forward only when the answer is adequate.
When it is not, loop to the named earlier stage.

The IDs below are the only stage IDs used by `assets/method_system.json`, the
run manifest, documentation and stage review.  Other documents may explain a
stage but must not invent another numbered workflow.

| Stage ID | Work | Required exit question | Canonical authored state |
|---|---|---|---|
| `decision_contract` | Define entity, security, consolidation perimeter, accounting basis, fiscal calendar, currency, horizons and decision. Pre-register the initial view, rival explanations and largest unknowns before broad research. The runtime records a snapshot identity automatically; it does not close research or limit which current evidence may enter. | What exactly is being forecast, for whom, and on which accounting/perimeter basis? | contract and hypothesis register |
| `evidence_system` | Reproduce at least three comparable annual periods and the latest interim when disclosed, then search specifically for uncertain nodes and rival hypotheses. Preserve each quantitative observation's value, observed construct, actual availability time, vintage/revision chain, definition, scope, conflicts and failed searches. Current evidence continues to enter until publication freeze. | Can the system explain the historical profit chain, and is every material input definition-compatible, dated and traceable to its origin? | source, claim, observation and financial-fact ledgers |
| `causal_graph` | Map the industry/company boundary and select the smallest causally sufficient set of thesis-carrying paths plus a serious rival. One to three is common, never a hard cap. | Which few causal changes explain most of future revenue and operating-profit variation, and what would refute them? | typed causal graph and thesis/rival register |
| `operating_model` | Choose the smallest unit/price/cost, cohort, capacity, order-recognition or other equations for each material branch; represent demand, supply, stocks, cycle and commercialization gates. | Do the equations represent how the company earns money and where the industry profit pool moves? | assumptions and executable operating equations |
| `integrated_statements` | Execute the operating model by period into revenue, costs, operating profit, pretax, tax, NCI, attributable net income, cash, capital and shares. | Does one causal path mechanically produce the complete statements without plugs? | accounting equations and reconciled statement views |
| `value_creation` | Separate reported/normalized/cash earnings; close the NOPAT/operating-FCF/ΔNOA bridge; estimate reinvestment, incremental ROIC, competitive response, conditional mean reversion and fade. Preserve an unavailable reference class as a limitation instead of fabricating a peer set or fixed horizon. | Which earnings are sustainable, what capital produces them, and why should excess returns persist or decay? | earnings-power, reinvestment and fade equations |
| `valuation` | Value the resulting cash flows/residual income and reverse the market price into named operating drivers. | What future earning power and duration does the price require? | valuation equations and price-implied expectations |
| `scenarios_and_red_team` | Change named causal inputs, re-execute joint paths, attack the main line first and record independent disagreements. | What credible state breaks the thesis, and does it propagate through revenue, operating profit and net income? | scenario overrides and frozen independent review |
| `validation_and_readiness` | Apply the orthogonal assurance portfolio and resolve or disclose material conflicts. | Are logic, evidence, execution and investment relevance jointly adequate without metric gaming? | review decisions and readiness limits |
| `publish_monitor_version` | Generate workbook/snapshot/report from canonical state, validate the final input pack, atomically commit a registry-bound seal, and bind decisive future observations to model actions. Material updates create a new forecast identity that explicitly supersedes the prior publication. | Is the result reproducible and immutable now, and which evidence would require a new version? | published bundle hashes, atomic seal and executable monitors |

## Authored state versus generated views

The method has four authoring surfaces:

1. the decision/hypothesis contract;
2. source, claim, observation and financial-fact ledgers;
3. the typed causal/equation graph and named scenario overrides;
4. analyst judgment on scenario probabilities, required return, margin of
   safety and posture.

The historical bridges, operating schedules, scenario profit paths, integrated
statements, earnings-power bridge, valuation, monitoring table, workbook,
snapshot and report are **views of that state**.  They should be generated or
reconciled from stable IDs and equations, not independently populated with a
second copy of the same number.  During the migration to a fully compiled case
model, a legacy view may still be present, but it never becomes an independent
source of truth.

## Research control: question before source

For every material research query record:

- the node or rival hypothesis being investigated;
- the present range and why it matters to revenue, operating profit or net
  income;
- the type of observation that can discriminate between explanations;
- the root measurement sought, not merely a preferred publisher;
- the stop condition: what result would make another search unlikely to change
  the forecast or decision.

This prevents broad source collection from becoming confirmation bias.  Source
prestige never repairs a definition mismatch.  Several links derived from one
measurement remain one origin.  An independent cross-check must be independent
in root origin, originating organization/team **and** measurement method, and
must reconcile its definition to the model construct.  Resolve that provenance
once at ingestion and reuse the shared graph in forward-signal, data-series and
technical-evidence validation; changing a cluster label cannot create a new
origin.  Any material scope conversion uses the shared structured numeric bridge
whose adjustments and residual are recomputed, never a narrative formula.

Before resolving a disagreement, classify each assertion as reported history,
current observed state, management intent, external-party state, future
estimate or causal interpretation.  Apply the source only inside its authority
scope.  Check whether apparent conflict is a basis/perimeter/period/unit issue;
if genuine, preserve both explanations and seek a different root measurement.
Every SourceRecord also declares exactly one controlled `epistemic_class`:
`official_reported_fact`, `independent_external_observation`,
`management_statement_or_plan`, `expert_or_analyst_opinion`,
`technical_evidence` or `discovery_only`. `source_type` and `role` only route
retrieval/workflow and cannot grant factual authority. Each source also has a
controlled `origin_record_kind`, which is a permission ceiling rather than a
quality score: a class may be narrowed but cannot exceed the affirmative kind
of original record actually preserved. If an expert, analyst or
management source cites a verifiable external measurement, record that original
measurement as a separate SourceRecord with its true publisher, method and root
lineage; do not reclassify the opinion document as an observation.
Do not turn consensus, management guidance or expert conviction into a vote or
a generic haircut.  Recover the underlying observations, record incentives and
common origins, construct a counter-hypothesis, and let an independent reviewer
decide whether the resulting analyst assumption is sufficiently grounded.
Encode the result in `claim_ledger.jsonl` as one bounded source-to-claim link,
not only a source list. Keep support, contradiction and context distinct; an
unresolved contradiction keeps the claim contested. Management self-report
can directly anchor management's own stated plan. Base use must preserve it as
a management forecast, document historical bias/range and its application
boundary, and obtain claim-specific permission from the review frozen to the
current claim ledger. A bridge from that plan to future execution or external
state needs a named causal or external test. The same test is required for
every model-changing claim whose proposition scope is `future_execution` or
`external_state`, independent of its source label; `reported_fact` cannot name
either scope. Its causal/external test must be a valid
`independent_external_observation`, and the evidence link must bind its
`observation_ids` to the observation-level record in
`data_series_register.csv`. That record carries the construct, value, period,
unit, vintage and method; the SourceRecord carries the originating team,
durable locator and content hash. An analyst-authored Base assumption also
needs claim-specific frozen permission whose reviewed source IDs, epistemic
classes and origin kinds exactly match the frozen SourceRecords. For an
external observation, the review additionally binds the computed
source-plus-observation fingerprint and gives a substantive classification
rationale. Code checks that this
judgment is current and faithfully applied; it does not replace the reviewer
with a score or source quota.

## Minimal-model rule

Start with the smallest causal model that can close the profit chain and a
simple historical carry or other economically appropriate rival explanation.
Add one mechanism at a time.  Each addition records:

- the forecast error, rival hypothesis or material risk it addresses;
- the target output and expected direction of change;
- the new evidence and equation;
- an ablation or sensitivity showing the mechanism contributes a distinct
  causal or decision-relevant result;
- a retirement condition if it adds no forecast or decision value.

More fields, documents, checks or model detail are not improvements by
themselves.

## The validator's limited role

Validation is the final safety net, not the research engine.  Strict delivery
has only five classes of non-negotiable invariant:

1. **model identity and evidence inclusion** — entity/perimeter/accounting
   identity, source availability/vintage, conclusion permissions and explicit
   inclusion in the bundle frozen for publication;
2. **provenance and type** — stable IDs, root origin, definition, period, unit,
   currency and accounting basis;
3. **equation execution** — derived values and scenario paths recompute from
   referenced operands;
4. **accounting conservation** — explicitly exhaustive, mutually exclusive
   partitions and stock-flow, statement and per-share identities close; partial
   or overlapping customer/product/geography views remain cross-checks rather
   than being forced to 100%;
5. **evidence-to-conclusion lineage** — every material conclusion reverses to
   an admissible observation or declared assumption, with a falsifier.

Breadth counts, prose length and the mere presence of a schedule may be useful
warnings, but they cannot manufacture decision readiness.  A new validator is
admitted only when the failure cannot be prevented by a stage design, shared
type, shared provenance resolver or shared equation primitive.  When admitted,
it must replace or consolidate the overlapping rule rather than create a new
parallel truth.

## Orthogonal assurance, not test accumulation

Review the case from a small number of independent angles.  A test belongs to
one primary angle; if two tests fail on the same underlying defect and neither
adds a distinct decision, consolidate them.

| Assurance angle | Question | Primary reviewer |
|---|---|---|
| economic causality | Does the model represent how this company earns money and the principal contradiction, including a credible rival? | independent industry/model agent |
| evidence and data | Are material observations dated, definition-compatible, independently corroborated where needed, eligible for the active run mode, and is noise/conflict preserved? | independent evidence agent |
| accounting and execution | Do referenced equations execute and do stocks, statements, scenarios and per-share bridges conserve value? | deterministic runtime plus accounting agent |
| disconfirmation and investment relevance | Does the downside attack the actual thesis, and do price-implied expectations, monitoring and margin of safety follow from the model? | independent red-team/investment agent |
| clarity and reproducibility | Can another analyst trace a conclusion backward and reproduce it without hidden assumptions? | independent delivery reviewer |

Deterministic tests are appropriate for types, hashes, bundle membership, referenced
IDs, equation recomputation and accounting identities.  They are not allowed to
decide that a moat is real, that a paper transfers to production, that a chosen
reference class is economically sound, or that the main line is insightful.
Those judgments require an independent agent that did not build the case, has
not seen the builder's preferred conclusion before recording its critique, and
cites the case evidence behind its decision.

Independence is substantive, not a role label.  Reusing the same prompt,
summary, assumptions and preferred thesis under a different agent name is not
an independent review.  The reviewer receives the frozen evidence and model,
can reconstruct its own rival explanation, and returns findings before the
builder responds.  Unresolved material disagreement lowers readiness; the
builder cannot edit the review into agreement.

There is no target equation count.  The acceptable model is the smallest
equation set that explains material changes in revenue, operating profit and
attributable net income, represents required stocks and accounting identities,
and distinguishes the main line from its rival.  Equation count, artifact
count, test count and citation count are complexity diagnostics, never quality
scores.

## Stop and loop rules

- If `evidence_system` does not reconcile history, do not forecast; return to accounting scope,
  facts and restatement lineage.
- If `causal_graph` needs many unrelated drivers to explain the thesis, compress the
  thesis or admit that the edge is weak.
- If the evidence cannot distinguish the main line from its rival, keep the
  disputed input out of Base or widen the named state; do not average stories.
- If `integrated_statements` only closes through a plug, return to the operating equation or
  accounting bridge that created the residual.
- If most value comes from an unsupported fade or terminal assumption, cap the
  posture and return to `value_creation`; a sensitivity table is not a cure.
- If new research cannot change a material node, scenario or posture, stop
  collecting it.

## What specialist references are for

Equation modules explain how to implement one branch.  Industry lenses suggest
useful variables, failure modes and sources.  Accounting, paper, patent, cycle
and intangible-investment references deepen a material issue.  None is a
mandatory checklist for every company.  Route by the company's economics and
material uncertainty, not its sector label.
