# Analysis Kernel

This is the canonical reasoning spine for every company. Industry labels,
module names and familiar ratios are aids; none may replace the causal chain.

## The required chain

Every conclusion must be traceable in both directions through:

dated evidence → causal DAG → operating equations → integrated three
statements → ROIC, reinvestment and fade → valuation and reverse-implied
expectations → red team → monitoring.

Forward tracing asks what a fact changes in the model. Reverse tracing starts
from value per share or a key forecast and walks back to the evidence and
assumptions that caused it. A link that cannot be traversed is an unresolved
model risk, not an invitation to fill a cell with an analyst plug.

## Typed causal graph

Represent the company as a directed acyclic graph unrolled through time. Each
node records:

- stable node ID, entity and segment;
- node type: observed fact, derived fact, analyst assumption, state,
  operating output, accounting output, valuation output or monitor;
- period, unit, currency and accounting basis;
- source or derivation;
- uncertainty state and scenario applicability.

Each edge records:

- source and target node IDs;
- equation or transformation;
- expected sign and economic mechanism;
- lag or recognition window;
- evidence permission;
- falsification condition.

Financial nodes use statement roles, not the generic label `profit`.  Every
full-company main line contains typed nodes for `revenue`,
`operating_profit`, `pretax_profit`, `tax_expense`,
`noncontrolling_interest_net_income` (an explicit zero-valued node when absent)
and `gaap_net_income_attributable`.  Revenue must reach operating profit,
operating profit must reach pretax profit, and pretax, tax and the minority
claim must all reach the attributable-net-income target.  Free cash flow is a
later linked output; it cannot substitute for this reported-profit chain.

Feedback loops such as price → capacity → supply → price are not hidden. Unroll
them by period and state the lag. Correlation alone does not authorize an edge.
If several explanations fit the history, preserve competing hypotheses until a
discriminating observation arrives.

## Evidence permissions

Evidence does not become forecast input merely because it is interesting.

1. Establish identity, date, provenance, independence cluster and measurement
   basis.
2. State the narrow causal claim it supports.
3. Identify the graph edge or parameter it may change.
4. Record the rival explanation and the observation that would reject the
   claim.
5. Keep technical feasibility, manufacturing readiness, customer
   qualification, commercial commitment, accounting recognition and cash
   collection as separate permissions.

Papers and patents may establish a technical bound or mechanism. They do not
by themselves prove production, customer adoption, revenue, margin or value.
Management guidance may constrain a near-term range; it does not remove the
need to model the causal path.

## Main line and principal contradiction

Name the smallest causally sufficient set of thesis carriers. One or two is
often enough, but count is not a correctness test. The set must explain most
of the forecast change and valuation asymmetry. A thesis carrier is not a
score. It is a sequence of falsifiable nodes and equations, for example:

qualified capacity → saleable volume → mix-adjusted ASP → unit gross profit →
NOPAT → incremental invested capital → value.

Quantify how much revenue, NOPAT, FCF and value changes when each thesis carrier
is perturbed. The red team attacks these paths first. Secondary detail cannot
compensate for an unsupported main line.

## Subjective-judgment boundary

Subjective judgment is necessary, but it has four explicit homes:

1. selecting the main line and rival causal hypotheses;
2. defining named scenarios and their probabilities;
3. selecting a required return with a stated risk rationale;
4. selecting a margin of safety and resulting investment posture.

Judgment may not appear as manual importance weights, unexplained revenue CAGR,
balancing plugs, arbitrary margin paths or evidence scores presented as truth.
Inside each scenario, arithmetic and accounting remain deterministic.

## Build order

Use the only canonical stage order in `references/research-sop.md` and
`assets/method_system.json`.  This document defines the reasoning spine, not a
second workflow.  In particular, do not begin with a forecast template: close
`decision_contract` and historical reconstruction inside `evidence_system`,
then progress through `causal_graph`, `operating_model`,
`integrated_statements`, `value_creation`, `valuation`,
`scenarios_and_red_team`, `validation_and_readiness` and
`freeze_monitor_learn`.

## Hard gates

A case is not decision-ready when any of the following is true:

- a material output has no reversible path to dated evidence;
- segment revenue does not reconcile to consolidated revenue;
- a node mixes units, periods or recognition bases without a bridge;
- the three statements or required roll-forwards do not close;
- growth is disconnected from reinvestment and incremental returns;
- terminal economics require impossible competitive or capital conditions;
- the market-implied case is not expressed in named operating drivers;
- the main line lacks a falsification condition and monitoring owner.

Industry lenses may supply vocabulary, benchmarks or likely cycle variables.
They are optional calibration examples and never a dependency of this kernel.
