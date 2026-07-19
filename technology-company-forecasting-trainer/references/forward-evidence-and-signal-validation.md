# Forward evidence and signal validation

## Purpose

Use forward-looking evidence without letting optimism, channel noise, copied research, or future information contaminate a point-in-time forecast. This layer supplements statutory and official operating facts; it does not replace them.

## Evidence families and default permissions

| Family | Typical sources | Default permission |
|---|---|---|
| Official dialogue | Earnings Q&A, Investor Day, conference presentation, regulator/company response | Near-term driver or timing input with execution and incentive discount |
| Cross-company official read-through | Customer, supplier, competitor or standards-body disclosure | Demand/supply cross-check; never infer named supplier share without direct evidence |
| Independent industry research | Measured price, inventory, shipment, capacity, channel or end-market studies | State/timing input when methodology is transparent and the causal driver is specific |
| Named expert or field interview | Identified operator, engineer, purchaser, former employee or industry specialist | Hypothesis/timing input; Base only after independent corroboration and incentive review |
| Sell-side or deep research | Models, surveys, expert calls and expectation framing | Comparison, scenario and expectations; trace every key claim to its original source |
| Technical paper, standard or patent | Peer-reviewed paper, dated preprint, standards committee, patent | Feasibility, failure boundary and regime probability; not company revenue or share |
| Anonymous or copied channel claim | Unnamed checks, social media, second-hand notes | Monitoring/search trigger only |

## Evidence roles

Assign each signal exactly one primary role: `fact_anchor`, `state_signal`, `timing_signal`, `capacity_signal`, `adoption_signal`, `failure_boundary`, `perimeter_signal`, `scenario_probability`, or `monitor_trigger`. Split a source into separate SignalCards when claims have different roles.

## SignalCard minimum fields

Identity, publication/event/version/retrieval times, source tier and exact location, methodology, specificity, causal proximity, falsifiability, incentive bias, independence cluster, economic driver, horizon, time decay, allowed use, adjustment cap, model impact, limitations and next falsification point. Numeric quality fields route evidence; they are not calibrated probabilities.

## Independence rules

1. Reports quoting the same original company, expert, TrendForce, Gartner, IDC or channel count as one cluster.
2. A company statement and a sell-side note repeating it are not independent.
3. Customer and supplier disclosures may be independent when each describes its own facts.
4. A paper and a product announcement are different evidence types, but neither proves customer adoption alone.
5. Do not increase weight because many articles repeat the same original source.

## Permission gates

### Base point change

Require at least two independent evidence clusters, at least one direct, measurement-based or official-operating signal, a causal path from claim to driver to financial line, an adjustment cap and a falsification trigger.

### Scenario probability change

Allow one high-quality direct signal or two medium-quality independent signals. State old and new probabilities.

### Technical papers

Map through `paper/standard -> demonstrated benchmark -> prototype -> customer evaluation -> sample -> qualification -> production -> material revenue`. Before commercial Stage 3, technical evidence may change feasibility bounds or regime-tail probability only. It must not directly create company revenue, market share or margin.

### Experts and research reports

Use the original source where possible. Record methodology, sample, date, incentives and operational proximity. Anonymous expert conclusions remain E4 unless independently corroborated.

## Time decay

Spot price/channel/procurement signals decay in weeks or quarters; capacity/qualification/backlog in quarters to two years; architecture/standards may be multi-year but stage-dependent. Do not carry a stale signal without testing whether its driver materialized or reversed.

## Evidence-to-model cascade

Every material non-statutory input must show `source claim -> evidence role -> economic driver -> parameter/horizon -> financial output -> falsification trigger`. Missing links route the source to monitoring.

## Required ablation

Compare official/statutory evidence only with official plus accepted forward evidence, and technical/expert evidence under restricted permissions. Report point error, direction, sign, coverage and normalized interval score. Do not claim improvement when only the interval became wider.

## Point-in-time isolation

Freeze cutoff timestamp/timezone, retain publication/version dates, log historical queries/domains, prohibit future outcome terms and later product/transaction names, preserve rejected sources and run `validate_point_in_time_sources.py`. An unknown later transaction or shock uses `distribution-only` or `human-required`; never name or dimension it in Base.

## Full-company delivery requirement

A filings-only Source Pack is incomplete when external forward evidence is thesis-critical. The run workspace must contain `forward_signal_cards.csv`, `historical_query_log.csv`, `source_independence_map.csv`, a report section covering accepted/rejected/conflicting signals, and a red-team source-chain review. If no non-statutory signal survives, document the search and rejection.
