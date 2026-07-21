# Lens: memory and storage
# Memory and storage playbook

Use this playbook for DRAM, NAND, HBM, enterprise/client/mobile SSD, embedded flash, context storage, high-bandwidth flash, and companies that manufacture through unconsolidated or jointly operated fabs.

## 1. Required model grain

Build the operating model at the lowest disclosed economic grain, normally:

```text
end market or product
× bit / unit shipments
× ASP per bit, GB or unit
× unit cost per bit, GB or unit
```

Typical NAND end markets are Datacenter, Edge/client/mobile/embedded, and Consumer/retail. Do not use one company-wide revenue CAGR when the mix and price cycles differ materially.

For the next four quarters, anchor the model to reported quarterly segment revenue, bit shipments, ASP changes, company guidance, and the latest exit rate. Thereafter, transition to annual bit, ASP and cost paths with explicit cycle-state probabilities.

## 2. Revenue and gross-profit equations

```text
Revenue[p,t]
= BaseRevenue[p]
× cumulative_bit_index[p,t]
× cumulative_ASP_index[p,t]

COGS[p,t]
= BaseCOGS[p]
× cumulative_bit_index[p,t]
× cumulative_unit_cost_index[p,t]

GrossProfit[p,t]
= Revenue[p,t] - COGS[p,t]
```

Do not infer product gross margins from company gross margin without labeling the result as an analyst calibration. Reconcile the calibrated product margins back to company guidance.

## 3. Contract, NBM, LTA and RPO bridge

Keep four concepts separate:

1. legal quantity commitment;
2. price protection or floor-price coverage;
3. actual execution / enforceability;
4. revenue-recognition timing.

```text
Effective price-protected share
= disclosed quantity coverage
× share with disclosed price protection
× execution rate
```

RPO, backlog or a firm financial commitment may improve revenue visibility, but
does **not** prove that ASP, gross margin or product mix is locked. Unless the
contract or an authorized disclosure establishes price or margin protection,
do not give the Base case that protection. Mark the protected share
`unobserved`/`human-required` and test unprotected pricing; missing disclosure
is not evidence that the economic share is literally zero.

Customer prepayments and contract liabilities belong in the cash and working-capital bridge until revenue is recognized.

## 4. Channel sell-in and sell-through

For Edge, client, mobile, embedded and Consumer channels, do not equate supplier bit shipments with final demand. Build:

```text
Supplier sell-in
= End-market sell-through
+ Change in channel / customer inventory
```

Track channel inventory, OEM inventory, promotions, price protection, product transitions and customer production constraints separately. Long-term AI content growth does not prevent short-term sell-in from turning negative during inventory correction.

Maintain two cost paths:

```text
Technical cost per bit
= node density, yield and process efficiency

Effective cost per bit
= technical cost
+ low-utilization / fixed-cost absorption
+ transition and NRV effects
```

A technical cost decline does not guarantee an effective cost decline at a cycle downturn.

## 4. Customer and AI-storage demand

Separate customer demand from supplier awards:

```text
AI storage demand
= accelerator / rack population
× local-workspace capacity
+ context-store attach rate × context capacity
+ shared data-lake capacity
```

Then apply enterprise-flash serviceability and supplier share. Platform demand is a cross-check, not an additional revenue line. Do not claim a hyperscaler as a customer without company, customer or regulatory evidence.

For KV or context storage, model both demand expansion and efficiency offsets: KV quantization, GQA/MLA, sparse attention, recomputation, cache admission and shared storage.

## 5. Product stage gates

Use the standard stages:

- Stage 0 research/concept: zero base revenue.
- Stage 1 sample/development: option only.
- Stage 2 customer qualification: zero or immaterial base revenue.
- Stage 3 production plus named or high-confidence customer/platform: may enter base.
- Stage 4 material revenue and profit: full model.

Do not convert layer count, interface speed or bit-density improvement directly into cost reduction. Node transitions require a separate yield, wafer-output, conversion-cost and product-adoption bridge.

## 6. Manufacturing and joint-venture capital bridge

Table capex is not necessarily economic capital intensity. For unconsolidated or jointly operated fabs, model:

```text
Economic manufacturing cash requirement
= consolidated capex
+ JV loans / equity contributions
+ equipment prepayments
+ guarantee or support payments
+ manufacturing-service / supply-availability payments
- JV loan repayments and other recoveries
```

Also track:

- economic share of fab output;
- obligation to absorb fixed costs even when purchases are reduced;
- maximum exposure under guarantees;
- known contractual cash requirements;
- foreign-exchange effects;
- whether the same manufacturing cost is already included in COGS.

Avoid double counting: normal wafer purchases, fixed manufacturing costs and service fees already included in inventory/COGS should not also be deducted from free cash flow. Only incremental financing, capital contributions, prepayments, guarantees and capital-like service commitments should be added to economic capex.

## 7. Inventory, utilization and accounting bridge

Model DSO, DIO, DPO, customer advances, inventory reserves, under-utilization and NRV separately. At a NAND trough, gross profit can be much worse than the simple ASP-minus-cost spread because low utilization and inventory write-downs are nonlinear.

Maintain both reported GAAP and operating/normalized profit where material. Do not erase NRV, impairment, debt-extinguishment, restructuring, stock compensation or tax effects from the reported model.

## 8. Shares, buybacks and capital allocation

Roll shares explicitly:

```text
Ending shares
= Beginning shares
+ stock compensation / ESPP issuance
- repurchased shares

Repurchased shares
= buyback dollars / average repurchase price
```

Do not assume an authorization is renewed after it is exhausted. Test whether repurchases compete with R&D, joint-venture funding, debt repayment and working-capital needs.

## 9. Valuation contract

Use the valuation lenses that expose the material uncertainty; common choices
include:

1. **cycle value** using one- to three-year scenario EPS or free cash flow;
2. **normalized value** using post-cycle revenue, gross margin, capital intensity, FCFE/FCF and a terminal multiple.

Also run a reverse model from the current price to implied revenue, gross margin, ASP path or bull-case probability. HBM, HBF, QLC or context-storage options must be valued separately until they pass the stage gate.

## 10. Mandatory outputs

- quarterly one-year product model;
- five-year end-market revenue and gross-profit schedule;
- bit, ASP and unit-cost assumptions;
- contract/RPO visibility bridge;
- customer and AI-storage cross-check;
- JV/fab economic-capital bridge;
- working-capital, cash and share-count roll-forward;
- a free-named reference path plus only the material rival states selected for
  the case, including under-utilization/NRV when a downside state makes them relevant;
- cycle and normalized valuation;
- monitoring triggers tied to exact assumptions.
