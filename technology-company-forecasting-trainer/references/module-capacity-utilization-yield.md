# Module: capacity, utilization, yield, and process complexity

Use when revenue or margin is constrained by production capacity, tool throughput, fab utilization, yield, node mix, package complexity, or qualified manufacturing capacity.

## Core equations

```text
Deliverable units = Installed capacity × Utilization × Yield × Qualified share
Revenue = Deliverable units × Blended ASP
```

## Required schedules

- installed and available capacity;
- node/process/package mix;
- utilization;
- yield and ramp;
- depreciation and fixed costs;
- materials and energy;
- capex and construction lag;
- customer qualification;
- geographic/export overlays.

## Typical companies

Foundries, OSAT, advanced packaging, materials manufacturing, memory fabs, and selected equipment businesses.

## Supply-tightness asymmetric interval rule

When observable utilization is elevated and supply is tight at `as_of`, the forecast interval must be asymmetric: the upside tail is wider than the downside because supply tightness compounds favorably through pricing power, mix shift toward advanced nodes, and accelerated capacity additions that themselves generate revenue once qualified.

**Applicability.** Both conditions must hold:

1. Blended utilization is at or above 85% at the `as_of` date, with E0/E1 evidence (official disclosures, quarterly filings, industry data).
2. At least one of: (a) pricing power is confirmed by rising blended ASP or favorable node-mix shift in recent quarters, (b) capacity expansion (new fabs, tools, lines) is under construction with disclosed timelines, or (c) customer demand signals (design wins, wafer-start commitments, order backlogs) exceed current deliverable capacity.

**Rule.** For FY+2 and FY+3:

- Set the Bull-case revenue at least 15% above the Bear case (i.e., the upside range from Base is wider than the downside range from Base). The exact asymmetry derives from the measured pricing, mix, and capacity-addition evidence.
- The Base case itself should reflect the compounding effect: if utilization stays above 85%, ASP and mix trends observed in recent quarters persist into FY+2/FY+3 rather than mean-reverting to cycle-average levels by default.
- When capacity additions have disclosed qualification timelines, include their incremental revenue contribution in the Base from the qualification date forward, not from the capex announcement date.

**Failure conditions — do not apply when:**

- utilization is below 85% or declining quarter-over-quarter at `as_of`;
- pricing power is not confirmed by recent ASP or mix data (narrative-only claims of tightness);
- a known demand shock (e.g., pandemic, export restriction, major customer loss) at `as_of` makes the supply-tightness transient;
- the company is a pure equipment supplier (use the orders-backlog module instead — supply tightness at the customer benefits the equipment maker through orders, not through utilization of the equipment maker's own capacity).

## Failure modes

- treating capex as immediately productive capacity;
- ignoring yield and qualification;
- using total capacity without node/customer mix;
- assuming higher content always increases margin;
- omitting overseas-fab or new-line dilution.
