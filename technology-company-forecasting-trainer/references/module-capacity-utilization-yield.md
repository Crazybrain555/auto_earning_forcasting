# Module: capacity, utilization, yield, and process complexity

Use this primitive when revenue, gross margin, cash conversion, or capital
intensity depends on a physical bottleneck: manufacturing capacity, tool
throughput, availability, yield, customer qualification, constrained inputs, or
product/process mix. It is an accounting-and-causal schedule, not a generic
signal that high utilization must produce a wider upside case.

## Start with the source-specific capacity definition

Never combine capacity observations until each source-specific capacity
definition has been recorded. For every observation state:

- product, process/node/package, site and geography covered;
- physical unit and period denominator (per day, month, quarter, or year);
- whether the source reports nameplate, engineering maximum, sustainable
  maximum, installed, available, qualified, good-output, or saleable capacity;
- uptime, maintenance, product-mix, yield, qualification, outsourcing and joint
  venture assumptions already embedded in the reported number;
- reference period, publication date, data vintage, revision policy and any
  later restatement or classification change;
- whether the observation is a stock at period end, an average rate, actual
  production, shipment, or management's future target.

Build a `source_basis_bridge` when definitions differ. Do not multiply by yield
again when a source already reports good or saleable units; do not multiply by
utilization when the observation is actual production. A false precision
created by mixing denominators is worse than an explicit range.

## Canonical physical identities

Use only the factors not already embedded in the source basis:

```text
AvailableCapacity[t]
  = NameplateCapacity[t] × Availability[t]

QualifiedPotentialOutput[t]
  = AvailableCapacity[t] × Yield[t] × QualifiedShare[t]

InputConstraintEquivalentUnits[t]
  = minimum output supported by constrained materials, tools, labour,
    utilities, logistics and regulatory/export access

SaleableOutput[t]
  = min(DemandUnits[t], QualifiedPotentialOutput[t],
        InputConstraintEquivalentUnits[t])

Utilization[t]
  = ActualProduction[t] / AvailableCapacity[t]

Revenue[t]
  = UnitsShippedAndAccepted[t] × RealizedASP[t]
```

`SaleableOutput` is a production ceiling, not automatically a shipment or
revenue forecast. Bridge saleable output through finished-goods inventory,
shipment, customer acceptance, returns and the company's revenue-recognition
policy. Reconcile annual flows to quarterly or monthly schedules in the same
physical unit.

Where a limiting input cannot be converted credibly to equivalent output,
model a named constraint state and cap production in the formula graph rather
than inventing a precise conversion factor.

## Materiality-routed schedules and evidence

For each material branch select the factors that can change saleable output,
unit economics, cash or timing. Common factors include:

1. installed and available capacity by product/process/site;
2. maintenance downtime and operational availability;
3. yield, rework, scrap and rate/yield ramp;
4. engineering qualification and customer qualification by end use;
5. end demand, orders, cancellations, backlog and customer/channel inventory;
6. constrained materials, tools, labour, power, water, logistics and export
   access;
7. production, shipments, acceptance and realized price/mix;
8. variable input cost, depreciation, fixed-cost absorption and cash cost;
9. capex, construction-in-progress, commitments and funding;
10. source publication dates, vintage identifiers and revisions.

Demand, qualification and input constraints are separate causal nodes. A
backlog is not demand if cancellation rights are material. A design win is not
qualified production. Nameplate capacity is not good output. Good output is
not a sale. Preserve those distinctions in the driver tree.

## Capacity-investment and qualification clock

Model every expansion through explicit gates:

```text
approval → funding → permits/utilities → construction → equipment delivery
→ installation → engineering qualification → customer qualification
→ yield/rate ramp → saleable capacity → shipment → acceptance → revenue → cash
```

Each gate needs a dated state, source, probability or unresolved status, and a
falsification trigger. Announced capex is not Base-case available capacity.
Enter incremental capacity only when the preceding gates and expected lag
support it; reflect partial ramp, initial yield loss, duplicated operating cost
and depreciation before assuming mature economics.

## Pricing, mix and margin transmission

Capacity tightness does not have one universal margin sign. Separate:

- spot, contract and realized prices;
- product/customer mix from like-for-like price;
- utilization from yield and qualification;
- temporary fixed-cost absorption from structural unit-cost improvement;
- expedite, overtime, scrap, outsourcing and new-line dilution;
- customer dual-sourcing, substitution, redesign and inventory response.

Show the bridge from volume, price, mix and unit cost to gross profit and cash.
Measure incremental margin through more than one cycle state; do not infer
pricing power from utilization alone.

## Scenario response has no preset direction

Scenarios must be produced by named shocks to causal nodes, not by a universal
utilization threshold or a fixed upside/downside interval. Consider the
following only when material:

- end demand and customer/channel inventory;
- availability, yield and qualified share;
- constrained inputs and export/regulatory access;
- spot/contract/realized ASP and product mix;
- variable cost and fixed-cost absorption;
- capacity-project timing, attrition and competitor response.

A tight state can create upside through realized price and favorable mix, but
can also create downside through poor yield, maintenance, costly outsourcing,
customer dual-sourcing, accelerated rival supply or an inventory unwind. Let
the dated evidence and response function determine the direction and width of
the scenario range. Record which observations would move or invalidate each
case.

## Revision and version discipline

Capacity, utilization and industrial-production series are frequently revised
when source data, seasonal factors, benchmark weights or industry
classifications change. Preserve for every external series:

- `reference_period`, `published_at`, `vintage_id` and retrieval timestamp;
- first-released value and the exact version used by the forecast bundle;
- current revised value used for a later economic reconstruction;
- definition/classification version and a revision bridge;
- allowed use (`historical_anchor`, `base_parameter`, `scenario_bound`, or
  monitoring only).

A revised series creates a linked observation and, when material, a new forecast
version. Never overwrite the vintage bound to an earlier published decision.

## Applicability and failure modes

If capacity is not material to the company's economics, mark this primitive
`not_material_with_reason` and route to the appropriate demand, recurring
contract, order/backlog, or unit-economics primitive. Do not manufacture a
utilization schedule merely because the company mentions capacity.

Fail the model when it:

- uses capacity without a source-specific capacity definition;
- double-counts utilization, yield or qualification embedded in source data;
- treats capex or an announcement as immediately productive capacity;
- omits demand, qualification or an input constraint from saleable output;
- mixes physical units, sites, nodes, periods or data vintages without a bridge;
- converts saleable output directly to revenue without shipment/acceptance;
- assumes that higher utilization, content or complexity always raises margin;
- applies a preset scenario asymmetry rather than modeling the response;
- overwrites a first-release observation with a later revision.

## Primary methodological anchors

- Federal Reserve, *Industrial Capacity and Capacity Utilization Methodology*:
  https://www.federalreserve.gov/releases/g17/capnotes.htm
- Federal Reserve, *Industrial Production and Capacity Utilization: 2025 Annual
  Revision*: https://www.federalreserve.gov/releases/g17/revisions/current/defaultrev.htm
- U.S. Bureau of Labor Statistics, *Producer Price Index quality adjustment*:
  https://www.bls.gov/ppi/quality-adjustment/home.htm
- U.S. Bureau of Labor Statistics, *Producer Price Index calculation and
  revision policy*: https://www.bls.gov/opub/hom/ppi/calculation.htm
