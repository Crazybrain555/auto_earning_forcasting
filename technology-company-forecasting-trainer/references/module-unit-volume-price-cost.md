# Module: unit, volume, price, mix, and cost

Use when revenue is primarily physical units, bits, wafers, components, or content per unit multiplied by price.

## Core equations

```text
Revenue[p,t] = Units[p,t] × Content[p,t] × ASP[p,t] × Share[p,t]
COGS[p,t] = Units[p,t] × UnitCost[p,t] + utilization/NRV/transition charges
```

## Required separations

- units/bit volume;
- content per unit;
- ASP and contract protection;
- mix;
- technical unit cost;
- effective unit cost after utilization, yield, fixed cost, and transition;
- customer/channel inventory;
- supplier inventory and capacity response.

## Typical companies

Memory/storage, GPUs/chips, materials, optical components, packaging, client devices, and industrial components.

## Failure modes

- replacing ASP with demand growth;
- treating content growth as revenue growth without price erosion;
- treating density improvement as equal cost reduction;
- ignoring inventory, NRV, fixed-cost absorption, or pass-through BOM;
- assuming a customer platform proves supplier share.
