# Research lanes and corroboration

An audit of three live runs found the research was filings-only: management
forward commentary, sell-side and industry research, expert/channel work, and
technical literature were all absent from the query logs. Filings are audited
history; they cannot answer what happens next. This file makes lane coverage
and cross-validation enforceable.

Two principles:

1. **Breadth is required.** A forecast built from one lane is one lane's
   blind spots wearing a model.
2. **Credibility is asymmetric.** Low-tier lanes are valuable *and*
   dangerous. They may generate hypotheses freely; they may only set Base
   numbers under corroboration.

## The eight lanes

| # | Lane | Examples | Default tier | Base permission |
|---|---|---|---|---|
| L1 | Official filings | 10-K/10-Q/8-K, prospectus, annual report | E0 | Base anchor |
| L2 | Management voice | earnings call, investor/analyst day, conference keynote, CEO/CFO interview, fireside chat, 业绩说明会, 投资者关系问答 | E1 | Base driver, guidance-bias adjusted |
| L3 | Cross-company official | customers/suppliers/competitors describing this company or the shared value chain | E1 | Base driver |
| L4 | Industry data | TrendForce, IDC, Counterpoint, Yole, TechInsights, Omdia, SEMI | E3 | Base driver only if method disclosed |
| L5 | Sell-side / broker research | broker models, initiation notes, industry primers | E3 | Never Base alone - corroboration required |
| L6 | Expert & channel work | expert-network calls, supply-chain checks, distributor/dealer checks, 产业链调研 | E4 (E3 if named expert + disclosed method) | Monitor/trigger only unless corroborated |
| L7 | Technical literature | papers, standards, patents, roadmaps (see `technology-trend-evidence.md`) | E2 | Timing/feasibility/scenario only, never Base point |
| L8 | Trade press & articles | reputable trade media, quality long-form analysis | E3/E4 | Never Base alone - corroboration required |

Lane ≠ truth ranking. An expert channel check can be more informative than a
10-K; it is simply less verifiable, so it carries a different permission.

## Coverage requirement

Every delivery's `historical_query_log.csv` must show searches spanning at
least **5 of the 8 lanes**, and **L2 (management voice) is mandatory** - a
technology forecast that never read the earnings call, investor day, or a
management interview has not done the work. L7 is mandatory for FY+2+
horizons (see `technology-trend-evidence.md`).

Log every search whether or not it found anything: an empty lane with a
recorded query is a documented negative; an empty lane with no query is a
gap. Record the queries that failed - they show where evidence does not exist.

## The corroboration rule

**Materiality is computed, never assigned.** An assumption does not become
important because someone typed 0.15 next to it - that is factor scoring in
disguise. It is important if perturbing it moves the answer. Every row of
`material_assumption_support.csv` therefore states:

- `test_delta` - the perturbation actually tested ("-5pp ASP", "ramp slips
  two quarters", "share holds flat instead of +3pp"), and
- `revenue_impact_pct` / `profit_impact_pct` - what the model does under it,
  and
- `changes_conclusion` - whether the rating or buy price flips.

An assumption is **material** when the tested perturbation moves FY+1 revenue
≥2%, profit ≥5%, or flips the conclusion. Those thresholds are on measured
output, so a reviewer can re-run the test and disagree with a number rather
than with a weight.

A material assumption requires:

- support from **≥2 independent source clusters** spanning **≥2 different
  lanes**, and
- at least one of those from an **anchoring lane** (L1, L2, L3, or a direct
  measurement), unless the assumption is explicitly labeled `scenario_only`.

An assumption that flips the conclusion must additionally state its
falsification trigger - if the whole call turns on it, the reader is owed the
observation that would kill it.

`support_status` values in `material_assumption_support.csv`:

| Status | Meaning | Allowed use |
|---|---|---|
| `hard_anchor` | L1/L2 direct disclosure of this exact quantity | Base point |
| `corroborated` | ≥2 lanes agree, ≥1 anchoring | Base driver |
| `single_lane` | only one lane supports it | Scenario/monitor only - may not carry Base |
| `contested` | lanes disagree | Both readings recorded; Base states which and why |
| `scenario_only` | speculative by construction | Tail/scenario weight only |

A single-lane claim that carries a Base number is the specific failure this
rule exists to prevent.

## Handling low-credibility lanes well

- **Record the incentive.** Sell-side has banking and access incentives;
  experts are paid and often former employees with stale or partial views;
  trade press amplifies whoever briefed them. Note the incentive per source.
- **Prefer disclosed method.** An industry-data point with a stated
  methodology outranks a bigger name without one.
- **Trace to the original.** Three articles repeating one analyst note is one
  source; `source_independence_map.csv` must collapse them into one cluster.
- **Date everything.** Expert views decay fast; a channel check older than one
  quarter is a historical observation, not a current read.
- **Contradiction is signal.** When management voice and channel work
  disagree, that gap is often the most valuable thing in the pack. Record it
  and let it widen the scenario spread rather than averaging it away.

## Management-voice specifics (L2)

Prioritise, in order: (1) the most recent earnings call Q&A - the analyst
questions reveal what the market doubts; (2) investor/analyst day materials -
where multi-year targets and segment detail live; (3) conference keynotes and
fireside chats - often the first place a strategy shift is voiced;
(4) executive interviews in trade or business media; (5) IR follow-up Q&A.

Treat guidance as a management-adjusted quantity, not a fact: record the
company's historical guidance-versus-actual bias where computable, and state
whether the Base uses guidance as given, haircut, or raised, with the reason.
