# Forward evidence and signal validation

## Purpose

Use forward-looking evidence without letting optimism, channel noise, copied research, or future information contaminate a point-in-time forecast. This layer supplements statutory and official operating facts; it does not replace them.

## Evidence families and default permissions

| Family | Typical sources | Default permission |
|---|---|---|
| Official dialogue | Earnings Q&A, Investor Day, conference presentation, regulator/company response | Near-term driver or timing input with execution and incentive discount |
| Cross-company official read-through | Customer, supplier, competitor or standards-body disclosure | Demand/supply cross-check; never infer named supplier share without direct evidence |
| Independent industry research | Measured price, inventory, shipment, capacity, channel or end-market studies | State/timing input when methodology is transparent and the causal driver is specific |
| Named expert or field interview | Identified operator, engineer, purchaser, former employee or industry specialist | Hypothesis/timing input; a directly observed, definition-compatible fact can enter Base only after proposition-scoped authority and incentive review |
| Sell-side or deep research | Models, surveys, expert calls and expectation framing | Comparison, scenario and expectations; trace every key claim to its original source |
| Technical paper, standard or patent | Peer-reviewed paper, dated preprint, standards committee, patent | Feasibility, failure boundary and regime probability; not company revenue or share |
| Anonymous or copied channel claim | Unnamed checks, social media, second-hand notes | Monitoring/search trigger only |

Suggested machine slugs for `source_family` include `official-dialogue`,
`cross-company-official`, `industry-research`, `expert-field`,
`sell-side-research`, `technical-paper-standard`, `news-event`,
`official-product`, `measurement`, `regulatory`, `official-transaction` and
`anonymous-channel`.  They route default permissions; they are not a required
coverage taxonomy.  Add a family when the measurement method demands it.  A
full delivery has as many SignalCards as there are distinct accepted claims—no
card, family or citation quota creates research quality.

## Evidence roles

Assign each signal exactly one primary role: `fact_anchor`, `state_signal`, `timing_signal`, `capacity_signal`, `adoption_signal`, `failure_boundary`, `perimeter_signal`, `scenario_probability`, or `monitor_trigger`. Split a source into separate SignalCards when claims have different roles.

## SignalCard minimum fields

Identity, `source_id`, `claim_ids`, publication/event/version/retrieval times, source tier and exact location, methodology, specificity, causal proximity, falsifiability, incentive bias, economic driver, horizon, time decay, allowed use, adjustment cap, model impact, limitations and next falsification point. The `source_id` must resolve through the shared provenance graph to its root original, publisher/originating team, measurement method and independence cluster; fields copied onto a SignalCard must match that source record. Numeric quality fields route evidence; they are not calibrated probabilities.

## Independence rules

1. Reports quoting the same original company, expert, TrendForce, Gartner, IDC or channel count as one cluster.
2. A company statement and a sell-side note repeating it are not independent.
3. Customer and supplier disclosures may be independent when each describes its own facts.
4. A paper and a product announcement are different evidence types, but neither proves customer adoption alone.
5. Do not increase weight because many articles repeat the same original source.

Cluster labels are indexing aids, not proof.  A purported independent pair must
have different resolved roots, originating organizations/teams and measurement
methods. `derived_from_source_id` and `common_origin` survive republication,
translation, chart extraction and database resale; renaming a cluster cannot
turn one observation into two.

## Permission gates

### Common model-changing binding

Every model-changing permission is proposition-bound. `base_point`,
`base_driver`, `base_parameter`, `historical_anchor`, `technical_bound`,
`scenario_only` and `scenario_probability` each require one or more accepted
`claim_ids`. For every named claim:

- the SignalCard's own `source_id` is a `support` evidence link, not merely a
  source elsewhere in the claim;
- `model_driver` is one of the claim's `driver_node_ids`;
- claim use matches the card semantics (`historical_anchor`/`base_parameter`
  for Base, `technical_bound` for a technical bound and `scenario_only` for an
  authored state or probability); and
- management-, analyst-, expert- or scenario-derived subjectivity has an
  `adequate` current frozen judgment for that exact claim, source set and use.

