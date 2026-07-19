# Lens: equipment and process control

# Wafer-fab equipment playbook

Use the installed-base and revenue-quality rules in this lens and `module-orders-backlog-recognition.md`.

## Core revenue equation

```text
Systems revenue
= Σ(customer-spend cohort
    × process intensity
    × product share
    × shipment probability
    × installation/acceptance probability)

Support revenue
= contract service
+ spares/consumables
+ installed-base upgrades
+ mature-node/refurbished equipment
```

## Required customer cohorts

Separate DRAM, NAND, foundry, logic/IDM, geography and export controls. Avoid a single memory-WFE variable unless DRAM and NAND are demonstrably synchronized.

## Required schedules

- system revenue by customer cohort and product family;
- service/spares/upgrades/mature-node schedule;
- backlog and deferred-revenue quality bridge;
- shipment, installation, acceptance and control-transfer schedule;
- installed base, utilization and service attach;
- component supply and field-capacity constraints;
- gross-margin bridge by product, customer, geography, material/freight and utilization;
- export-control scenario.

## Failure modes

- treating a bundled support group as pure recurring service;
- treating deposits or deferred revenue as recognized one-year revenue;
- using total WFE as company revenue without process share and delivery timing;
- combining DRAM and NAND into one cycle;
- assuming installed-base revenue cannot decline;
- omitting field and factory utilization from gross margin.

# Process-control and inspection/metrology playbook

Use the installed-base and revenue-quality rules in this lens and `module-orders-backlog-recognition.md`.

## Core demand split

Separate two spending pools:

1. **Technology-development spend** — process learning, yield ramp, new-node and advanced-packaging development;
2. **Capacity spend** — tools added with wafer capacity.

Technology-development demand can lead or outperform aggregate WFE.

## Product revenue equation

```text
Product revenue
= Σ((technology-development spend + capacity spend)
    × inspection/metrology step intensity
    × capture rate
    × supplier share
    × shipment/acceptance probability)
```

Build categories separately where disclosed:

- wafer inspection;
- patterning / overlay / metrology;
- specialty semiconductor;
- PCB and display;
- other products.

## Service equation

```text
Service revenue
= installed base
× customer utilization
× attach / renewal rate
× service ASP
```

## Revenue quality and accounting

Split contract liabilities and RPO by near-term systems, shipped/unaccepted tools, deferred service and long-dated commitments. Model acquisitions, divestitures, impairment, amortization and tax separately.

## Failure modes

- revenue equals aggregate WFE × fixed share;
- technology-development and capacity spending are treated as one cycle;
- all process-control products share one growth rate;
- RPO is treated as one-year revenue;
- service is disconnected from installed base and utilization;
- acquired perimeter and impairment are omitted.

# Equipment revenue-quality bridge

Use this reference for wafer-fab equipment, process control and other hardware businesses whose reported service/support or deferred-revenue buckets combine different economic behaviors.

## 1. Decompose support revenue

Do not treat a named support business group as a single recurring annuity. Build:

```text
Support revenue
= contract service
+ spares and consumables
+ installed-base upgrades
+ mature-node / refurbished / Reliant equipment
```

Contract service may be recurring. Spares depend on utilization. Upgrades depend on node transitions and customer capital budgets. Mature-node equipment behaves more like systems revenue and can be cyclical.

## 2. Customer-spend cohorts

At minimum separate:

- DRAM;
- NAND / non-volatile memory;
- foundry;
- logic/IDM;
- geography and export-control overlay.

A single `memory WFE` variable is insufficient when DRAM and NAND are in different cycle states.

## 3. Deferred-revenue quality

```text
Deferred revenue / RPO
= customer deposits
+ shipped systems pending installation or acceptance
+ deferred contract service
+ long-dated commitments
```

Assign a separate recognition curve and cancellation/deferral risk to each bucket. Do not use total deferred revenue as a homogeneous one-year revenue floor.

## 4. Delivery and recognition

```text
Customer spend
→ order
→ backlog / deposit
→ shipment
→ installation
→ acceptance / control transfer
→ recognized revenue
```

For each step track component supply, field labor, customer fab readiness, export licenses and acceptance terms.

## 5. Margin bridge

```text
Gross margin
= product/service mix
+ customer/geographic mix
- material and freight cost
- factory under-utilization
- field-utilization / installation cost
- restructuring and transition cost
```

## 6. Scope rule

This bridge applies to equipment and process-control archetypes. Do not propagate it to commodity memory/storage, where bit volume, ASP, inventory and utilization are the primary equations.