`monitor`, `monitor_trigger`, `search_trigger`, `discovery` and
`discovery_only` do not change model state and therefore need no claim binding.
Changing one of those rows to a model-changing use activates the full contract.
`source_family` is never read as authority, and no source or claim count is a
permission rule.

### Base point change

A direct, definition-compatible measurement or official operating observation
may be a hard anchor by itself.  When corroboration is claimed, the observations
must resolve to genuinely independent roots, originating teams and measurement
methods.  In either case require a causal path from claim to driver to financial
line, an adjustment cap and a falsification trigger.  A pile of secondary links
cannot repair a weak anchor.

### Scenario probability change

Change probability only when the evidence is relevant to the named transition,
its measurement and reference-class basis are explicit, and the frozen
independent review accepts the inference. State old and new probabilities.
Neither a source count nor a tier tally substitutes for that reasoning.

### Technical papers

Map through `paper/standard -> demonstrated benchmark -> prototype -> customer evaluation -> sample -> qualification -> production -> material revenue`. Before commercial Stage 3, technical evidence may change feasibility bounds or regime-tail probability only. It must not directly create company revenue, market share or margin.

### Experts and research reports

Use the original source where possible. Record methodology, sample, date,
incentives and operational proximity. Anonymous conclusions cannot authorize a
Base parameter because their identity, authority and conflicts cannot be
audited; use them as search or monitoring triggers.

An expert or analyst SourceRecord remains subjective regardless of a claim's
declared `claim_type`. It cannot be laundered through `reported_fact` to obtain
historical-anchor, technical-bound or scenario permission; use a bounded
analyst assumption or scenario claim and obtain the matching frozen review.
When that bounded claim itself asserts `future_execution` or `external_state`
and changes the model, the opinion also needs a named `causal_test` or
`external_test` from an independent factual observation. This extra bridge is
not required for a reviewed scenario-only or technical-bound proposition that
does not cross into execution or external-state fact.

The bridge is an observation record, not a renamed document. The source must
have the affirmative `origin_record_kind=original_measurement_observation` and
a compatible epistemic class; the evidence link names the corresponding
`observation_ids` from `data_series_register.csv`. The independent review binds
the source content hash, origin kind, measurement method and computed
observation fingerprint, then records why the inspected content is a direct
measurement. An expert transcript or broker note may point to that record but
cannot itself become it by changing `source_type`, role or class.

## Time decay

Spot price/channel/procurement signals decay in weeks or quarters; capacity/qualification/backlog in quarters to two years; architecture/standards may be multi-year but stage-dependent. Do not carry a stale signal without testing whether its driver materialized or reversed.

## Evidence-to-model cascade

Every material non-statutory input must show `source claim -> evidence role -> economic driver -> parameter/horizon -> financial output -> falsification trigger`. Missing links route the source to monitoring.

## Required ablation

Re-execute the same causal and financial model first with official/statutory
evidence only, then with accepted forward evidence under its proposition-level
permissions.  Hold equations and unrelated assumptions fixed.  Record which
driver nodes and financial lines move, the direction and horizon of the move,
the change in scenario ranges or decision posture, whether the signal
distinguishes the main line from its rival, and the observation that would
reverse the change.  This is a live causal-sensitivity test: evidence earns use
by changing a named mechanism in a bounded, falsifiable way.  A wider interval
or a different point with no causal bridge, rival discrimination or action
change is not an improvement.

## Availability and version isolation

Always retain publication/version/availability dates and preserve rejected
sources. Current research accepts signals through evidence/model freeze. A later
source version remains a separate record and may create a new bundle; it never
overwrites the observation or claim bound to a published forecast.

## Full-company delivery requirement

A filings-only Source Pack is incomplete when external forward evidence is
thesis-critical. The run workspace must contain `forward_signal_cards.csv`,
`source_independence_map.csv`, a report section covering
accepted/rejected/conflicting signals and a red-team source-chain review.
If no non-statutory signal survives, document the search and rejection.
